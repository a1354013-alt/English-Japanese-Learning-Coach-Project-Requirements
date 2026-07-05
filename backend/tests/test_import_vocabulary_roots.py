"""Imported vocabulary root/category fields flow into list and SRS due APIs."""

from __future__ import annotations

import io

import gamification_engine as gamification_module
import pandas as pd
from config import settings
from database import Database
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import imports as imports_router
from routers import review as review_router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(imports_router.router)
    app.include_router(review_router.router)
    return app


def _excel_bytes(rows: list[dict]) -> bytes:
    output = io.BytesIO()
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


def test_imported_vocabulary_roots_categories_and_tags_round_trip(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "import-roots.db"))
    monkeypatch.setattr(imports_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(settings, "max_upload_size_mb", 1, raising=False)

    client = TestClient(_make_app())
    files = {
        "file": (
            "vocab.xlsx",
            _excel_bytes(
                [
                    {
                        "word": "review",
                        "definition_zh": "複習",
                        "example_sentence": "I review words.",
                        "example_translation": "我複習單字。",
                        "part_of_speech": "verb",
                        "root": "view",
                        "prefix": "re-",
                        "suffix": "",
                        "word_family": "review, reviewer",
                        "memory_tip": "re- means again.",
                        "category": "study",
                        "tags": "root, habit",
                    }
                ]
            ),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = client.post("/api/import/excel?language=EN", files=files)
    assert response.status_code == 200
    assert response.json() == {"success": True, "count": 1}

    listed = client.get("/api/imported-vocabulary?language=EN")
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["part_of_speech"] == "verb"
    assert item["root"] == "view"
    assert item["prefix"] == "re-"
    assert item["word_family"] == ["review", "reviewer"]
    assert item["memory_tip"] == "re- means again."
    assert item["category"] == "study"
    assert item["tags"] == ["root", "habit"]
    assert item["mastery_state"] == "new"

    for query in ("view", "study", "habit"):
        searched = client.get(f"/api/imported-vocabulary?language=EN&q={query}")
        assert searched.status_code == 200
        assert searched.json()["count"] == 1
        assert searched.json()["items"][0]["word"] == "review"

    with test_db.get_connection() as conn:
        conn.execute(
            "UPDATE srs_vocabulary SET next_review = ? WHERE user_id = ? AND word = ? AND language = ?",
            ("2020-01-01T00:00:00", settings.default_user_id, "review", "EN"),
        )

    due = client.get("/api/srs/due?language=EN")
    assert due.status_code == 200
    due_item = due.json()["items"][0]
    assert due_item["word"] == "review"
    assert due_item["root"] == "view"
    assert due_item["memory_tip"] == "re- means again."
    assert due_item["category"] == "study"
    assert due_item["tags"] == ["root", "habit"]
