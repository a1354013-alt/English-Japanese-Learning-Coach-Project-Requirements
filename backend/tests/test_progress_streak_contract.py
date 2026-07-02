"""Integration coverage for the shared streak/progress source of truth."""

from datetime import datetime
from zoneinfo import ZoneInfo

import database as database_module
import demo_seed as demo_seed_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.lesson_ops as lesson_ops_module
import srs as srs_module
from config import settings
from database import Database
from fastapi import FastAPI
from fastapi.testclient import TestClient
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
    answers = []
    for idx, exercise in enumerate(lesson["grammar"]["exercises"]):
        answers.append(
            {
                "lesson_id": lesson_id,
                "exercise_type": "grammar",
                "question_index": idx,
                "user_answer": exercise["correct_answer"],
                "correct_answer": exercise["correct_answer"],
            }
        )
    for idx, question in enumerate(lesson["reading"]["questions"]):
        answers.append(
            {
                "lesson_id": lesson_id,
                "exercise_type": "reading",
                "question_index": idx,
                "user_answer": question["correct_answer"],
                "correct_answer": question["correct_answer"],
            }
        )

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
    monkeypatch.setattr(settings, "allow_demo_reset", True, raising=False)
    client = TestClient(_make_app())

    reset = client.post("/api/demo/reset")
    assert reset.status_code == 200

    progress = client.get("/api/progress").json()
    streak = client.get("/api/streak").json()
    assert streak["current_streak"] == 3
    assert streak["today_completed"] is True
    assert progress["streak"]["current_streak"] == streak["current_streak"]
    assert progress["progress"]["rpg_stats"]["streak_days"] == streak["current_streak"]


def test_demo_reset_uses_local_timezone_for_streak_seed(tmp_path, monkeypatch):
    _wire_test_db(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "allow_demo_reset", True, raising=False)
    monkeypatch.setattr(settings, "timezone", "Asia/Taipei", raising=False)
    def simulated_now() -> datetime:
        return datetime(2026, 5, 18, 16, 22, tzinfo=ZoneInfo("UTC")).astimezone(
            ZoneInfo(settings.timezone)
        )

    monkeypatch.setattr(database_module, "_local_now", simulated_now, raising=True)
    monkeypatch.setattr(
        demo_seed_module,
        "_local_now",
        simulated_now,
        raising=True,
    )
    client = TestClient(_make_app())

    reset = client.post("/api/demo/reset")
    assert reset.status_code == 200

    streak = client.get("/api/streak").json()
    progress = client.get("/api/progress").json()

    assert streak["current_streak"] == 3
    assert streak["today_completed"] is True
    assert progress["streak"]["current_streak"] == streak["current_streak"]
    assert progress["streak"]["today_completed"] is True
    assert progress["progress"]["rpg_stats"]["streak_days"] == streak["current_streak"]


def test_srs_due_uses_configured_local_timezone(tmp_path, monkeypatch):
    test_db = _wire_test_db(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "timezone", "Asia/Taipei", raising=False)

    due_now = datetime(2026, 5, 19, 0, 30, tzinfo=ZoneInfo(settings.timezone))
    monkeypatch.setattr(database_module, "_local_now", lambda: due_now, raising=True)
    monkeypatch.setattr(srs_module, "local_now", lambda: due_now, raising=True)

    srs_data = srs_module.srs_engine.calculate(
        quality=1,
        prev_interval=0,
        prev_ease_factor=2.5,
        repetition=0,
    )
    test_db.update_srs_item(
        "u1",
        "hello",
        "EN",
        srs_data,
        {"definition_zh": "greeting"},
    )

    before_due = due_now.replace(day=19, hour=23, minute=30)
    monkeypatch.setattr(database_module, "_local_now", lambda: before_due, raising=True)
    assert test_db.get_due_srs_items("u1", language="EN") == []

    after_due = due_now.replace(day=20, hour=0, minute=31)
    monkeypatch.setattr(database_module, "_local_now", lambda: after_due, raising=True)
    due_items = test_db.get_due_srs_items("u1", language="EN")
    assert [item["word"] for item in due_items] == ["hello"]
