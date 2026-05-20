"""Upload limit coverage for import and RAG endpoints."""

from __future__ import annotations

import io

import pandas as pd
from api_errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from config import settings
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from routers import imports as imports_router


class _StubRag:
    enabled = True
    init_error: str | None = None
    disabled_by_config = False

    def add_material(self, text: str, metadata: dict, *, user_id: str, doc_id=None) -> str:
        return doc_id or "doc-1"

    def list_materials(self, *, user_id: str, language=None):
        return []

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        return False


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(imports_router.router)
    return app


def _excel_bytes() -> bytes:
    output = io.BytesIO()
    df = pd.DataFrame(
        [
            {
                "word": "hello",
                "definition_zh": "你好",
                "example_sentence": "Hello there.",
                "example_translation": "你好啊。",
            }
        ]
    )
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


def test_import_excel_small_file_succeeds(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 1, raising=False)
    client = TestClient(_make_app())

    files = {
        "file": (
            "vocab.xlsx",
            _excel_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    response = client.post("/api/import/excel?language=EN", files=files)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["count"] >= 1


def test_import_excel_rejects_oversized_file_with_413(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 0, raising=False)
    client = TestClient(_make_app())

    files = {
        "file": (
            "vocab.xlsx",
            _excel_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    response = client.post("/api/import/excel?language=EN", files=files)

    assert response.status_code == 413
    body = response.json()
    assert body["code"] == "FILE_TOO_LARGE"
    assert body["detail"] == body["message"]


def test_import_excel_keeps_file_type_errors_separate(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 10, raising=False)
    client = TestClient(_make_app())

    files = {"file": ("vocab.txt", b"word,definition\nhello,hi", "text/plain")}
    response = client.post("/api/import/excel?language=EN", files=files)

    assert response.status_code == 400
    assert response.json()["code"] == "import_unsupported_file_type"


def test_import_excel_rejects_legacy_xls_extension(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 10, raising=False)
    client = TestClient(_make_app())

    files = {"file": ("vocab.xls", b"not-a-real-xls", "application/vnd.ms-excel")}
    response = client.post("/api/import/excel?language=EN", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .xlsx files are supported"


def test_rag_upload_small_file_succeeds(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 1, raising=False)
    monkeypatch.setattr(imports_router, "rag_manager", _StubRag(), raising=False)
    client = TestClient(_make_app())

    files = {"file": ("notes.txt", b"small rag payload", "text/plain")}
    response = client.post("/api/rag/upload?language=EN", files=files)

    assert response.status_code == 200
    assert response.json() == {"success": True, "doc_id": "doc-1"}


def test_rag_upload_rejects_oversized_file_with_413(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 0, raising=False)
    monkeypatch.setattr(imports_router, "rag_manager", _StubRag(), raising=False)
    client = TestClient(_make_app())

    files = {"file": ("notes.txt", b"too large", "text/plain")}
    response = client.post("/api/rag/upload?language=EN", files=files)

    assert response.status_code == 413
    body = response.json()
    assert body["code"] == "FILE_TOO_LARGE"
    assert body["detail"] == body["message"]


def test_rag_upload_rejects_empty_file(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 1, raising=False)
    monkeypatch.setattr(imports_router, "rag_manager", _StubRag(), raising=False)
    client = TestClient(_make_app())

    files = {"file": ("notes.txt", b"", "text/plain")}
    response = client.post("/api/rag/upload?language=EN", files=files)

    assert response.status_code == 400
    assert response.json()["code"] == "rag_file_empty"


def test_rag_disabled_material_list_is_unaffected_by_upload_limit(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 0, raising=False)
    stub = _StubRag()
    stub.enabled = False
    stub.init_error = "RAG is disabled by configuration"
    stub.disabled_by_config = True
    monkeypatch.setattr(imports_router, "rag_manager", stub, raising=False)
    client = TestClient(_make_app())

    response = client.get("/api/rag/materials?language=EN")

    assert response.status_code == 200
    assert response.json() == {"success": True, "items": []}
