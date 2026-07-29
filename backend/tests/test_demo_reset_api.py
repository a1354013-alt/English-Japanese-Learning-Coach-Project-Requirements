"""Demo reset API should rebuild a fully presentable dataset."""

import database as database_module
import services.learning_intelligence as learning_intelligence_module
from config import settings
from database import Database
from fastapi import FastAPI
from fastapi.testclient import TestClient
from models import LearningSessionEventMetadata
from routers import micro_lessons as micro_lessons_router
from routers import review as review_router
from routers import system as system_router
from services.learning_intelligence import build_snowball_context


def test_demo_reset_disabled_by_default_returns_403(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "allow_demo_reset", False, raising=False)
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"), raising=False)
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(micro_lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(learning_intelligence_module, "db", test_db, raising=False)

    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(review_router.router)
    app.include_router(micro_lessons_router.router)
    client = TestClient(app)

    response = client.post("/api/demo/reset")
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


def test_demo_reset_rebuilds_seed_data(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "allow_demo_reset", True, raising=False)
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"), raising=False)
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(micro_lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(learning_intelligence_module, "db", test_db, raising=False)

    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(review_router.router)
    app.include_router(micro_lessons_router.router)
    client = TestClient(app)

    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["summary"]["lessons"] >= 2

    diagnostic_state = test_db.get_diagnostic_state("default_user")
    assert diagnostic_state is not None
    assert diagnostic_state["current_day"] == 1
    assert diagnostic_state["estimated_total_days"] == 90
    assert diagnostic_state["correct_count"] == 4
    assert diagnostic_state["completed_at"]

    lessons, total = test_db.query_lessons("default_user", limit=10, offset=0)
    assert total >= 2
    vocab, vocab_total = test_db.list_imported_vocabulary(user_id="default_user", limit=10, offset=0)
    assert vocab_total >= 2
    assert test_db.list_wrong_answers(user_id="default_user", limit=10, offset=0)

    micro_today = client.get("/api/micro-lessons/today")
    assert micro_today.status_code == 200
    assert micro_today.json()["diagnostic_completed"] is True

    due = client.get("/api/srs/items/due?language=EN")
    assert due.status_code == 200
    due_items = due.json()["items"]
    assert due_items

    weak = client.get("/api/srs/items/weak?language=EN")
    assert weak.status_code == 200
    weak_body = weak.json()
    assert weak_body["vocabulary"]
    assert weak_body["grammar"] or weak_body["sentence_pattern"]

    context = build_snowball_context("default_user", "EN", "A2")
    assert context["weak_vocabulary"]
    assert context["weak_grammar"]
    assert context["recent_vocabulary"]

    analytics_response = client.get("/api/analytics")
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()["analytics"]
    assert analytics["weakest_vocabulary"][0]["item_key"] == "blocker"
    assert analytics["weakest_grammar"][0]["item_key"] == "Present Simple for status updates"
    assert analytics["weakest_sentence_patterns"][0]["item_key"] == "I report blockers in the standup."
    assert len(analytics["recent_7_day_review_counts"]) >= 4
    assert sum(point["count"] for point in analytics["recent_7_day_review_counts"]) >= 9


def test_demo_reset_clears_stale_micro_lesson_state(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "allow_demo_reset", True, raising=False)
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"), raising=False)
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(micro_lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(learning_intelligence_module, "db", test_db, raising=False)

    test_db.save_diagnostic_state(
        user_id="default_user",
        estimated_total_days=150,
        current_day=7,
        summary_zh="stale state",
        correct_count=1,
    )
    test_db.save_micro_lesson(
        "default_user",
        {
            "lesson_id": "stale-micro-lesson",
            "day_index": 7,
            "total_days": 150,
            "target_exam": "TOEIC 600",
            "sentence": "We study today.",
            "translation_zh": "stale",
            "subject_text": "We",
            "verb_text": "study",
            "object_text": "today",
            "reading_order_steps": ["We", "study", "today"],
            "grammar_note": "stale",
            "toeic_usage_note": "stale",
            "vocabulary_items": [
                {
                    "word": "study",
                    "phonetic": "/s/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "We study today.",
                    "example_translation": "stale",
                },
                {
                    "word": "team",
                    "phonetic": "/t/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "Our team studies.",
                    "example_translation": "stale",
                },
                {
                    "word": "daily",
                    "phonetic": "/d/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "Daily practice helps.",
                    "example_translation": "stale",
                },
                {
                    "word": "review",
                    "phonetic": "/r/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "We review often.",
                    "example_translation": "stale",
                },
                {
                    "word": "plan",
                    "phonetic": "/p/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "A plan helps.",
                    "example_translation": "stale",
                },
            ],
            "dialogue_lines": [
                {
                    "speaker": "A",
                    "english": "We study today.",
                    "translation_zh": "stale",
                }
            ],
            "reading_passage": "stale passage",
            "comic_panels": [
                {
                    "panel": 1,
                    "english": "We study today.",
                    "translation_zh": "stale",
                    "scene_prompt": "stale",
                }
            ],
            "fill_blank_question": {
                "prompt": "We ___ today.",
                "choices": ["study", "studies", "studied"],
                "correct_answer": "study",
                "explanation": "stale",
            },
            "completed": True,
        },
    )

    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(review_router.router)
    app.include_router(micro_lessons_router.router)
    client = TestClient(app)

    response = client.post("/api/demo/reset")
    assert response.status_code == 200

    diagnostic_state = test_db.get_diagnostic_state("default_user")
    assert diagnostic_state is not None
    assert diagnostic_state["current_day"] == 1
    assert diagnostic_state["estimated_total_days"] == 90
    assert diagnostic_state["correct_count"] == 4
    assert test_db.get_micro_lesson_by_day("default_user", 7) is None


def test_demo_reset_clears_learning_sessions_and_rebuilds_seeded_demo_data(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "allow_demo_reset", True, raising=False)
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"), raising=False)
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(micro_lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(learning_intelligence_module, "db", test_db, raising=False)

    active = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=20,
    )
    finalized = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="JP",
        planned_minutes=25,
    )
    test_db.learning_session_repository.append_event(
        session_id=active.session_id,
        user_id="default_user",
        event_type="session_note",
        metadata=LearningSessionEventMetadata(note="active note"),
        idempotency_key="active-note",
    )
    test_db.learning_session_repository.append_event(
        session_id=finalized.session_id,
        user_id="default_user",
        event_type="session_note",
        metadata=LearningSessionEventMetadata(note="finalized note"),
        idempotency_key="final-note",
    )
    test_db.learning_session_repository.complete_session(
        session_id=finalized.session_id,
        user_id="default_user",
        idempotency_key="jp-complete",
    )

    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(review_router.router)
    app.include_router(micro_lessons_router.router)
    client = TestClient(app)

    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    assert response.json()["summary"]["today_lesson_id"] == "demo-en-today"

    with test_db.get_connection() as conn:
        session_count = conn.execute(
            "SELECT COUNT(1) AS count FROM learning_sessions WHERE user_id = ?",
            ("default_user",),
        ).fetchone()["count"]
        event_count = conn.execute(
            """
            SELECT COUNT(1) AS count
            FROM learning_session_events
            WHERE session_id IN (
                SELECT session_id FROM learning_sessions WHERE user_id = ?
            )
            """,
            ("default_user",),
        ).fetchone()["count"]
    assert session_count == 0
    assert event_count == 0

    lessons, total_lessons = test_db.query_lessons("default_user", limit=10, offset=0)
    assert total_lessons >= 2
    assert any(lesson["lesson_id"] == "demo-en-today" for lesson in lessons)
