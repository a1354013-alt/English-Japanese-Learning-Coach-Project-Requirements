from __future__ import annotations

import json

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


def test_weekly_insight_week_start_validation_is_structured(monkeypatch, tmp_path):
    _patch_db(monkeypatch, tmp_path)
    client = TestClient(app)

    valid_midweek = client.get("/api/learning-insights/weekly?language=EN&week_start=2026-07-22")
    assert valid_midweek.status_code == 200
    assert valid_midweek.json()["insight"]["week_start"].startswith("2026-07-20")

    invalid_text = client.get("/api/learning-insights/weekly?language=EN&week_start=not-a-date")
    assert invalid_text.status_code == 422
    assert invalid_text.json()["detail"][0]["type"] == "date_from_datetime_parsing"

    invalid_month = client.get("/api/learning-insights/weekly?language=EN&week_start=2026-13-01")
    assert invalid_month.status_code == 422
    assert invalid_month.json()["detail"][0]["type"] == "date_from_datetime_parsing"

    invalid_day = client.get("/api/learning-insights/weekly?language=EN&week_start=2026-02-30")
    assert invalid_day.status_code == 422
    assert invalid_day.json()["detail"][0]["type"] == "date_from_datetime_parsing"

    leap_day = client.get("/api/learning-insights/weekly?language=EN&week_start=2028-02-29")
    assert leap_day.status_code == 200
    assert leap_day.json()["insight"]["week_start"].startswith("2028-02-28")


def _finalized_session_with_event(
    test_db: Database,
    *,
    session_idempotency_suffix: str,
    started_at: str,
    ended_at: str,
    duration_seconds: int,
    event_occurred_at: str,
    event_type: str = "lesson_completed",
):
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=10,
    )
    event = test_db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type=event_type,
        entity_type="lesson" if event_type == "lesson_completed" else "review",
        entity_id=f"entity-{session_idempotency_suffix}",
        idempotency_key=f"event-{session_idempotency_suffix}",
        metadata=(
            LearningSessionEventMetadata(correct=True)
            if event_type == "review_answered"
            else None
        ),
    )
    test_db.learning_session_repository.complete_session(
        session_id=session.session_id,
        user_id="default_user",
        idempotency_key=f"complete-{session_idempotency_suffix}",
    )
    with test_db.get_connection() as conn:
        conn.execute(
            """
            UPDATE learning_sessions
            SET started_at = ?, ended_at = ?, duration_seconds = ?
            WHERE session_id = ?
            """,
            (started_at, ended_at, duration_seconds, session.session_id),
        )
        conn.execute(
            "UPDATE learning_session_events SET occurred_at = ? WHERE event_id = ?",
            (event_occurred_at, event.event_id),
        )
    return session


def test_weekly_insight_attributes_sessions_by_end_and_events_by_occurrence(monkeypatch, tmp_path):
    test_db = _patch_db(monkeypatch, tmp_path)
    client = TestClient(app)
    test_db.upsert_learning_goal(
        user_id="default_user",
        language="EN",
        daily_minutes=10,
        weekly_sessions=4,
        weekly_minutes=60,
    )

    sunday_to_monday = _finalized_session_with_event(
        test_db,
        session_idempotency_suffix="sunday-to-monday",
        started_at="2026-07-19T23:50:00+08:00",
        ended_at="2026-07-20T00:10:00+08:00",
        duration_seconds=1200,
        event_occurred_at="2026-07-19T23:55:00+08:00",
    )
    inside_to_next = _finalized_session_with_event(
        test_db,
        session_idempotency_suffix="inside-to-next",
        started_at="2026-07-26T23:50:00+08:00",
        ended_at="2026-07-27T00:10:00+08:00",
        duration_seconds=1200,
        event_occurred_at="2026-07-26T23:55:00+08:00",
    )
    inside = _finalized_session_with_event(
        test_db,
        session_idempotency_suffix="inside",
        started_at="2026-07-21T10:00:00+08:00",
        ended_at="2026-07-21T10:20:00+08:00",
        duration_seconds=1200,
        event_occurred_at="2026-07-21T10:05:00+08:00",
        event_type="review_answered",
    )

    response = client.get("/api/learning-insights/weekly?language=EN&week_start=2026-07-20")

    assert response.status_code == 200
    insight = response.json()["insight"]
    assert insight["completed_session_count"] == 2
    assert insight["total_completed_duration_seconds"] == 2400
    assert insight["event_counts_by_type"]["lesson_completed"] == 1
    assert insight["event_counts_by_type"]["review_answered"] == 1
    assert insight["most_active_day"] == "2026-07-21"
    recent_ids = [item["session_id"] for item in insight["recent_completed_sessions"]]
    assert sunday_to_monday.session_id in recent_ids
    assert inside.session_id in recent_ids
    assert inside_to_next.session_id not in recent_ids


def test_weekly_insight_does_not_invent_review_correctness_when_metadata_missing(monkeypatch, tmp_path):
    test_db = _patch_db(monkeypatch, tmp_path)
    client = TestClient(app)
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=10,
    )
    with test_db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO learning_session_events (
                event_id, session_id, event_type, entity_type, entity_id,
                sequence_number, metadata_json, idempotency_key, occurred_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "event-review-missing-correctness",
                session.session_id,
                "review_answered",
                "review",
                "review-missing-correctness",
                1,
                json.dumps({"note": "legacy review metadata"}),
                "review-missing-correctness",
                "2026-07-24T08:01:00+08:00",
                "2026-07-24T08:01:00+08:00",
            ),
        )
    test_db.learning_session_repository.complete_session(
        session_id=session.session_id,
        user_id="default_user",
        idempotency_key="complete-missing-correctness",
    )

    response = client.get("/api/learning-insights/weekly?language=EN&week_start=2026-07-20")

    assert response.status_code == 200
    insight = response.json()["insight"]
    assert insight["review_answer_count"] == 1
    assert insight["correct_review_answer_count"] == 0
    assert insight["review_correctness_rate"] is None


def test_weekly_insight_uses_application_timezone_for_boundaries(monkeypatch, tmp_path):
    test_db = _patch_db(monkeypatch, tmp_path)
    client = TestClient(app)
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=10,
    )
    event = test_db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type="lesson_completed",
        entity_type="lesson",
        entity_id="timezone-lesson",
        idempotency_key="timezone-lesson",
    )
    test_db.learning_session_repository.complete_session(
        session_id=session.session_id,
        user_id="default_user",
        idempotency_key="complete-timezone",
    )
    with test_db.get_connection() as conn:
        conn.execute(
            """
            UPDATE learning_sessions
            SET started_at = ?, ended_at = ?, duration_seconds = ?
            WHERE session_id = ?
            """,
            (
                "2026-07-19T15:40:00+00:00",
                "2026-07-19T16:10:00+00:00",
                1800,
                session.session_id,
            ),
        )
        conn.execute(
            "UPDATE learning_session_events SET occurred_at = ? WHERE event_id = ?",
            ("2026-07-19T16:00:00+00:00", event.event_id),
        )

    response = client.get("/api/learning-insights/weekly?language=EN&week_start=2026-07-20")

    assert response.status_code == 200
    insight = response.json()["insight"]
    assert insight["completed_session_count"] == 1
    assert insight["lesson_completion_count"] == 1
    assert insight["active_learning_days"] == 1
    assert insight["most_active_day"] == "2026-07-20"
