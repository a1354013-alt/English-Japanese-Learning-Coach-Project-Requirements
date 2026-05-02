"""RAG manager abstraction with a safe disabled mode and optional Chroma backend."""

from __future__ import annotations

import importlib
import uuid
from typing import Any, Dict, List, Optional

from config import settings

__all__ = ["DisabledRAGManager", "RAGManager", "rag_manager", "split_into_chunks"]


def split_into_chunks(text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")

    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_length = 0

    for word in words:
        token_length = len(word) + (1 if current_chunk else 0)
        if current_length + token_length > max_chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            if overlap <= 0:
                current_chunk = []
                current_length = 0
            else:
                overlap_words = current_chunk[-overlap:]
                current_chunk = list(overlap_words)
                current_length = sum(len(w) + 1 for w in current_chunk) - 1
        current_chunk.append(word)
        current_length += token_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


class RAGUnavailableError(RuntimeError):
    """Raised when callers try to mutate RAG while the backend is unavailable."""


class DisabledRAGManager:
    def __init__(self, message: str, *, disabled_by_config: bool) -> None:
        self.enabled = False
        self.init_error = message
        self.disabled_by_config = disabled_by_config

    def add_material(self, text: str, metadata: dict, *, user_id: str, doc_id: Optional[str] = None) -> str:
        raise RAGUnavailableError(self.init_error or "RAG is unavailable")

    def list_materials(self, *, user_id: str, language: Optional[str] = None) -> List[dict]:
        return []

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        return False

    def query_materials(
        self,
        query: str,
        *,
        user_id: str,
        language: Optional[str] = None,
        n_results: int = 3,
    ) -> List[dict]:
        return []


class _ChromaRAGManager:
    COLLECTION_NAME = "rag_materials"

    def __init__(self, chromadb_module: Any, chroma_settings_cls: Any, embedding_function_cls: Any) -> None:
        self.enabled = True
        self.init_error: Optional[str] = None
        self.disabled_by_config = False
        self._client = chromadb_module.PersistentClient(
            path=str(settings.chroma_db_path),
            settings=chroma_settings_cls(),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=embedding_function_cls(),
        )

    def _user_filter(self, user_id: str, language: Optional[str] = None) -> Dict[str, Any]:
        filters: List[Dict[str, str]] = [{"user_id": user_id}]
        if language:
            filters.append({"language": language})
        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}

    def _normalize_get_result(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []

        items: List[Dict[str, Any]] = []
        for idx, item_id in enumerate(ids):
            metadata = dict(metadatas[idx] if idx < len(metadatas) else {})
            _ = documents[idx] if idx < len(documents) else ""
            items.append(
                {
                    "doc_id": item_id,
                    "source": metadata.get("source", "unknown"),
                    "language": metadata.get("language", "unknown"),
                    "uploaded_at": metadata.get("uploaded_at", ""),
                    "total_chunks": metadata.get("total_chunks", 1),
                }
            )
        return items

    def add_material(self, text: str, metadata: dict, *, user_id: str, doc_id: Optional[str] = None) -> str:
        doc_id = doc_id or str(uuid.uuid4())
        metadata_copy = dict(metadata)
        metadata_copy["user_id"] = user_id

        self._collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata_copy],
        )
        return doc_id

    def list_materials(self, *, user_id: str, language: Optional[str] = None) -> List[dict]:
        where = self._user_filter(user_id, language)
        result = self._collection.get(where=where, include=["ids", "documents", "metadatas"])
        return self._normalize_get_result(result)

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        result = self._collection.get(ids=[doc_id], include=["metadatas"])
        if not result.get("ids"):
            return False

        metadata = result.get("metadatas", [])[0] if result.get("metadatas") else {}
        if metadata.get("user_id") != user_id:
            return False

        self._collection.delete(ids=[doc_id])
        return True

    def query_materials(
        self,
        query: str,
        *,
        user_id: str,
        language: Optional[str] = None,
        n_results: int = 3,
    ) -> List[dict]:
        where = self._user_filter(user_id, language)
        result = self._collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["metadatas", "documents"],
        )

        ids = result.get("ids") or [[]]
        documents = result.get("documents") or [[]]
        metadatas = result.get("metadatas") or [[]]

        row_ids = ids[0] if ids and isinstance(ids[0], list) else ids
        row_documents = documents[0] if documents and isinstance(documents[0], list) else documents
        row_metadatas = metadatas[0] if metadatas and isinstance(metadatas[0], list) else metadatas

        items: List[Dict[str, Any]] = []
        for idx, item_id in enumerate(row_ids):
            metadata = dict(row_metadatas[idx] if idx < len(row_metadatas) else {})
            document = row_documents[idx] if idx < len(row_documents) else ""
            items.append(
                {
                    "doc_id": item_id,
                    "text": document,
                    "source": metadata.get("source", "unknown"),
                    "language": metadata.get("language", "unknown"),
                    "uploaded_at": metadata.get("uploaded_at", ""),
                    "total_chunks": metadata.get("total_chunks", 1),
                }
            )
        return items


class RAGManager:
    def __init__(self) -> None:
        self._backend = self._build_backend()

    @staticmethod
    def _build_backend() -> DisabledRAGManager | _ChromaRAGManager:
        if not settings.enable_rag:
            return DisabledRAGManager("RAG is disabled by configuration", disabled_by_config=True)

        try:
            chromadb_module = importlib.import_module("chromadb")
            chroma_settings_cls = importlib.import_module("chromadb.config").Settings
            embedding_function_cls = importlib.import_module(
                "chromadb.utils.embedding_functions"
            ).DefaultEmbeddingFunction
        except ModuleNotFoundError as err:
            missing_name = err.name or ""
            if missing_name == "chromadb" or missing_name.startswith("chromadb.") or "chromadb" in str(err).lower():
                message = (
                    "RAG is enabled but chromadb is not installed. "
                    "Install backend requirements or set ENABLE_RAG=false."
                )
                return DisabledRAGManager(message, disabled_by_config=False)
            raise

        try:
            return _ChromaRAGManager(chromadb_module, chroma_settings_cls, embedding_function_cls)
        except Exception as err:
            message = f"RAG could not be initialized: {err}"
            return DisabledRAGManager(message, disabled_by_config=False)

    @property
    def enabled(self) -> bool:
        return self._backend.enabled

    @property
    def init_error(self) -> Optional[str]:
        return self._backend.init_error

    @property
    def disabled_by_config(self) -> bool:
        return self._backend.disabled_by_config

    def add_material(self, text: str, metadata: dict, *, user_id: str, doc_id: Optional[str] = None) -> str:
        return self._backend.add_material(text, metadata, user_id=user_id, doc_id=doc_id)

    def list_materials(self, *, user_id: str, language: Optional[str] = None) -> List[dict]:
        return self._backend.list_materials(user_id=user_id, language=language)

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        return self._backend.delete_material(user_id=user_id, doc_id=doc_id)

    def query_materials(
        self,
        query: str,
        *,
        user_id: str,
        language: Optional[str] = None,
        n_results: int = 3,
    ) -> List[dict]:
        return self._backend.query_materials(
            query,
            user_id=user_id,
            language=language,
            n_results=n_results,
        )


rag_manager = RAGManager()
