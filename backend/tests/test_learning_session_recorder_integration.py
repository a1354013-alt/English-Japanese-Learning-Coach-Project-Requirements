from __future__ import annotations

import database as database_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.learning_intelligence as learning_intelligence_module
import services.lesson_ops as lesson_ops_module
import services.streak_service as streak_service_module
from database import Database
from fastapi.testclient import TestClient
from main import app
from routers import ai_tools as ai_tools_router
from routers import chat as chat_router
from routers import lessons as lessons_router
from routers import micro_lessons as micro_lessons_router
from routers import review as review_router
from services.learning_intelligence import sync_lesson_items

import chat_handler as chat_handler_module

from test_learning_intelligence import _seed_textbook_lesson
from test_micro_lessons import _submit_diagnostic


class _FakeOllama:
    async def generate(self, **_: object) -> dict[str, object]:
        return {"success": True, "response": "Persisted assistant reply?"}


class _UnavailableOllama:
    async def generate(self, **_: object) -> dict[str, object]:
        return {"success": False, "error": "offline"}


def _patch_all(monkeypatch, test_db: Database) -> None:
    for module in (
        database_module,
        gamification_module,
        lesson_ops_module,
        learning_intelligence_module,
        lesson_generator_module,
        lessons_router,
        review_router,
        micro_lessons_router,
        streak_service_module.database_module,
        chat_handler_module,
        chat_router,
        ai_tools_router,
    ):
        monkeypatch.setattr(module, "db", test_db, raising=False)


def _review_answers(lesson: dict) -> list[dict[str, object]]:
    lesson_id = lesson["metadata"]["lesson_id"]
    return [
        {
            "lesson_id": lesson_id,
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": "reviews",
            "correct_answer": "review",
        },
        {
            "lesson_id": lesson_id,
            "exercise_type": "reading",
            "question_index": 0,
            "user_answer": "one pattern",
            "correct_answer": "one pattern",
        },
    ]


def test_review_submission_records_review_and_lesson_completion_events(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "session-review.db"))
    _patch_all(monkeypatch, test_db)
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id="default_user")
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=20,
    )
    client = TestClient(app)

    response = client.post("/api/review", json=_review_answers(lesson))

    assert response.status_code == 200
    events = test_db.learning_session_repository.list_events(
        session_id=session.session_id,
        user_id="default_user",
        limit=20,
    ).events
    assert [event.event_type.value for event in events] == [
        "review_answered",
        "review_answered",
        "lesson_completed",
    ]
    assert [event.metadata.correct for event in events[:2]] == [False, True]


def test_wrong_language_active_session_does_not_capture_review_events(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "session-language.db"))
    _patch_all(monkeypatch, test_db)
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id="default_user")
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="JP",
        planned_minutes=20,
    )
    client = TestClient(app)

    response = client.post("/api/review", json=_review_answers(lesson))

    assert response.status_code == 200
    events = test_db.learning_session_repository.list_events(
        session_id=session.session_id,
        user_id="default_user",
        limit=20,
    ).events
    assert events == []


def test_chat_assistant_completion_records_one_session_event(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "session-chat.db"))
    _patch_all(monkeypatch, test_db)
    test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=10,
    )
    monkeypatch.setattr("chat_handler.ollama_client", _FakeOllama(), raising=False)
    client = TestClient(app)

    with client.websocket_connect("/ws/chat/EN?scenario_id=travel") as websocket:
        ready = websocket.receive_json()
        conversation_id = ready["conversation_id"]
        websocket.send_json({"text": "Hello", "client_message_id": "turn-1"})
        websocket.receive_json()
        websocket.receive_json()

    active = test_db.learning_session_repository.find_active_session(user_id="default_user", language="EN")
    assert active is not None
    events = test_db.learning_session_repository.list_events(
        session_id=active.session_id,
        user_id="default_user",
        limit=20,
    ).events
    assert len(events) == 1
    assert events[0].event_type.value == "chat_turn_completed"
    assert events[0].entity_id == conversation_id


def test_srs_feynman_and_micro_lesson_record_events(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "session-mixed.db"))
    _patch_all(monkeypatch, test_db)
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id="default_user")
    sync_lesson_items(user_id="default_user", lesson_data=lesson)
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=30,
    )
    monkeypatch.setattr(learning_intelligence_module, "ollama_client", _UnavailableOllama(), raising=False)
    client = TestClient(app)

    due_items = client.get("/api/srs/items/due?language=EN").json()["items"]
    vocab_item = next(item for item in due_items if item["item_type"] == "vocabulary")
    srs_response = client.post(
        "/api/srs/items/review",
        json={"item_id": vocab_item["item_id"], "rating": 5, "source": "srs_review"},
    )
    assert srs_response.status_code == 200

    feynman_response = client.post(
        f"/api/lessons/{lesson['metadata']['lesson_id']}/feynman-feedback",
        json={"explanation": "I review one pattern every day.", "language": "EN"},
    )
    assert feynman_response.status_code == 200

    _submit_diagnostic(client)
    today_lesson = client.get("/api/micro-lessons/today").json()["lesson"]
    micro_response = client.post(
        f"/api/micro-lessons/{today_lesson['lesson_id']}/answer",
        json={"answer": today_lesson["fill_blank_question"]["correct_answer"]},
    )
    assert micro_response.status_code == 200

    events = test_db.learning_session_repository.list_events(
        session_id=session.session_id,
        user_id="default_user",
        limit=20,
    ).events
    event_types = [event.event_type.value for event in events]
    assert "srs_reviewed" in event_types
    assert "feynman_completed" in event_types
    assert "micro_lesson_completed" in event_types
