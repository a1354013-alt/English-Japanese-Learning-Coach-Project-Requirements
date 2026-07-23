"""Contract tests for chunked local RAG storage."""

from __future__ import annotations

from pathlib import Path

from config import settings
from rag_manager import _LocalRAGManager, split_into_chunks


def _make_manager(tmp_path: Path, monkeypatch) -> _LocalRAGManager:
    monkeypatch.setattr(settings, "chroma_db_path", str(tmp_path / "rag_store"), raising=False)
    return _LocalRAGManager()


def test_add_material_splits_long_text_and_stores_required_metadata(tmp_path, monkeypatch):
    manager = _make_manager(tmp_path, monkeypatch)
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

    with manager._connect() as conn:
        stored = conn.execute(
            "SELECT * FROM rag_chunks WHERE material_id = ? ORDER BY chunk_index",
            (material_id,),
        ).fetchall()
    assert len(stored) > 1
    for expected_index, record in enumerate(stored):
        assert record["material_id"] == material_id
        assert record["title"] == "notes.txt"
        assert record["language"] == "EN"
        assert record["source_type"] == "text"
        assert record["chunk_index"] == expected_index
        assert record["total_chunks"] == len(stored)
        assert record["uploaded_at"] == "2026-05-10T10:00:00"

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


def test_query_returns_evidence_fields_needed_by_frontend(tmp_path, monkeypatch):
    manager = _make_manager(tmp_path, monkeypatch)
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


def test_delete_material_removes_all_chunks_for_same_material(tmp_path, monkeypatch):
    manager = _make_manager(tmp_path, monkeypatch)
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

    with manager._connect() as conn:
        count = conn.execute("SELECT COUNT(1) AS count FROM rag_chunks").fetchone()["count"]
    assert count > 1
    assert manager.delete_material(user_id="u1", doc_id=material_id) is True
    with manager._connect() as conn:
        count = conn.execute("SELECT COUNT(1) AS count FROM rag_chunks").fetchone()["count"]
    assert count == 0
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
