"""Smoke coverage for ENABLE_RAG=true with the local RAG backend."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.mark.rag
def test_rag_enabled_smoke(tmp_path):
    env = os.environ.copy()
    data_dir = tmp_path / "rag-enabled-data"
    env.update(
        {
            "ENABLE_RAG": "true",
            "DATA_DIR": str(data_dir),
            "DB_PATH": str(data_dir / "language_coach.db"),
            "CHROMA_DB_PATH": str(data_dir / "chroma_db"),
            "PYTHONPATH": str(BACKEND_DIR),
        }
    )

    code = """
from config import settings
from rag_manager import RAGManager
from services.rag_service import build_material_metadata


assert settings.enable_rag is True
manager = RAGManager()
assert manager.enabled is True

text = (
    "Daily standup updates unblock releases. "
    "Chunking should keep repeated practice material searchable. "
) * 20
metadata = build_material_metadata(filename="smoke.txt", language="EN")
doc_id = manager.add_material(text, metadata=metadata, user_id="smoke-user", doc_id="smoke-doc")
assert doc_id == "smoke-doc"

items = manager.list_materials(user_id="smoke-user", language="EN")
assert len(items) == 1
assert items[0]["doc_id"] == "smoke-doc"
assert items[0]["total_chunks"] >= 2

hits = manager.query_materials("standup release practice", user_id="smoke-user", language="EN", n_results=2)
assert hits
assert any(hit["doc_id"] == "smoke-doc" for hit in hits)

assert manager.delete_material(user_id="smoke-user", doc_id="smoke-doc") is True
assert manager.list_materials(user_id="smoke-user", language="EN") == []
print("rag-enabled-smoke-ok")
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert result.returncode == 0, result.stderr
    assert "rag-enabled-smoke-ok" in result.stdout
