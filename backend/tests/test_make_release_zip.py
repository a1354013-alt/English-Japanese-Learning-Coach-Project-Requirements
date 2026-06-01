"""Release zip should exclude runtime data and local artifacts."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_make_release_zip() -> ModuleType:
    module_path = REPO_ROOT / "scripts" / "make_release_zip.py"
    spec = importlib.util.spec_from_file_location("make_release_zip", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load release script: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


make_release_zip = _load_make_release_zip()


def _write_text(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_release_zip_excludes_runtime_and_local_artifacts(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    dist_dir = repo_root / "dist"
    _write_text(repo_root / "VERSION", "9.9.9")
    _write_text(repo_root / "README.md", "keep me")
    _write_text(repo_root / "data" / ".gitkeep", "")
    _write_text(repo_root / "data" / "language_coach.db", "db")
    _write_text(repo_root / "data" / "language_coach.db-wal", "wal")
    _write_text(repo_root / "data" / "language_coach.db-shm", "shm")
    _write_text(repo_root / "data" / "chroma" / "index.bin", "vector")
    _write_text(repo_root / "data" / "chroma_db" / "index.bin", "vector")
    _write_text(repo_root / "data" / "audio" / "sample.wav", "audio")
    _write_text(repo_root / "data" / "exports" / "lesson.pdf", "pdf")
    _write_text(repo_root / "data" / "lessons" / "lesson.json", "{}")
    _write_text(repo_root / "frontend" / "test-results" / "result.txt", "test")
    _write_text(repo_root / "frontend" / "dist" / "index.html", "build")
    _write_text(repo_root / "frontend" / "playwright-report" / "index.html", "report")
    _write_text(repo_root / "frontend" / "coverage" / "lcov.info", "coverage")
    _write_text(repo_root / "frontend" / "node_modules" / "dep.js", "dep")
    _write_text(repo_root / "backend" / ".playwright-data" / "language_coach.db", "db")
    _write_text(repo_root / "backend" / ".pytest_cache" / "state", "cache")
    _write_text(repo_root / "__pycache__" / "module.pyc", "pyc")

    monkeypatch.setattr(make_release_zip, "REPO_ROOT", repo_root)
    monkeypatch.setattr(make_release_zip, "DIST_DIR", dist_dir)
    monkeypatch.setattr(make_release_zip, "VERSION", "9.9.9")

    assert make_release_zip.main() == 0

    archive_path = dist_dir / "english-japanese-learning-coach-v9.9.9.zip"
    assert archive_path.exists()
    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "README.md" in names
    assert "data/.gitkeep" in names
    assert "data/language_coach.db" not in names
    assert "data/language_coach.db-wal" not in names
    assert "data/language_coach.db-shm" not in names
    assert not any(name.endswith(".db") for name in names)
    assert not any(name.endswith(".db-wal") for name in names)
    assert not any(name.endswith(".db-shm") for name in names)
    assert not any(name.startswith("data/chroma/") for name in names)
    assert not any(name.startswith("data/chroma_db/") for name in names)
    assert not any(name.startswith("data/audio/") for name in names)
    assert not any(name.startswith("data/exports/") for name in names)
    assert not any(name.startswith("data/lessons/") for name in names)
    assert not any(name.startswith("frontend/dist/") for name in names)
    assert not any(name.startswith("frontend/test-results/") for name in names)
    assert not any(name.startswith("frontend/playwright-report/") for name in names)
    assert not any(name.startswith("frontend/coverage/") for name in names)
    assert not any(name.startswith("frontend/node_modules/") for name in names)
    assert not any(name.startswith("backend/.playwright-data/") for name in names)


def test_should_skip_covers_required_artifact_patterns():
    assert make_release_zip.should_skip(Path("data/language_coach.db"))
    assert make_release_zip.should_skip(Path("data/language_coach.db-wal"))
    assert make_release_zip.should_skip(Path("data/language_coach.db-shm"))
    assert make_release_zip.should_skip(Path("data/chroma/index.bin"))
    assert make_release_zip.should_skip(Path("data/chroma_db/index.bin"))
    assert make_release_zip.should_skip(Path("frontend/dist/index.html"))
    assert make_release_zip.should_skip(Path("frontend/test-results/index.html"))
    assert make_release_zip.should_skip(Path("frontend/playwright-report/index.html"))
    assert make_release_zip.should_skip(Path("frontend/node_modules/pkg/index.js"))
    assert make_release_zip.should_skip(Path("backend/.playwright-data/language_coach.db"))
    assert make_release_zip.should_skip(Path("backend/.pytest_cache/state"))
    assert make_release_zip.should_skip(Path("__pycache__/module.pyc"))
    assert not make_release_zip.should_skip(Path("data/.gitkeep"))
