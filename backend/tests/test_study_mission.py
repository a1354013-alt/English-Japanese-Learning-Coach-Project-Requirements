"""Daily study mission and Analytics 2.0 coverage."""

from __future__ import annotations

import database as database_module
import gamification_engine as gamification_module
import routers.study as study_router
import services.streak_service as streak_service_module
from database import Database
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import study, system


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(study.router)
    app.include_router(system.api_router)
    return app


def _client(tmp_path, monkeypatch) -> tuple[TestClient, Database]:
    test_db = Database(str(tmp_path / "study.db"))
    for module in (
        database_module,
        study_router,
        system,
        gamification_module,
    ):
        monkeypatch.setattr(module, "db", test_db, raising=False)
    monkeypatch.setattr(streak_service_module.database_module, "db", test_db, raising=False)
    return TestClient(_make_app()), test_db


def _seed_item(
    db: Database,
    *,
    item_type: str,
    item_key: str,
    mastery_state: str,
    language: str = "EN",
    level: str = "A1",
    rating: int = 1,
    correct: bool = False,
) -> None:
    saved = db.upsert_learning_item(
        user_id="default_user",
        item_type=item_type,
        item_key=item_key,
        language=language,
        level=level,
        lesson_id="lesson-1",
        content={"word": item_key, "title": item_key, "pattern": item_key},
        category=item_type,
        tags=[],
    )
    db.record_learning_item_review(
        user_id="default_user",
        item_id=str(saved["id"]),
        rating=rating,
        correct=correct,
        source="manual",
    )
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE learning_item_srs SET mastery_state = ?, due_at = '2000-01-01T00:00:00' WHERE item_id = ?",
            (mastery_state, str(saved["id"])),
        )


def test_today_study_mission_no_diagnostic_state_yet(tmp_path, monkeypatch):
    client, _db = _client(tmp_path, monkeypatch)

    response = client.get("/api/study/today?language=EN")

    assert response.status_code == 200
    mission = response.json()["mission"]
    assert mission["diagnostic_completed"] is False
    assert mission["micro_lesson_status"] == "diagnostic_required"
    assert mission["micro_lesson"] is None
    assert mission["today_goal_text"].startswith("Complete the diagnostic")
    assert mission["suggested_next_lesson"] == {
        "language": "EN",
        "level": "A1",
        "topic": "Placement diagnostic",
    }


def test_today_study_mission_seeded_demo_state_contract_and_counts(tmp_path, monkeypatch):
    client, db = _client(tmp_path, monkeypatch)
    db.save_diagnostic_state(
        user_id="default_user",
        estimated_total_days=90,
        current_day=3,
        summary_zh="ready",
        correct_count=4,
    )
    _seed_item(db, item_type="vocabulary", item_key="invoice", mastery_state="weak")
    _seed_item(db, item_type="grammar", item_key="Present Simple", mastery_state="weak")
    _seed_item(db, item_type="sentence_pattern", item_key="I confirm ...", mastery_state="learning", rating=4, correct=True)

    response = client.get("/api/study/today?language=EN")

    assert response.status_code == 200
    mission = response.json()["mission"]
    assert {
        "diagnostic_completed",
        "micro_lesson_status",
        "learning_plan",
        "micro_lesson",
        "due_counts",
        "weak_counts",
        "weak_items",
        "suggested_next_lesson",
        "today_goal_text",
        "completion_summary",
    } <= set(mission)
    assert mission["micro_lesson"]["day_index"] == 3
    assert mission["due_counts"]["vocabulary"] == 1
    assert mission["due_counts"]["grammar"] == 1
    assert mission["due_counts"]["sentence_pattern"] == 1
    assert mission["due_counts"]["total"] >= 3
    assert mission["weak_counts"] == {"vocabulary": 1, "grammar": 1, "sentence_pattern": 1}
    assert mission["weak_items"]["vocabulary"][0]["item_key"] == "invoice"
    assert mission["suggested_next_lesson"]["topic"].startswith("Repair grammar")


def test_today_study_mission_uses_selected_language_filters_and_progress(tmp_path, monkeypatch):
    client, db = _client(tmp_path, monkeypatch)
    progress = db.get_progress("default_user")
    progress["japanese_progress"]["current_level"] = "N4"
    db.save_progress(progress)

    _seed_item(db, item_type="grammar", item_key="ている", mastery_state="weak", language="JP", level="N4", rating=3)
    _seed_item(db, item_type="vocabulary", item_key="invoice", mastery_state="weak", language="EN", level="A1")

    response = client.get("/api/study/today?language=JP")

    assert response.status_code == 200
    mission = response.json()["mission"]
    assert mission["diagnostic_completed"] is False
    assert mission["micro_lesson_status"] == "unavailable"
    assert mission["learning_plan"] is None
    assert mission["micro_lesson"] is None
    assert mission["due_counts"] == {
        "vocabulary": 0,
        "grammar": 1,
        "sentence_pattern": 0,
        "legacy_vocabulary": 0,
        "total": 1,
    }
    assert mission["weak_counts"] == {"vocabulary": 0, "grammar": 1, "sentence_pattern": 0}
    assert mission["weak_items"]["grammar"][0]["item_key"] == "ている"
    assert mission["suggested_next_lesson"] == {
        "language": "JP",
        "level": "N4",
        "topic": "Repair grammar: ている",
    }
    assert "diagnostic" not in mission["today_goal_text"].lower()


def test_analytics_2_learning_item_fields(tmp_path, monkeypatch):
    client, db = _client(tmp_path, monkeypatch)
    _seed_item(db, item_type="vocabulary", item_key="invoice", mastery_state="weak")
    _seed_item(db, item_type="grammar", item_key="Present Simple", mastery_state="weak")
    _seed_item(db, item_type="sentence_pattern", item_key="I confirm ...", mastery_state="learning", rating=4, correct=True)

    response = client.get("/api/analytics")

    assert response.status_code == 200
    analytics = response.json()["analytics"]
    assert analytics["mastery_state_counts"]["vocabulary"]["weak"] == 1
    assert analytics["weakest_vocabulary"][0]["item_key"] == "invoice"
    assert analytics["weakest_grammar"][0]["item_key"] == "Present Simple"
    assert analytics["weakest_sentence_patterns"][0]["item_key"] == "I confirm ..."
    assert analytics["recent_7_day_review_counts"]
