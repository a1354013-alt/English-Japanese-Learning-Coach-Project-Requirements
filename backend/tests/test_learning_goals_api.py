from __future__ import annotations

import database as database_module
from database import Database
from fastapi.testclient import TestClient
from main import app
from models import LearningSessionEventMetadata
from routers import learning_goals as learning_goals_router


def _patch_db(monkeypatch, tmp_path) -> Database:
    test_db = Database(str(tmp_path / "learning-goals.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(learning_goals_router, "db", test_db, raising=False)
    return test_db


def test_learning_goals_get_put_and_validation(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    client = TestClient(app)

    default_goal = client.get("/api/learning-goals?language=EN")
    assert default_goal.status_code == 200
    assert default_goal.json()["goal"]["daily_minutes"] == 20

    updated = client.put(
        "/api/learning-goals?language=EN",
        json={"daily_minutes": 30, "weekly_sessions": 5, "weekly_minutes": 150},
    )
    assert updated.status_code == 200
    assert updated.json()["goal"]["weekly_sessions"] == 5

    invalid = client.put(
        "/api/learning-goals?language=EN",
        json={"daily_minutes": 0, "weekly_sessions": 5, "weekly_minutes": 150},
    )
    assert invalid.status_code == 422


def test_weekly_insight_uses_monday_boundary_and_deterministic_counts(monkeypatch, tmp_path):
    test_db = _patch_db(monkeypatch, tmp_path)
    client = TestClient(app)
    test_db.upsert_learning_goal(
        user_id="default_user",
        language="EN",
        daily_minutes=10,
        weekly_sessions=2,
        weekly_minutes=30,
    )
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=10,
    )
    test_db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type="review_answered",
        entity_type="review",
        entity_id="review-1",
        idempotency_key="review-1",
        metadata=LearningSessionEventMetadata(correct=True),
    )
    test_db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type="lesson_completed",
        entity_type="lesson",
        entity_id="lesson-1",
        idempotency_key="lesson-1",
    )
    test_db.learning_session_repository.complete_session(
        session_id=session.session_id,
        user_id="default_user",
        idempotency_key="complete-1",
    )

    response = client.get("/api/learning-insights/weekly?language=EN")

    assert response.status_code == 200
    insight = response.json()["insight"]
    assert insight["week_start"].startswith("2026-07-20")
    assert insight["week_end"].startswith("2026-07-27")
    assert insight["completed_session_count"] == 1
    assert insight["abandoned_session_count"] == 0
    assert insight["event_counts_by_type"]["review_answered"] == 1
    assert insight["lesson_completion_count"] == 1
    assert insight["review_correctness_rate"] == 100.0
    assert insight["weekly_session_goal_progress"] == 0.5
    assert len(insight["recent_completed_sessions"]) == 1
