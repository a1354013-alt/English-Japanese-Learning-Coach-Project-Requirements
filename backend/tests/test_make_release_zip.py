"""Release zip should exclude runtime data and local artifacts."""

from __future__ import annotations

import importlib.util
import shutil
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


def _load_verify_delivery() -> ModuleType:
    module_path = REPO_ROOT / "scripts" / "verify_delivery.py"
    spec = importlib.util.spec_from_file_location("verify_delivery", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load verifier script: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


make_release_zip = _load_make_release_zip()
verify_delivery = _load_verify_delivery()


def _write_text(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_release_zip_excludes_runtime_and_local_artifacts(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    dist_dir = repo_root / "dist"
    _write_text(repo_root / "VERSION", "9.9.9")
    _write_text(repo_root / "README.md", "keep me")
    _write_text(repo_root / "start_backend.sh", "#!/usr/bin/env bash\ncd backend\ncp .env.example .env\n")
    _write_text(repo_root / "start_frontend.sh", "#!/usr/bin/env bash\ncd frontend\nnpm ci\n")
    _write_text(repo_root / "docker-compose.yml", "services: {}\n")
    _write_text(repo_root / ".vscode" / "launch.json", "{}")
    _write_text(repo_root / ".vscode" / "tasks.json", "{}")
    _write_text(repo_root / ".env", "SECRET=1")
    _write_text(repo_root / ".env.local", "SECRET=1")
    _write_text(repo_root / ".env.example", "ROOT_TEMPLATE=1")
    _write_text(repo_root / ".env.sample", "ROOT_SAMPLE=1")
    _write_text(repo_root / ".env.template", "ROOT_TEMPLATE=1")
    _write_text(repo_root / "backend" / ".env", "SECRET=1")
    _write_text(repo_root / "backend" / ".env.example", "BACKEND_TEMPLATE=1")
    _write_text(repo_root / "backend" / "requirements.txt", "fastapi\n")
    _write_text(repo_root / "backend" / "main.py", "app = object()\n")
    _write_text(repo_root / "frontend" / ".env.local", "SECRET=1")
    _write_text(repo_root / "frontend" / "package.json", "{\"name\":\"frontend\"}")
    _write_text(repo_root / "frontend" / "package-lock.json", "{\"name\":\"frontend\",\"lockfileVersion\":3}")
    _write_text(repo_root / "ops.env.production", "SECRET=1")
    _write_text(repo_root / "backend" / "api.log", "log")
    _write_text(repo_root / "backend" / "data" / "runtime.json", "{}")
    _write_text(repo_root / "data" / ".gitkeep", "")
    _write_text(repo_root / "data" / "language_coach.db", "db")
    _write_text(repo_root / "data" / "language_coach.sqlite", "db")
    _write_text(repo_root / "data" / "language_coach.sqlite3", "db")
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
    _write_text(repo_root / ".cache" / "tool" / "state", "cache")
    _write_text(repo_root / "htmlcov" / "index.html", "coverage")
    _write_text(repo_root / "coverage" / "coverage.xml", "coverage")
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
    assert ".env.example" in names
    assert ".env.sample" in names
    assert ".env.template" in names
    assert "backend/.env.example" in names
    assert "backend/requirements.txt" in names
    assert "backend/main.py" in names
    assert "frontend/package.json" in names
    assert "frontend/package-lock.json" in names
    assert "start_backend.sh" in names
    assert "start_frontend.sh" in names
    assert ".vscode/launch.json" in names
    assert ".vscode/tasks.json" in names
    assert "docker-compose.yml" in names
    assert "data/.gitkeep" in names
    assert ".env" not in names
    assert ".env.local" not in names
    assert "backend/.env" not in names
    assert "frontend/.env.local" not in names
    assert "ops.env.production" not in names
    assert "backend/api.log" not in names
    assert "data/language_coach.db" not in names
    assert "data/language_coach.sqlite" not in names
    assert "data/language_coach.sqlite3" not in names
    assert "data/language_coach.db-wal" not in names
    assert "data/language_coach.db-shm" not in names
    assert not any(name.endswith(".db") for name in names)
    assert not any(name.endswith(".log") for name in names)
    assert not any(name.endswith(".sqlite") for name in names)
    assert not any(name.endswith(".sqlite3") for name in names)
    assert not any(name.endswith(".db-wal") for name in names)
    assert not any(name.endswith(".db-shm") for name in names)
    assert not any(name.startswith("backend/data/") for name in names)
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
    assert not any(name.startswith(".cache/") for name in names)
    assert not any(name.startswith("htmlcov/") for name in names)
    assert not any(name.startswith("coverage/") for name in names)
    assert not any(name.startswith("backend/.playwright-data/") for name in names)


def test_should_skip_covers_required_artifact_patterns():
    assert make_release_zip.should_skip(Path(".env"))
    assert make_release_zip.should_skip(Path(".env.local"))
    assert make_release_zip.should_skip(Path("backend/.env"))
    assert make_release_zip.should_skip(Path("frontend/.env.local"))
    assert make_release_zip.should_skip(Path("ops.env.production"))
    assert make_release_zip.should_skip(Path("backend/.env.production"))
    assert not make_release_zip.should_skip(Path(".env.example"))
    assert not make_release_zip.should_skip(Path(".env.sample"))
    assert not make_release_zip.should_skip(Path(".env.template"))
    assert not make_release_zip.should_skip(Path("backend/.env.example"))
    assert make_release_zip.should_skip(Path("backend/api.log"))
    assert make_release_zip.should_skip(Path("data/language_coach.db"))
    assert make_release_zip.should_skip(Path("data/language_coach.sqlite"))
    assert make_release_zip.should_skip(Path("data/language_coach.sqlite3"))
    assert make_release_zip.should_skip(Path("data/language_coach.db-wal"))
    assert make_release_zip.should_skip(Path("data/language_coach.db-shm"))
    assert make_release_zip.should_skip(Path("data/chroma/index.bin"))
    assert make_release_zip.should_skip(Path("data/chroma_db/index.bin"))
    assert make_release_zip.should_skip(Path("frontend/dist/index.html"))
    assert make_release_zip.should_skip(Path("frontend/test-results/index.html"))
    assert make_release_zip.should_skip(Path("frontend/playwright-report/index.html"))
    assert make_release_zip.should_skip(Path("frontend/node_modules/pkg/index.js"))
    assert make_release_zip.should_skip(Path(".cache/tool/state"))
    assert make_release_zip.should_skip(Path("htmlcov/index.html"))
    assert make_release_zip.should_skip(Path("coverage/coverage.xml"))
    assert make_release_zip.should_skip(Path("backend/data/runtime.json"))
    assert make_release_zip.should_skip(Path("backend/.playwright-data/language_coach.db"))
    assert make_release_zip.should_skip(Path("backend/.pytest_cache/state"))
    assert make_release_zip.should_skip(Path("__pycache__/module.pyc"))
    assert not make_release_zip.should_skip(Path("data/.gitkeep"))


def test_verify_release_archive_rejects_excluded_artifacts(tmp_path, monkeypatch):
    archive_path = tmp_path / "release.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("README.md", "keep")
        archive.writestr("VERSION", "9.9.9")
        archive.writestr("backend/.env.example", "BACKEND_TEMPLATE=1\n")
        archive.writestr("backend/requirements.txt", "fastapi\n")
        archive.writestr("backend/main.py", "app = object()\n")
        archive.writestr("frontend/package.json", "{\"name\":\"frontend\"}")
        archive.writestr("frontend/package-lock.json", "{\"name\":\"frontend\",\"lockfileVersion\":3}")
        archive.writestr("start_backend.sh", "#!/usr/bin/env bash\ncd backend\ncp .env.example .env\n")
        archive.writestr("start_frontend.sh", "#!/usr/bin/env bash\ncd frontend\nnpm ci\n")
        archive.writestr(".vscode/launch.json", "{}")
        archive.writestr(".vscode/tasks.json", "{}")
        archive.writestr("docker-compose.yml", "services: {}\n")
        archive.writestr("backend/.env", "SECRET=1")

    monkeypatch.setattr(verify_delivery, "RELEASE_ARCHIVE", archive_path)

    try:
        verify_delivery.verify_release_archive()
    except verify_delivery.StepFailed as exc:
        assert "excluded local env file" in str(exc)
    else:
        raise AssertionError("Expected release archive verification to reject backend/.env")


def test_verify_release_archive_rejects_missing_required_files(tmp_path, monkeypatch):
    archive_path = tmp_path / "release.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("README.md", "keep")
        archive.writestr("VERSION", "9.9.9")

    monkeypatch.setattr(verify_delivery, "RELEASE_ARCHIVE", archive_path)

    try:
        verify_delivery.verify_release_archive()
    except verify_delivery.StepFailed as exc:
        assert "missing required files" in str(exc)
        assert "backend/.env.example" in str(exc)
    else:
        raise AssertionError("Expected release archive verification to reject missing required files")


def test_release_archive_extraction_bootstrap_smoke(tmp_path, monkeypatch):
    archive_path = tmp_path / "release.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("README.md", "keep")
        archive.writestr("VERSION", "9.9.9")
        archive.writestr("backend/.env.example", "BACKEND_TEMPLATE=1\n")
        archive.writestr("backend/requirements.txt", "fastapi\n")
        archive.writestr("backend/main.py", "app = object()\n")
        archive.writestr("frontend/package.json", "{\"name\":\"frontend\"}")
        archive.writestr("frontend/package-lock.json", "{\"name\":\"frontend\",\"lockfileVersion\":3}")
        archive.writestr("start_backend.sh", "#!/usr/bin/env bash\ncd backend\ncp .env.example .env\n")
        archive.writestr("start_frontend.sh", "#!/usr/bin/env bash\ncd frontend\nnpm ci\n")
        archive.writestr(".vscode/launch.json", "{}")
        archive.writestr(".vscode/tasks.json", "{}")
        archive.writestr("docker-compose.yml", "services: {}\n")

    monkeypatch.setattr(verify_delivery, "RELEASE_ARCHIVE", archive_path)

    verify_delivery.verify_release_archive()
    verify_delivery.verify_release_archive_bootstrap_smoke()

    extract_root = tmp_path / "manual-extract"
    with ZipFile(archive_path) as archive:
        archive.extractall(extract_root)
    shutil.copyfile(
        extract_root / "backend" / ".env.example",
        extract_root / "backend" / ".env",
    )
    assert (extract_root / "backend" / ".env").read_text(encoding="utf-8") == "BACKEND_TEMPLATE=1\n"
    assert (extract_root / "backend" / "main.py").exists()
