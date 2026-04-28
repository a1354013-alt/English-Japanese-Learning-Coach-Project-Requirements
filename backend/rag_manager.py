"""RAG manager implementation backed by Chroma for user-uploaded reference materials."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from config import settings

__all__ = ["RAGManager", "rag_manager", "split_into_chunks"]


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


class RAGManager:
    COLLECTION_NAME = "rag_materials"

    def __init__(self) -> None:
        self.enabled = False
        self.init_error: Optional[str] = None
        self._client = None
        self._collection = None

        if not settings.enable_rag:
            self.init_error = "RAG is disabled by configuration"
            return

        try:
            self._client = chromadb.PersistentClient(
                path=str(settings.chroma_db_path),
                settings=ChromaSettings(),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=DefaultEmbeddingFunction(),
            )
            self.enabled = True
        except Exception as err:
            self.init_error = str(err)
            self.enabled = False

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
            document = documents[idx] if idx < len(documents) else ""
            item: Dict[str, Any] = {
                "doc_id": item_id,
                "source": metadata.get("source", "unknown"),
                "language": metadata.get("language", "unknown"),
                "uploaded_at": metadata.get("uploaded_at", ""),
                "total_chunks": metadata.get("total_chunks", 1),
            }
            items.append(item)
        return items

    def add_material(self, text: str, metadata: dict, *, user_id: str, doc_id: Optional[str] = None) -> str:
        if not self.enabled or self._collection is None:
            raise RuntimeError("RAG manager is not available")

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
        if not self.enabled or self._collection is None:
            return []

        where = self._user_filter(user_id, language)
        result = self._collection.get(where=where, include=["ids", "documents", "metadatas"])
        return self._normalize_get_result(result)

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        if not self.enabled or self._collection is None:
            return False

        result = self._collection.get(ids=[doc_id], include=["metadatas"])
        if not result.get("ids"):
            return False

        metadata = result.get("metadatas", [])[0] if result.get("metadatas") else {}
        if metadata.get("user_id") != user_id:
            return False

        self._collection.delete(ids=[doc_id])
        return True


class LazyRAGManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._backend: _DummyRetriever | _ChromaRAGBackend | None = None

    def _build_backend(self) -> _DummyRetriever | _ChromaRAGBackend:
        if not getattr(settings, "rag_enabled", True):
            logger.info("rag_disabled_by_config")
            return _DummyRetriever(init_error="RAG disabled by configuration")
        try:
            backend = _ChromaRAGBackend()
            logger.info("rag_backend_ready", extra={"path": str(settings.chroma_db_path)})
            return backend
        except Exception as err:
            logger.warning("rag_backend_init_failed", extra={"error": str(err)})
            return _DummyRetriever(init_error=str(err))

    def _get_backend(self) -> _DummyRetriever | _ChromaRAGBackend:
        if self._backend is None:
            with self._lock:
                if self._backend is None:
                    self._backend = self._build_backend()
        return self._backend

    @property
    def enabled(self) -> bool:
        return self._get_backend().enabled

    @property
    def init_error(self) -> Optional[str]:
        return self._get_backend().init_error

    def add_material(
        self,
        text: str,
        metadata: Dict[str, Any],
        *,
        doc_id: Optional[str] = None,
        user_id: str,
    ) -> str:
        return self._get_backend().add_material(text, metadata, doc_id=doc_id, user_id=user_id)

    def query_materials(
        self,
        query: str,
        *,
        user_id: str,
        language: Optional[str] = None,
        n_results: int = 3,
    ) -> List[dict]:
        if not self.enabled or self._collection is None:
            return []

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

        items: List[Dict[str, Any]] = []
        for idx, item_id in enumerate(ids[0] if isinstance(ids[0], list) else ids):
            metadata = dict(metadatas[0][idx] if metadatas and metadatas[0] else {})
            document = documents[0][idx] if documents and documents[0] else ""
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


rag_manager = RAGManager()
