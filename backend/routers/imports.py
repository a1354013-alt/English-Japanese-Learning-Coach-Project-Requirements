"""Vocabulary import, RAG material upload, and lesson PDF export."""
import io
from typing import Literal

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from config import settings
from database import db
from export_service import pdf_exporter
from gamification_engine import gamification_engine
from rag_manager import rag_manager
from srs import srs_engine
from services.lesson_ops import load_lesson_payload

router = APIRouter(prefix="/api", tags=["imports"])


@router.post("/import/excel")
async def import_excel(
    language: Literal["EN", "JP"] = "EN",
    file: UploadFile = File(...),
    user_id: str = "default_user",
):
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {err}") from err

    column_map = {str(c).strip().lower(): c for c in df.columns}
    if "word" not in column_map:
        raise HTTPException(status_code=400, detail="Excel must include a 'word' column")

    definition_col = column_map.get("definition_zh") or column_map.get("definition")
    if not definition_col:
        raise HTTPException(status_code=400, detail="Excel must include 'definition' or 'definition_zh' column")

    reading_col = column_map.get("reading")
    example_col = column_map.get("example_sentence") or column_map.get("example")
    translation_col = column_map.get("example_translation")

    imported_count = 0
    for _, row in df.iterrows():
        word = str(row[column_map["word"]]).strip()
        definition_zh = str(row[definition_col]).strip()
        if not word or not definition_zh or word.lower() == "nan":
            continue

        vocab_item = {
            "word": word,
            "reading": str(row[reading_col]).strip() if reading_col and not pd.isna(row[reading_col]) else None,
            "definition_zh": definition_zh,
            "example_sentence": str(row[example_col]).strip() if example_col and not pd.isna(row[example_col]) else "",
            "example_translation": str(row[translation_col]).strip()
            if translation_col and not pd.isna(row[translation_col])
            else "",
        }

        db.save_imported_vocabulary(user_id, language, vocab_item)
        gamification_engine.collect_word_cards(user_id, [word], language)

        prev = db.get_srs_item(user_id, word, language)
        srs_data = srs_engine.calculate(
            quality=3,
            prev_interval=int(prev["interval"]) if prev else 0,
            prev_ease_factor=float(prev["ease_factor"]) if prev else 2.5,
            repetition=int(prev["srs_level"]) if prev else 0,
        )
        db.update_srs_item(user_id, word, language, srs_data, vocab_item)
        imported_count += 1

    return {"success": True, "count": imported_count}


@router.post("/rag/upload")
async def upload_rag_material(language: Literal["EN", "JP"], file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith((".txt", ".md", ".csv")):
        raise HTTPException(status_code=400, detail="Only .txt, .md, and .csv files are supported")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    decoded_text = None
    for encoding in ("utf-8", "utf-8-sig", "cp932", "big5"):
        try:
            decoded_text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if decoded_text is None:
        decoded_text = raw.decode("utf-8", errors="replace")

    rag_manager.add_material(decoded_text, metadata={"language": language, "source": file.filename or "unknown"})
    return {"success": True}


@router.get("/export/pdf/{lesson_id}")
async def export_lesson_pdf(lesson_id: str):
    lesson_data = load_lesson_payload(lesson_id)
    pdf_path = pdf_exporter.export_lesson(lesson_data)
    return FileResponse(pdf_path, filename=f"lesson_{lesson_id}.pdf")
