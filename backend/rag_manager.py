"""RAG manager abstraction with a safe disabled mode and optional Chroma backend."""

from __future__ import annotations

import importlib
import re
import uuid
from typing import Any, Dict, List, Optional

from config import settings
from time_utils import local_now

__all__ = ["DisabledRAGManager", "RAGManager", "rag_manager", "split_into_chunks"]


def split_into_chunks(text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")

    normalized = text.strip()
    if not normalized:
        return []

    chunks: List[str] = []
    boundaries = [m.end() for m in re.finditer(r"[\u3002\uff01\uff1f.!?\n]+", normalized)]
    start = 0
    while start < len(normalized):
        hard_end = min(start + max_chunk_size, len(normalized))
        end = hard_end
        natural = [idx for idx in boundaries if start < idx <= hard_end]
        if natural:
            end = natural[-1]
        elif hard_end < len(normalized):
            space = normalized.rfind(" ", start + 1, hard_end + 1)
            if space > start:
                end = space

        if end <= start:
            end = hard_end

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break

        next_start = max(0, end - overlap) if overlap else end
        start = end if next_start <= start else next_start

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

        materials: Dict[str, Dict[str, Any]] = {}
        for idx, item_id in enumerate(ids):
            metadata = dict(metadatas[idx] if idx < len(metadatas) else {})
            document = documents[idx] if idx < len(documents) else ""
            material_id = str(metadata.get("material_id") or item_id)
            current = materials.get(material_id)
            if current is None:
                current = {
                    "material_id": material_id,
                    "doc_id": material_id,
                    "source": metadata.get("source", "unknown"),
                    "title": metadata.get("title") or metadata.get("source", "unknown"),
                    "language": metadata.get("language", "unknown"),
                    "source_type": metadata.get("source_type", "text"),
                    "uploaded_at": metadata.get("uploaded_at", ""),
                    "total_chunks": int(metadata.get("total_chunks", 1) or 1),
                    "text": document or None,
                }
                materials[material_id] = current
            else:
                current["total_chunks"] = max(
                    int(current.get("total_chunks", 1) or 1),
                    int(metadata.get("total_chunks", 1) or 1),
                )
                if not current.get("text") and document:
                    current["text"] = document
        return sorted(materials.values(), key=lambda item: str(item.get("uploaded_at") or ""), reverse=True)

    @staticmethod
    def _chunk_id(material_id: str, chunk_index: int) -> str:
        return f"{material_id}:chunk:{chunk_index}"

    @staticmethod
    def _material_metadata(
        metadata: Dict[str, Any],
        *,
        user_id: str,
        material_id: str,
        chunk_index: int,
        total_chunks: int,
    ) -> Dict[str, Any]:
        title = str(metadata.get("title") or metadata.get("source") or "unknown")
        source = str(metadata.get("source") or title)
        uploaded_at = str(metadata.get("uploaded_at") or local_now().isoformat())
        source_type = str(metadata.get("source_type") or "text")
        language = str(metadata.get("language") or "unknown")
        return {
            "user_id": user_id,
            "material_id": material_id,
            "title": title,
            "source": source,
            "language": language,
            "source_type": source_type,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "uploaded_at": uploaded_at,
        }

    def add_material(self, text: str, metadata: dict, *, user_id: str, doc_id: Optional[str] = None) -> str:
        material_id = doc_id or str(uuid.uuid4())
        chunks = split_into_chunks(text)
        if not chunks and text.strip():
            chunks = [text.strip()]
        if not chunks:
            raise ValueError("Cannot add empty material")

        total_chunks = len(chunks)
        self._collection.add(
            ids=[self._chunk_id(material_id, idx) for idx in range(total_chunks)],
            documents=chunks,
            metadatas=[
                self._material_metadata(
                    dict(metadata),
                    user_id=user_id,
                    material_id=material_id,
                    chunk_index=idx,
                    total_chunks=total_chunks,
                )
                for idx in range(total_chunks)
            ],
        )
        return material_id

    def list_materials(self, *, user_id: str, language: Optional[str] = None) -> List[dict]:
        where = self._user_filter(user_id, language)
        result = self._collection.get(where=where, include=["documents", "metadatas"])
        return self._normalize_get_result(result)

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        where = {"$and": [self._user_filter(user_id), {"material_id": doc_id}]}
        result = self._collection.get(where=where, include=["metadatas"])
        ids = result.get("ids") or []
        if not ids:
            return False
        self._collection.delete(ids=ids)
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
            material_id = str(metadata.get("material_id") or item_id)
            items.append(
                {
                    "material_id": material_id,
                    "doc_id": material_id,
                    "text": document,
                    "source": metadata.get("source", "unknown"),
                    "title": metadata.get("title") or metadata.get("source", "unknown"),
                    "language": metadata.get("language", "unknown"),
                    "source_type": metadata.get("source_type", "text"),
                    "uploaded_at": metadata.get("uploaded_at", ""),
                    "total_chunks": int(metadata.get("total_chunks", 1) or 1),
                    "chunk_index": int(metadata.get("chunk_index", 0) or 0),
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
            message = RAGManager._optional_dependency_error_message(err)
            if message:
                return DisabledRAGManager(message, disabled_by_config=False)
            raise

        try:
            return _ChromaRAGManager(chromadb_module, chroma_settings_cls, embedding_function_cls)
        except ModuleNotFoundError as err:
            message = RAGManager._optional_dependency_error_message(err)
            if message:
                return DisabledRAGManager(message, disabled_by_config=False)
            raise
        except Exception as err:
            message = f"RAG could not be initialized: {err}"
            return DisabledRAGManager(message, disabled_by_config=False)

    @staticmethod
    def _optional_dependency_error_message(err: ModuleNotFoundError) -> Optional[str]:
        missing_name = (err.name or "").lower()
        error_text = str(err).lower()
        if missing_name == "chromadb" or missing_name.startswith("chromadb.") or "chromadb" in error_text:
            return (
                "RAG is enabled but chromadb is not installed. "
                "Install backend/requirements-rag.txt and set ENABLE_RAG=true only when those dependencies are available."
            )
        if (
            missing_name == "sentence_transformers"
            or missing_name.startswith("sentence_transformers.")
            or "sentence-transformers" in error_text
            or "sentence_transformers" in error_text
        ):
            return (
                "RAG is enabled but sentence-transformers is not installed. "
                "Install backend/requirements-rag.txt and set ENABLE_RAG=true only when those dependencies are available."
            )
        return None

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
