"""Pytest import setup for backend tests in local and CI environments."""

import gc
import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="language-coach-pytest-"))

os.environ.setdefault("DATA_DIR", str(TEST_DATA_DIR))
os.environ.setdefault("DB_PATH", str(TEST_DATA_DIR / "language_coach.db"))
os.environ.setdefault("CHROMA_DB_PATH", str(TEST_DATA_DIR / "chroma_db"))
os.environ.setdefault("ENABLE_RAG", "false")

for path in (REPO_ROOT, BACKEND_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture(autouse=True)
def _close_database_instances():
    yield
    from database import Database

    Database.close_all_instances()
    gc.collect()
