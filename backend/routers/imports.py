"""Vocabulary import, RAG material upload, and lesson PDF export."""
import io
from typing import Any

import pandas as pd
from api_errors import COMMON_ERROR_RESPONSES, api_error
from config import settings
from database import db
from export_service import pdf_exporter
from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from gamification_engine import gamification_engine
from models import (
    ImportedVocabularyListResponse,
    ImportExcelResponse,
    LanguageCode,
    RagMaterialsResponse,
    RagUploadResponse,
    SuccessResponse,
)
from rag_manager import rag_manager
from services.learning_intelligence import sync_imported_vocabulary_item
from services.lesson_ops import load_lesson_payload
from services.rag_service import build_material_metadata, extract_text_from_upload
from srs import srs_engine

from routers.deps import require_demo_user_id

router = APIRouter(prefix="/api", tags=["imports"], responses=COMMON_ERROR_RESPONSES)


def _excel_text(value, *, allow_empty: bool = False) -> str | None:
    if pd.isna(value):
        return "" if allow_empty else None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return "" if allow_empty else None
    return text


def _excel_list(value) -> list[str]:
    text = _excel_text(value, allow_empty=True)
    if not text:
        return []
    return [part.strip() for part in str(text).replace(";", ",").split(",") if part.strip()]


def _normalize_material_item(item: dict) -> dict:
    material_id = str(item.get("material_id") or item.get("doc_id") or "")
    return {
        **item,
        "material_id": material_id,
        "doc_id": str(item.get("doc_id") or material_id),
        "title": str(item.get("title") or item.get("source") or "unknown"),
        "source_type": str(item.get("source_type") or "text"),
        "total_chunks": int(item.get("total_chunks", 1) or 1),
    }


async def _read_upload_with_size_limit(file: UploadFile) -> bytes:
    max_bytes = settings.max_upload_size_bytes
    if max_bytes <= 0:
        raise api_error(
            413,
            f"Uploaded file exceeds the {settings.max_upload_size_mb} MB limit",
            "FILE_TOO_LARGE",
        )

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise api_error(
                413,
                f"Uploaded file exceeds the {settings.max_upload_size_mb} MB limit",
                "FILE_TOO_LARGE",
            )
        chunks.append(chunk)

    await file.seek(0)
    return b"".join(chunks)


@router.post("/import/excel", response_model=ImportExcelResponse)
async def import_excel(
    language: LanguageCode = "EN",
    file: UploadFile = File(...),
    user_id: str = Depends(require_demo_user_id),
):
    filename = (file.filename or "").lower()
    if not filename.endswith(".xlsx"):
        raise api_error(400, "Only .xlsx files are supported", "import_unsupported_file_type")

    contents = await _read_upload_with_size_limit(file)
    if not contents:
        raise api_error(400, "Uploaded file is empty", "import_file_empty")
    try:
        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
    except Exception as err:
        raise api_error(400, f"Invalid Excel file: {err}", "invalid_excel_file") from err

    column_map = {str(c).strip().lower(): c for c in df.columns}
    if "word" not in column_map:
        raise api_error(400, "Excel must include a 'word' column", "excel_word_column_required")

    definition_col = column_map.get("definition_zh") or column_map.get("definition")
    if not definition_col:
        raise api_error(400, "Excel must include 'definition' or 'definition_zh' column", "excel_definition_column_required")

    reading_col = column_map.get("reading")
    example_col = column_map.get("example_sentence") or column_map.get("example")
    translation_col = column_map.get("example_translation")
    optional_text_cols = {
        name: column_map.get(name)
        for name in (
            "part_of_speech",
            "root",
            "prefix",
            "suffix",
            "memory_tip",
            "category",
            "source_lesson_id",
            "mastery_state",
        )
    }
    optional_list_cols = {
        name: column_map.get(name)
        for name in (
            "word_family",
            "tags",
        )
    }

    imported_count = 0
    for _, row in df.iterrows():
        word = _excel_text(row[column_map["word"]])
        definition_zh = _excel_text(row[definition_col])
        if not word or not definition_zh:
            continue

        vocab_item: dict[str, Any] = {
            "word": word,
            "reading": _excel_text(row[reading_col]) if reading_col else None,
            "definition_zh": definition_zh,
            "example_sentence": _excel_text(row[example_col], allow_empty=True) if example_col else "",
            "example_translation": _excel_text(row[translation_col], allow_empty=True) if translation_col else "",
        }
        for field, col in optional_text_cols.items():
            if col:
                value = _excel_text(row[col], allow_empty=True)
                if value:
                    vocab_item[field] = value
        for field, col in optional_list_cols.items():
            if col:
                vocab_item[field] = _excel_list(row[col])

        db.save_imported_vocabulary(user_id, language, vocab_item)
        sync_imported_vocabulary_item(user_id=user_id, language=language, item=vocab_item)
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


@router.post("/rag/upload", response_model=RagUploadResponse)
async def upload_rag_material(
    language: LanguageCode,
    file: UploadFile = File(...),
    user_id: str = Depends(require_demo_user_id),
):
    if not rag_manager.enabled:
        raise api_error(503, rag_manager.init_error or "RAG is disabled", "rag_unavailable")
    filename = (file.filename or "").lower()
    if not filename.endswith((".txt", ".md", ".csv", ".pdf")):
        raise api_error(400, "Only .txt, .md, .csv, and .pdf files are supported", "rag_unsupported_file_type")

    raw = await _read_upload_with_size_limit(file)
    if not raw:
        raise api_error(400, "Uploaded file is empty", "rag_file_empty")

    decoded_text = extract_text_from_upload(file.filename or "unknown", raw)
    if not decoded_text:
        raise api_error(400, "Uploaded file does not contain readable text", "rag_file_empty")

    doc_id = rag_manager.add_material(
        decoded_text,
        metadata=build_material_metadata(filename=file.filename or "unknown", language=language),
        user_id=user_id,
    )
    return {"success": True, "doc_id": doc_id}


@router.get("/rag/materials", response_model=RagMaterialsResponse)
async def list_rag_materials(
    language: LanguageCode | None = None,
    user_id: str = Depends(require_demo_user_id),
):
    if not rag_manager.enabled and not getattr(rag_manager, "disabled_by_config", False):
        raise api_error(503, rag_manager.init_error or "RAG is unavailable", "rag_unavailable")
    items = [_normalize_material_item(item) for item in rag_manager.list_materials(user_id=user_id, language=language)]
    return {"success": True, "items": items}


@router.delete("/rag/materials/{doc_id}", response_model=SuccessResponse)
async def delete_rag_material(doc_id: str, user_id: str = Depends(require_demo_user_id)):
    if not rag_manager.enabled:
        raise api_error(503, rag_manager.init_error or "RAG is disabled", "rag_unavailable")
    try:
        ok = rag_manager.delete_material(user_id=user_id, doc_id=doc_id)
    except Exception as err:
        raise api_error(500, f"Failed to delete material: {err}", "rag_delete_failed") from err
    if not ok:
        raise api_error(404, "Material not found", "rag_material_not_found")
    return {"success": True}


@router.get("/imported-vocabulary", response_model=ImportedVocabularyListResponse)
async def list_imported_vocabulary(
    language: LanguageCode | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(require_demo_user_id),
):
    items, count = db.list_imported_vocabulary(user_id=user_id, language=language, q=q, limit=limit, offset=offset)
    return {"success": True, "count": count, "items": items}


@router.delete("/imported-vocabulary/{item_id}", response_model=SuccessResponse)
async def delete_imported_vocabulary(item_id: int, user_id: str = Depends(require_demo_user_id)):
    ok = db.delete_imported_vocabulary(user_id=user_id, item_id=item_id)
    if not ok:
        raise api_error(404, "Imported vocabulary item not found", "imported_vocabulary_not_found")
    return {"success": True}


@router.get("/export/pdf/{lesson_id}")
async def export_lesson_pdf(lesson_id: str, user_id: str = Depends(require_demo_user_id)):
    lesson_data = load_lesson_payload(lesson_id, user_id=user_id)
    pdf_path = pdf_exporter.export_lesson(lesson_data)
    return FileResponse(pdf_path, filename=f"lesson_{lesson_id}.pdf", media_type="application/pdf")
