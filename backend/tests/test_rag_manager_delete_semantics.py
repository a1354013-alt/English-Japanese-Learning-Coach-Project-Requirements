"""RAGManager delete semantics against a real Chroma collection.

This specifically guards against "fake success" deletes where Chroma's idempotent
delete(where=...) does not raise even when nothing matches.
"""

from __future__ import annotations

from pathlib import Path

import rag_manager as rag_manager_module
from config import settings
from rag_manager import RAGManager


def test_delete_material_distinguishes_missing_doc_id(tmp_path, monkeypatch):
    # Use an isolated Chroma store so this test is hermetic.
    chroma_dir = Path(tmp_path) / "chroma_db"
    monkeypatch.setattr(settings, "chroma_db_path", str(chroma_dir), raising=False)

    mgr = RAGManager()
    assert mgr.enabled is True

    doc_id = mgr.add_material(
        "hello world",
        metadata={"language": "EN", "source": "test"},
        user_id="u1",
    )

    assert mgr.delete_material(user_id="u1", doc_id=doc_id) is True
    # Deleting again must be a "not found", not a fake success.
    assert mgr.delete_material(user_id="u1", doc_id=doc_id) is False


def test_delete_material_respects_user_isolation(tmp_path, monkeypatch):
    chroma_dir = Path(tmp_path) / "chroma_db"
    monkeypatch.setattr(settings, "chroma_db_path", str(chroma_dir), raising=False)

    mgr = RAGManager()
    assert mgr.enabled is True

    doc_id = mgr.add_material(
        "hello world",
        metadata={"language": "EN", "source": "test"},
        user_id="u_owner",
    )

    # Other users should not be able to delete it.
    assert mgr.delete_material(user_id="u_other", doc_id=doc_id) is False
    # Owner can still delete successfully.
    assert mgr.delete_material(user_id="u_owner", doc_id=doc_id) is True


def test_delete_material_returns_false_when_rag_disabled(monkeypatch):
    def _boom(*args, **kwargs):  # pragma: no cover - executed in test only
        raise RuntimeError("chroma down")

    monkeypatch.setattr(rag_manager_module.chromadb, "PersistentClient", _boom, raising=True)

    mgr = RAGManager()
    assert mgr.enabled is False
    assert mgr.delete_material(user_id="u1", doc_id="missing") is False

