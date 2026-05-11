"""Contract tests for chunked RAG storage without requiring a real Chroma install."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rag_manager import _ChromaRAGManager, split_into_chunks


class _FakeCollection:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, Any]] = {}

    def add(self, *, ids: List[str], documents: List[str], metadatas: List[dict]) -> None:
        for item_id, document, metadata in zip(ids, documents, metadatas, strict=True):
            self.records[item_id] = {
                "id": item_id,
                "document": document,
                "metadata": metadata,
            }

    def _matches(self, metadata: dict, where: Optional[dict]) -> bool:
        if not where:
            return True
        if "$and" in where:
            return all(self._matches(metadata, clause) for clause in where["$and"])
        return all(metadata.get(key) == value for key, value in where.items())

    def get(self, ids: Optional[List[str]] = None, where: Optional[dict] = None, include: Optional[List[str]] = None) -> dict:
        include = include or []
        selected = []
        for item_id, record in self.records.items():
            if ids is not None and item_id not in ids:
                continue
            if not self._matches(record["metadata"], where):
                continue
            selected.append(record)
        return {
            "ids": [record["id"] for record in selected],
            "documents": [record["document"] for record in selected] if "documents" in include else [],
            "metadatas": [record["metadata"] for record in selected] if "metadatas" in include else [],
        }

    def delete(self, ids: List[str]) -> None:
        for item_id in ids:
            self.records.pop(item_id, None)

    def query(self, *, query_texts: List[str], n_results: int, where: Optional[dict], include: List[str]) -> dict:
        del query_texts
        selected = [
            record
            for record in self.records.values()
            if self._matches(record["metadata"], where)
        ][:n_results]
        return {
            "ids": [[record["id"] for record in selected]],
            "documents": [[record["document"] for record in selected]] if "documents" in include else [[]],
            "metadatas": [[record["metadata"] for record in selected]] if "metadatas" in include else [[]],
        }


def _make_manager() -> _ChromaRAGManager:
    manager = object.__new__(_ChromaRAGManager)
    manager.enabled = True
    manager.init_error = None
    manager.disabled_by_config = False
    manager._collection = _FakeCollection()
    return manager


def test_add_material_splits_long_text_and_stores_required_metadata():
    manager = _make_manager()
    long_text = " ".join(f"token-{idx}" for idx in range(200))

    material_id = manager.add_material(
        long_text,
        metadata={
            "title": "notes.txt",
            "source": "notes.txt",
            "language": "EN",
            "source_type": "text",
            "uploaded_at": "2026-05-10T10:00:00",
        },
        user_id="u1",
    )

    stored = list(manager._collection.records.values())
    assert len(stored) > 1
    for expected_index, record in enumerate(stored):
        metadata = record["metadata"]
        assert metadata["material_id"] == material_id
        assert metadata["title"] == "notes.txt"
        assert metadata["language"] == "EN"
        assert metadata["source_type"] == "text"
        assert metadata["chunk_index"] == expected_index
        assert metadata["total_chunks"] == len(stored)
        assert metadata["uploaded_at"] == "2026-05-10T10:00:00"

    materials = manager.list_materials(user_id="u1", language="EN")
    assert materials == [
        {
            "material_id": material_id,
            "doc_id": material_id,
            "source": "notes.txt",
            "title": "notes.txt",
            "language": "EN",
            "source_type": "text",
            "uploaded_at": "2026-05-10T10:00:00",
            "total_chunks": len(stored),
            "text": stored[0]["document"],
        }
    ]


def test_query_returns_evidence_fields_needed_by_frontend():
    manager = _make_manager()
    material_id = manager.add_material(
        "alpha beta gamma " * 80,
        metadata={
            "title": "guide.pdf",
            "source": "guide.pdf",
            "language": "JP",
            "source_type": "pdf",
            "uploaded_at": "2026-05-10T11:00:00",
        },
        user_id="u1",
    )

    evidence = manager.query_materials("gamma", user_id="u1", language="JP", n_results=2)

    assert evidence
    assert evidence[0]["material_id"] == material_id
    assert evidence[0]["doc_id"] == material_id
    assert evidence[0]["title"] == "guide.pdf"
    assert evidence[0]["language"] == "JP"
    assert evidence[0]["source_type"] == "pdf"
    assert isinstance(evidence[0]["chunk_index"], int)
    assert evidence[0]["total_chunks"] >= 1
    assert evidence[0]["text"]


def test_delete_material_removes_all_chunks_for_same_material():
    manager = _make_manager()
    material_id = manager.add_material(
        "delta epsilon zeta " * 90,
        metadata={
            "title": "delete-me.txt",
            "source": "delete-me.txt",
            "language": "EN",
            "source_type": "text",
            "uploaded_at": "2026-05-10T12:00:00",
        },
        user_id="u1",
    )

    assert len(manager._collection.records) > 1
    assert manager.delete_material(user_id="u1", doc_id=material_id) is True
    assert manager._collection.records == {}
    assert manager.delete_material(user_id="u1", doc_id=material_id) is False


def test_split_into_chunks_keeps_english_text_chunked():
    chunks = split_into_chunks(" ".join(f"word{idx}" for idx in range(80)), max_chunk_size=80, overlap=10)
    assert len(chunks) > 1
    assert all(len(chunk) <= 90 for chunk in chunks)
    assert chunks[0][-10:] == chunks[1][:10]


def test_split_into_chunks_handles_cjk_without_spaces():
    text = "これは日本語の文章です。" * 30
    chunks = split_into_chunks(text, max_chunk_size=60, overlap=8)
    assert len(chunks) > 1
    assert all(len(chunk) <= 68 for chunk in chunks)
    assert chunks[0][-8:] == chunks[1][:8]


def test_split_into_chunks_handles_very_long_paragraph_without_spaces():
    text = "x" * 250
    chunks = split_into_chunks(text, max_chunk_size=80, overlap=10)
    assert len(chunks) == 4
    assert chunks[0] == "x" * 80
    assert chunks[0][-10:] == chunks[1][:10]


def test_split_into_chunks_empty_text_is_empty():
    assert split_into_chunks("   ", max_chunk_size=20, overlap=5) == []
