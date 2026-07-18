"""Create a delivery zip with local secrets and runtime artifacts excluded."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release_file_policy import (  # noqa: E402
    has_virtualenv_marker,
    is_virtualenv_dir_name,
    may_include_in_release_archive,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "dev"


class ReleasePackagingError(RuntimeError):
    """Raised when the release archive cannot be packaged safely."""


def should_skip(relative_path: Path) -> bool:
    return not may_include_in_release_archive(relative_path)


def _iter_release_files() -> list[tuple[Path, Path]]:
    release_files: list[tuple[Path, Path]] = []

    for root, dirnames, filenames in os.walk(REPO_ROOT, topdown=True, followlinks=False):
        root_path = Path(root)

        filtered_dirnames: list[str] = []
        for dirname in dirnames:
            path = root_path / dirname
            relative_path = path.relative_to(REPO_ROOT)
            if path.is_symlink():
                if should_skip(relative_path):
                    continue
                raise ReleasePackagingError(
                    f"Refusing to package symlink: {relative_path.as_posix()}"
                )
            if is_virtualenv_dir_name(dirname) or has_virtualenv_marker(path):
                continue
            if should_skip(relative_path):
                continue
            filtered_dirnames.append(dirname)
        dirnames[:] = filtered_dirnames

        for filename in filenames:
            path = root_path / filename
            relative_path = path.relative_to(REPO_ROOT)
            if path.is_symlink():
                if should_skip(relative_path):
                    continue
                raise ReleasePackagingError(
                    f"Refusing to package symlink: {relative_path.as_posix()}"
                )
            if should_skip(relative_path):
                continue
            release_files.append((path, relative_path))

    return release_files


def build_release_archive() -> Path:
    release_files = _iter_release_files()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = DIST_DIR / f"english-japanese-learning-coach-v{VERSION}.zip"
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f"{archive_path.name}.",
        suffix=".tmp",
        dir=DIST_DIR,
    )
    os.close(temp_fd)
    temp_archive_path = Path(temp_name)

    try:
        with ZipFile(temp_archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for path, relative_path in release_files:
                archive.write(path, arcname=relative_path.as_posix())
        os.replace(temp_archive_path, archive_path)
    except Exception:
        temp_archive_path.unlink(missing_ok=True)
        raise

    return archive_path


def main() -> int:
    try:
        archive_path = build_release_archive()
    except ReleasePackagingError as exc:
        print(f"Release packaging failed: {exc}", file=sys.stderr)
        return 1

    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
