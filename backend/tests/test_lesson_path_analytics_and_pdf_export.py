"""Lesson file key portability + analytics + PDF export smoke tests."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database as database_module
import export_service as export_service_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.lesson_ops as lesson_ops_module
from database import Database
from export_service import PDFExporter
from routers import imports as imports_router
from routers import lessons as lessons_router
from routers import review as review_router
from routers import system as system_router


class _FailingModel:
    async def _generate_with_model(self, **kwargs):  # pragma: no cover
        raise RuntimeError("no model in tests")


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(lessons_router.router)
    app.include_router(review_router.router)
    app.include_router(imports_router.router)
    return app


def test_lesson_file_path_is_portable_key_and_loadable(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))

    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(imports_router, "db", test_db, raising=False)

    gen = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(gen, "_generate_with_model", _FailingModel()._generate_with_model, raising=True)
    monkeypatch.setattr(lessons_router, "lesson_generator", gen, raising=False)

    client = TestClient(_make_app())
    r_gen = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "PathKey"})
    assert r_gen.status_code == 200
    lesson_id = r_gen.json()["lesson"]["metadata"]["lesson_id"]

    meta = test_db.get_lesson(lesson_id, user_id="default_user")
    assert meta is not None
    stored = str(meta["file_path"])
    assert not Path(stored).is_absolute()
    assert stored.replace("\\", "/").startswith("lessons/")

    # Must be loadable through the API.
    r_get = client.get(f"/api/lessons/{lesson_id}")
    assert r_get.status_code == 200
    assert r_get.json()["lesson"]["metadata"]["lesson_id"] == lesson_id


def test_analytics_computes_from_db_sources(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))

    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(imports_router, "db", test_db, raising=False)

    gen = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(gen, "_generate_with_model", _FailingModel()._generate_with_model, raising=True)
    monkeypatch.setattr(lessons_router, "lesson_generator", gen, raising=False)

    client = TestClient(_make_app())

    # Generate + review once to create progress/exercise_result sources.
    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Analytics"}).json()["lesson"]
    lesson_id = lesson["metadata"]["lesson_id"]
    g0 = lesson["grammar"]["exercises"][0]
    r0 = lesson["reading"]["questions"][0]
    answers = [
        {
            "lesson_id": lesson_id,
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": g0["correct_answer"],
            "correct_answer": g0["correct_answer"],
        },
        {
            "lesson_id": lesson_id,
            "exercise_type": "reading",
            "question_index": 0,
            "user_answer": r0["correct_answer"],
            "correct_answer": r0["correct_answer"],
        },
    ]
    r_review = client.post("/api/review", json=answers)
    assert r_review.status_code == 200

    # Seed wrong answers to drive hardest_words/weakest_category.
    test_db.upsert_wrong_answer(
        user_id="default_user",
        language="EN",
        question_type="grammar",
        question="Hardest prompt",
        user_answer="A",
        correct_answer="B",
        source_lesson_id=lesson_id,
    )
    test_db.upsert_wrong_answer(
        user_id="default_user",
        language="EN",
        question_type="grammar",
        question="Hardest prompt",
        user_answer="C",
        correct_answer="B",
        source_lesson_id=lesson_id,
    )

    r = client.get("/api/analytics")
    assert r.status_code == 200
    payload = r.json()["analytics"]
    assert payload["lessons_completed"] >= 1
    assert isinstance(payload["accuracy_trend"], list)
    assert payload["hardest_words"]
    assert payload["hardest_words"][0]["mistakes"] >= 1


def test_pdf_export_endpoint_returns_pdf(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))

    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(imports_router, "db", test_db, raising=False)

    # Route PDF exports into tmp to avoid polluting the repo.
    exporter = PDFExporter(output_dir=str(tmp_path / "exports"))
    monkeypatch.setattr(export_service_module, "pdf_exporter", exporter, raising=False)
    monkeypatch.setattr(imports_router, "pdf_exporter", exporter, raising=False)

    gen = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(gen, "_generate_with_model", _FailingModel()._generate_with_model, raising=True)
    monkeypatch.setattr(lessons_router, "lesson_generator", gen, raising=False)

    client = TestClient(_make_app())
    lesson_id = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "PDF"}).json()["lesson"]["metadata"]["lesson_id"]

    r = client.get(f"/api/export/pdf/{lesson_id}")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
