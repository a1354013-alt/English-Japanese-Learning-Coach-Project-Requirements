"""Review API must validate payload boundaries and return clear 4xx errors."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database as database_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.lesson_ops as lesson_ops_module
from database import Database
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
    return app


def _setup_isolated_app(tmp_path, monkeypatch) -> TestClient:
    test_db = Database(str(tmp_path / "t.db"))

    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)

    gen = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(gen, "_generate_with_model", _FailingModel()._generate_with_model, raising=True)
    monkeypatch.setattr(lessons_router, "lesson_generator", gen, raising=False)

    return TestClient(_make_app())


def test_review_rejects_mixed_lesson_id(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    r_gen = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Validation"})
    lesson = r_gen.json()["lesson"]
    lesson_id = lesson["metadata"]["lesson_id"]

    g0 = lesson["grammar"]["exercises"][0]
    answers = [
        {
            "lesson_id": lesson_id,
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": g0["correct_answer"],
            "correct_answer": g0["correct_answer"],
        },
        {
            "lesson_id": "different",
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": g0["correct_answer"],
            "correct_answer": g0["correct_answer"],
        },
    ]

    r = client.post("/api/review", json=answers)
    assert r.status_code == 400
    assert "mixed lesson_id" in r.json()["detail"]


def test_review_rejects_duplicate_answers(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Dup"}).json()["lesson"]
    lesson_id = lesson["metadata"]["lesson_id"]
    g0 = lesson["grammar"]["exercises"][0]

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
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": g0["correct_answer"],
            "correct_answer": g0["correct_answer"],
        },
    ]
    r = client.post("/api/review", json=answers)
    assert r.status_code == 400
    assert "duplicate answer" in r.json()["detail"]


def test_review_rejects_out_of_range_indexes(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Range"}).json()["lesson"]
    lesson_id = lesson["metadata"]["lesson_id"]

    answers = [
        {
            "lesson_id": lesson_id,
            "exercise_type": "grammar",
            "question_index": 999,
            "user_answer": "A",
            "correct_answer": "B",
        }
    ]
    r = client.post("/api/review", json=answers)
    assert r.status_code == 400
    assert "out of range" in r.json()["detail"]


def test_review_rejects_correct_answer_mismatch(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Mismatch"}).json()["lesson"]
    lesson_id = lesson["metadata"]["lesson_id"]
    g0 = lesson["grammar"]["exercises"][0]

    answers = [
        {
            "lesson_id": lesson_id,
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": g0["correct_answer"],
            "correct_answer": "tampered",
        }
    ]
    r = client.post("/api/review", json=answers)
    assert r.status_code == 400
    assert "correct_answer mismatch" in r.json()["detail"]


def test_review_rejects_blank_user_answer(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Blank"}).json()["lesson"]
    lesson_id = lesson["metadata"]["lesson_id"]
    g0 = lesson["grammar"]["exercises"][0]

    answers = [
        {
            "lesson_id": lesson_id,
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": "   ",
            "correct_answer": g0["correct_answer"],
        }
    ]
    r = client.post("/api/review", json=answers)
    assert r.status_code == 400
    assert "user_answer must be non-empty" in r.json()["detail"]

