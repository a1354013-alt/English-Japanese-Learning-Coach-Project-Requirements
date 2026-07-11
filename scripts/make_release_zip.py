"""Create a delivery zip with local secrets and runtime artifacts excluded."""

from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release_file_policy import may_include_in_release_archive  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "dev"


def should_skip(relative_path: Path) -> bool:
    return not may_include_in_release_archive(relative_path)


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
