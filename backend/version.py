"""Application version helpers."""

from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"


@lru_cache(maxsize=1)
def get_app_version() -> str:
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"
    return version or "dev"
