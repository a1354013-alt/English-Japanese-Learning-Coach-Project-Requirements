"""RAG manager abstraction with a safe disabled mode and local SQLite backend."""

from __future__ import annotations

import re
import sqlite3
import uuid
from pathlib import Path
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


class _LocalRAGManager:
    COLLECTION_NAME = "rag_materials"

    def __init__(self, *_: Any) -> None:
        self.enabled = True
        self.init_error: Optional[str] = None
        self.disabled_by_config = False
        storage_path = Path(settings.chroma_db_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        self._db_path = storage_path / "rag_materials.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    material_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    language TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    total_chunks INTEGER NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    document TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_user_language_material
                ON rag_chunks(user_id, language, material_id, chunk_index)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_user_uploaded
                ON rag_chunks(user_id, uploaded_at DESC, material_id)
                """
            )

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
        rows = [
            {
                **self._material_metadata(
                    dict(metadata),
                    user_id=user_id,
                    material_id=material_id,
                    chunk_index=idx,
                    total_chunks=total_chunks,
                ),
                "id": self._chunk_id(material_id, idx),
                "document": chunk,
            }
            for idx, chunk in enumerate(chunks)
        ]
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM rag_chunks WHERE user_id = ? AND material_id = ?",
                (user_id, material_id),
            )
            conn.executemany(
                """
                INSERT INTO rag_chunks (
                    id, user_id, material_id, title, source, language, source_type,
                    chunk_index, total_chunks, uploaded_at, document
                ) VALUES (
                    :id, :user_id, :material_id, :title, :source, :language, :source_type,
                    :chunk_index, :total_chunks, :uploaded_at, :document
                )
                """,
                rows,
            )
        return material_id

    def list_materials(self, *, user_id: str, language: Optional[str] = None) -> List[dict]:
        query = """
            SELECT material_id, source, title, language, source_type, uploaded_at,
                   MAX(total_chunks) AS total_chunks,
                   MIN(chunk_index) AS first_chunk_index
            FROM rag_chunks
            WHERE user_id = ?
        """
        params: list[Any] = [user_id]
        if language:
            query += " AND language = ?"
            params.append(language)
        query += " GROUP BY material_id, source, title, language, source_type, uploaded_at"
        query += " ORDER BY uploaded_at DESC, material_id ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            materials: list[dict[str, Any]] = []
            for row in rows:
                text_row = conn.execute(
                    """
                    SELECT document
                    FROM rag_chunks
                    WHERE user_id = ? AND material_id = ? AND chunk_index = ?
                    """,
                    (user_id, row["material_id"], row["first_chunk_index"]),
                ).fetchone()
                materials.append(
                    {
                        "material_id": row["material_id"],
                        "doc_id": row["material_id"],
                        "source": row["source"],
                        "title": row["title"],
                        "language": row["language"],
                        "source_type": row["source_type"],
                        "uploaded_at": row["uploaded_at"],
                        "total_chunks": int(row["total_chunks"] or 1),
                        "text": text_row["document"] if text_row else None,
                    }
                )
        return materials

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM rag_chunks WHERE user_id = ? AND material_id = ?",
                (user_id, doc_id),
            )
            return int(result.rowcount or 0) > 0

    def query_materials(
        self,
        query: str,
        *,
        user_id: str,
        language: Optional[str] = None,
        n_results: int = 3,
    ) -> List[dict]:
        delimited_terms = [term for term in re.findall(r"[\w\u3040-\u30ff\u3400-\u9fff]+", query.lower()) if term]
        sql = "SELECT * FROM rag_chunks WHERE user_id = ?"
        params: list[Any] = [user_id]
        if language:
            sql += " AND language = ?"
            params.append(language)
        with self._connect() as conn:
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

        def score(row: dict[str, Any]) -> tuple[int, str, int, str]:
            haystack = " ".join(
                str(row.get(field) or "").lower()
                for field in ("document", "title", "source")
            )
            lexical_score = sum(haystack.count(term) for term in delimited_terms)
            return (
                -lexical_score,
                str(row.get("uploaded_at") or ""),
                int(row.get("chunk_index") or 0),
                str(row.get("id") or ""),
            )

        ranked = sorted(rows, key=score)[: max(0, n_results)]
        return [
            {
                "material_id": str(row["material_id"]),
                "doc_id": str(row["material_id"]),
                "text": str(row["document"]),
                "source": str(row["source"]),
                "title": str(row["title"]),
                "language": str(row["language"]),
                "source_type": str(row["source_type"]),
                "uploaded_at": str(row["uploaded_at"]),
                "total_chunks": int(row["total_chunks"] or 1),
                "chunk_index": int(row["chunk_index"] or 0),
            }
            for row in ranked
        ]


_ChromaRAGManager = _LocalRAGManager


class RAGManager:
    def __init__(self) -> None:
        self._backend = self._build_backend()

    @staticmethod
    def _build_backend() -> DisabledRAGManager | _LocalRAGManager:
        if not settings.enable_rag:
            return DisabledRAGManager("RAG is disabled by configuration", disabled_by_config=True)

        try:
            return _LocalRAGManager()
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
