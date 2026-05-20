"""Create a delivery zip with runtime and cache directories excluded."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "dev"

EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".playwright-data",
    "coverage",
    "dist",
}
EXCLUDED_FILE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDED_RUNTIME_PREFIXES = (
    ("data", "chroma_db"),
    ("data", "audio"),
    ("data", "exports"),
    ("data", "lessons"),
    ("frontend", "test-results"),
    ("frontend", "playwright-report"),
    ("frontend", "coverage"),
)


def should_skip(relative_path: Path) -> bool:
    parts = relative_path.parts
    if set(parts) & EXCLUDED_DIR_NAMES:
        return True
    if any(part.endswith(".egg-info") for part in relative_path.parts):
        return True
    if relative_path.suffix in EXCLUDED_FILE_SUFFIXES:
        return True
    if relative_path.name.endswith((".db", ".db-wal", ".db-shm")) and parts[:1] == ("data",):
        return True
    if any(parts[: len(prefix)] == prefix for prefix in EXCLUDED_RUNTIME_PREFIXES):
        return True
    return False


def main() -> int:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = DIST_DIR / f"english-japanese-learning-coach-v{VERSION}.zip"
    if archive_path.exists():
        archive_path.unlink()

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in REPO_ROOT.rglob("*"):
            if path.is_dir():
                continue
            relative_path = path.relative_to(REPO_ROOT)
            if should_skip(relative_path):
                continue
            archive.write(path, arcname=relative_path.as_posix())

    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
