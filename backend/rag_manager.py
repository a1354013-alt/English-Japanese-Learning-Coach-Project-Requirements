"""Lazy RAG manager with optional ChromaDB backend."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import uuid4

from config import settings

logger = logging.getLogger(__name__)

# Tests may monkeypatch this symbol directly.
chromadb: Any = SimpleNamespace(PersistentClient=None)


def split_into_chunks(text: str, size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks for better retrieval."""
    if not text or not text.strip():
        return []

    chunks: List[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + size
        chunk = text[start:end]
        if end < text_len:
            search_start = max(start, end - 100)
            for sep in ["?\n", ".\n", "!\n", "\n\n"]:
                idx = chunk.rfind(sep, search_start - start)
                if idx > size // 2:
                    end = start + idx + len(sep)
                    chunk = text[start:end]
                    break
        chunks.append(chunk.strip())
        start = end - overlap if end < text_len else text_len
    return [chunk for chunk in chunks if chunk]


def _and_where(clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
    clauses = [clause for clause in clauses if clause]
    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _load_chromadb_module() -> Any:
    global chromadb
    if getattr(chromadb, "PersistentClient", None) is None:
        chromadb = importlib.import_module("chromadb")
    return chromadb


@dataclass
class _DummyRetriever:
    enabled: bool = False
    init_error: Optional[str] = "RAG disabled by configuration"

    def add_material(
        self,
        text: str,
        metadata: Dict[str, Any],
        *,
        doc_id: Optional[str] = None,
        user_id: str,
    ) -> str:
        raise RuntimeError(self.init_error or "RAG is disabled")

    def query_materials(
        self,
        query_text: str,
        *,
        user_id: str,
        language: str,
        n_results: int = 3,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return []

    def list_materials(self, *, user_id: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        return False


class _ChromaRAGBackend:
    def __init__(self) -> None:
        chroma_module = _load_chromadb_module()
        self.client = chroma_module.PersistentClient(path=str(settings.chroma_db_path))
        self.collection = self.client.get_or_create_collection(
            name="learning_materials",
            embedding_function=_DeterministicEmbeddingFunction(),
        )
        self.enabled = True
        self.init_error: Optional[str] = None

    def add_material(
        self,
        text: str,
        metadata: Dict[str, Any],
        *,
        doc_id: Optional[str] = None,
        user_id: str,
    ) -> str:
        if not text.strip():
            raise ValueError("Material content is empty")
        chunks = split_into_chunks(text, size=500, overlap=50)
        if not chunks:
            raise ValueError("Material content produced no chunks")

        timestamp = datetime.utcnow().isoformat()
        source = str(metadata.get("source", "unknown"))
        language = str(metadata.get("language", "unknown"))
        material_id = doc_id or str(uuid4())

        chunk_ids: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            chunk_ids.append(f"{material_id}_chunk_{index}")
            metadatas.append(
                {
                    "doc_id": material_id,
                    "user_id": user_id,
                    "source": source,
                    "chunk_index": index,
                    "language": language,
                    "uploaded_at": timestamp,
                    "total_chunks": len(chunks),
                }
            )

        self.collection.add(documents=chunks, metadatas=metadatas, ids=chunk_ids)
        return material_id

    def query_materials(
        self,
        query_text: str,
        *,
        user_id: str,
        language: str,
        n_results: int = 3,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            clauses: List[Dict[str, Any]] = [{"user_id": user_id}, {"language": language}]
            if filter_criteria:
                for key, value in filter_criteria.items():
                    clauses.append({str(key): value})
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=_and_where(clauses),
                include=["documents", "metadatas"],
            )
            docs = results.get("documents") or []
            metas = results.get("metadatas") or []
            if not docs or not docs[0]:
                return []
            evidence: List[Dict[str, Any]] = []
            for index, doc in enumerate(docs[0]):
                if not doc:
                    continue
                metadata = metas[0][index] if metas and index < len(metas[0]) else {}
                evidence.append(
                    {
                        "text": str(doc),
                        "source": metadata.get("source", "unknown"),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "doc_id": metadata.get("doc_id"),
                    }
                )
            return evidence
        except Exception:
            logger.exception("rag_query_failed")
            return []

    def list_materials(self, *, user_id: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        clauses: List[Dict[str, Any]] = [{"user_id": user_id}]
        if language:
            clauses.append({"language": language})
        try:
            results = self.collection.get(where=_and_where(clauses), include=["metadatas"])
            metas = results.get("metadatas") or []
            by_doc: Dict[str, Dict[str, Any]] = {}
            for meta in metas:
                if not isinstance(meta, dict):
                    continue
                doc_id = str(meta.get("doc_id") or "")
                if not doc_id or doc_id in by_doc:
                    continue
                by_doc[doc_id] = {
                    "doc_id": doc_id,
                    "source": meta.get("source", "unknown"),
                    "language": meta.get("language", "unknown"),
                    "uploaded_at": meta.get("uploaded_at"),
                    "total_chunks": meta.get("total_chunks"),
                }
            return sorted(by_doc.values(), key=lambda item: str(item.get("uploaded_at") or ""), reverse=True)
        except Exception:
            logger.exception("rag_list_failed")
            return []

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        where = _and_where([{"user_id": user_id}, {"doc_id": doc_id}])
        try:
            existing = self.collection.get(where=where, include=["metadatas"])
        except Exception as err:
            raise RuntimeError(f"RAG lookup failed: {err}") from err
        ids = existing.get("ids") or []
        if not ids:
            return False
        try:
            self.collection.delete(where=where)
        except Exception as err:
            raise RuntimeError(f"RAG delete failed: {err}") from err
        return True


class LazyRAGManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._backend: _DummyRetriever | _ChromaRAGBackend | None = None

    def _build_backend(self) -> _DummyRetriever | _ChromaRAGBackend:
        enable_rag = bool(getattr(settings, "enable_rag", True))

        if not enable_rag:
            logger.info("rag_disabled_by_config")
            return _DummyRetriever(init_error="RAG disabled by ENABLE_RAG=false")

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
        query_text: str,
        *,
        user_id: str,
        language: str,
        n_results: int = 3,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self._get_backend().query_materials(
            query_text,
            user_id=user_id,
            language=language,
            n_results=n_results,
            filter_criteria=filter_criteria,
        )

    def list_materials(self, *, user_id: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._get_backend().list_materials(user_id=user_id, language=language)

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        return self._get_backend().delete_material(user_id=user_id, doc_id=doc_id)

    def reset(self) -> None:
        with self._lock:
            self._backend = None


class _DeterministicEmbeddingFunction:
    """Tiny local embedding function for tests/demo mode without external downloads."""

    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for text in input:
            vector = [0.0] * 8
            encoded = text.encode("utf-8", errors="ignore")
            if not encoded:
                embeddings.append(vector)
                continue
            for index, byte in enumerate(encoded):
                vector[index % 8] += byte / 255.0
            scale = float(len(encoded))
            embeddings.append([round(value / scale, 6) for value in vector])
        return embeddings


RAGManager = LazyRAGManager
rag_manager = LazyRAGManager()
