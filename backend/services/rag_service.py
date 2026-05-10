"""Upload parsing helpers for RAG materials."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from pypdf import PdfReader


TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "cp932", "big5")


def extract_text_from_upload(filename: str, contents: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(contents))
        parts = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(part.strip() for part in parts if part and part.strip()).strip()

    decoded_text: str | None = None
    for encoding in TEXT_ENCODINGS:
        try:
            decoded_text = contents.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if decoded_text is None:
        decoded_text = contents.decode("utf-8", errors="replace")
    return decoded_text.strip()


def build_material_metadata(*, filename: str, language: str, source_type: str | None = None) -> Dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    resolved_source_type = source_type or ("pdf" if suffix == ".pdf" else "text")
    timestamp = datetime.now().isoformat()
    return {
        "title": Path(filename).name or "unknown",
        "source": Path(filename).name or "unknown",
        "language": language,
        "source_type": resolved_source_type,
        "uploaded_at": timestamp,
    }

