"""Integration-ish tests for review submission dedupe (single-user demo rules)."""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database as database_module
import gamification_engine as gamification_module
import services.lesson_ops as lesson_ops_module
from database import Database
from routers import review as review_router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(review_router.router)
    return app


def _seed_minimal_lesson(db: Database, tmp_path: Path, *, user_id: str) -> str:
    lesson_id = "lesson_1"
    payload = {
        "metadata": {
            "lesson_id": lesson_id,
            "language": "EN",
            "level": "A1",
            "topic": "Test",
            "generated_at": "2026-04-21T00:00:00",
            "estimated_duration_minutes": 10,
            "key_points": ["k1"],
        },
        "vocabulary": [{"word": "hello", "definition_zh": "你好", "example_sentence": "hello", "example_translation": "你好"}],
        "grammar": {"title": "G", "explanation": "", "examples": [], "exercises": [{"question": "Q", "correct_answer": "A", "explanation": "E"}]},
        "reading": {"title": "R", "content": "", "word_count": 0, "questions": []},
        "dialogue": {"scenario": "D", "context": "C", "dialogue": [], "alternatives": []},
    }
    lesson_file = tmp_path / "lesson.json"
    lesson_file.write_text(json.dumps(payload), encoding="utf-8")
    db.save_lesson(payload, str(lesson_file), user_id=user_id)
    return lesson_id


def test_review_double_submit_does_not_farm_xp_or_progress(tmp_path, monkeypatch):
    # Isolate globals to a temp DB for this test.
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)

    user_id = "default_user"
    lesson_id = _seed_minimal_lesson(test_db, tmp_path, user_id=user_id)

    app = _make_app()
    client = TestClient(app)

    answers = [{"lesson_id": lesson_id, "exercise_type": "grammar", "question_index": 0, "user_answer": "A", "correct_answer": "A"}]

    r1 = client.post("/api/review", json=answers)
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["success"] is True
    assert body1["gamification"]["xp_added"] > 0

    p1 = test_db.get_progress(user_id)
    assert p1["english_progress"]["completed_lessons"] == 1
    assert p1["english_progress"]["total_exercises"] == 1

    # Second submission: updates latest exercise_result but must not add xp/progress.
    r2 = client.post("/api/review", json=answers)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["success"] is True
    assert body2["gamification"]["xp_added"] == 0

    p2 = test_db.get_progress(user_id)
    assert p2["english_progress"]["completed_lessons"] == 1
    assert p2["english_progress"]["total_exercises"] == 1

