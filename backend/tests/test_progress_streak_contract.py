"""Integration coverage for the shared streak/progress source of truth."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database as database_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.lesson_ops as lesson_ops_module
from config import settings
from database import Database
from routers import lessons as lessons_router
from routers import review as review_router
from routers import streak as streak_router
from routers import system as system_router


class _FailingModel:
    async def _generate_with_model(self, **kwargs):  # pragma: no cover - exercised via router
        raise RuntimeError("no model in tests")


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(lessons_router.router)
    app.include_router(review_router.router)
    app.include_router(streak_router.router)
    return app


def _wire_test_db(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"), raising=False)
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(streak_router, "db", test_db, raising=False)

    gen = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(gen, "_generate_with_model", _FailingModel()._generate_with_model, raising=True)
    monkeypatch.setattr(lessons_router, "lesson_generator", gen, raising=False)
    return test_db


def test_review_updates_progress_and_streak_from_same_source(tmp_path, monkeypatch):
    _wire_test_db(tmp_path, monkeypatch)
    client = TestClient(_make_app())

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Streak"}).json()["lesson"]
    lesson_id = lesson["metadata"]["lesson_id"]
    answers = [
        {
            "lesson_id": lesson_id,
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": lesson["grammar"]["exercises"][0]["correct_answer"],
            "correct_answer": lesson["grammar"]["exercises"][0]["correct_answer"],
        },
        {
            "lesson_id": lesson_id,
            "exercise_type": "reading",
            "question_index": 0,
            "user_answer": lesson["reading"]["questions"][0]["correct_answer"],
            "correct_answer": lesson["reading"]["questions"][0]["correct_answer"],
        },
    ]

    review = client.post("/api/review", json=answers)
    assert review.status_code == 200

    progress = client.get("/api/progress")
    streak = client.get("/api/streak")
    assert progress.status_code == 200
    assert streak.status_code == 200

    progress_body = progress.json()
    streak_body = streak.json()
    assert progress_body["streak"]["current_streak"] == streak_body["current_streak"]
    assert progress_body["streak"]["longest_streak"] == streak_body["longest_streak"]
    assert progress_body["streak"]["today_completed"] is True
    assert progress_body["progress"]["rpg_stats"]["streak_days"] == streak_body["current_streak"]


def test_demo_reset_restores_reasonable_streak_state(tmp_path, monkeypatch):
    _wire_test_db(tmp_path, monkeypatch)
    client = TestClient(_make_app())

    reset = client.post("/api/demo/reset")
    assert reset.status_code == 200

    progress = client.get("/api/progress").json()
    streak = client.get("/api/streak").json()
    assert streak["current_streak"] == 3
    assert streak["today_completed"] is True
    assert progress["streak"]["current_streak"] == streak["current_streak"]
    assert progress["progress"]["rpg_stats"]["streak_days"] == streak["current_streak"]
