from __future__ import annotations

import sqlite3

import chat_handler as chat_handler_module
import database as database_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.learning_intelligence as learning_intelligence_module
import services.lesson_ops as lesson_ops_module
import services.streak_service as streak_service_module
from database import Database
from fastapi.testclient import TestClient
from main import app
from models import LearningSessionEventMetadata
from repositories.errors import LearningSessionIdempotencyConflictError
from routers import ai_tools as ai_tools_router
from routers import chat as chat_router
from routers import lessons as lessons_router
from routers import micro_lessons as micro_lessons_router
from routers import review as review_router
from routers import study as study_router
from services.learning_intelligence import sync_lesson_items
from services.learning_session_recorder import build_learning_session_recorder
from test_learning_intelligence import _seed_textbook_lesson
from test_micro_lessons import _submit_diagnostic
from time_utils import local_now


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
        study_router,
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


def test_repeated_review_attempts_use_distinct_submission_operation_ids(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "session-review-repeat.db"))
    _patch_all(monkeypatch, test_db)
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id="default_user")
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=20,
    )
    client = TestClient(app)
    first_answers = _review_answers(lesson)
    second_answers = _review_answers(lesson)
    first_answers[0]["client_submission_id"] = "review-attempt-1"
    first_answers[1]["client_submission_id"] = "review-attempt-1"
    second_answers[0]["client_submission_id"] = "review-attempt-2"
    second_answers[1]["client_submission_id"] = "review-attempt-2"
    second_answers[0]["user_answer"] = "review"

    first = client.post("/api/review", json=first_answers)
    second = client.post("/api/review", json=second_answers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["gamification"]["xp_added"] > 0
    assert second.json()["gamification"]["xp_added"] == 0
    events = test_db.learning_session_repository.list_events(
        session_id=session.session_id,
        user_id="default_user",
        limit=20,
    ).events
    review_events = [event for event in events if event.event_type.value == "review_answered"]
    assert len(review_events) == 4
    submission_ids = {event.entity_id.split(":", 1)[0] for event in review_events}
    assert len(submission_ids) == 2
    assert [event.metadata.correct for event in review_events] == [False, True, True, True]


def test_review_network_retry_reuses_submission_events(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "session-review-retry.db"))
    _patch_all(monkeypatch, test_db)
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id="default_user")
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=20,
    )
    client = TestClient(app)
    answers = _review_answers(lesson)
    for answer in answers:
        answer["client_submission_id"] = "retry-review-1"

    first = client.post("/api/review", json=answers)
    retried = client.post("/api/review", json=answers)

    assert first.status_code == 200
    assert retried.status_code == 200
    events = test_db.learning_session_repository.list_events(
        session_id=session.session_id,
        user_id="default_user",
        limit=20,
    ).events
    assert [event.event_type.value for event in events].count("review_answered") == 2
    assert [event.event_type.value for event in events].count("lesson_completed") == 1


def test_review_retry_and_resubmission_is_stable_for_50_rounds(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "session-review-50.db"))
    _patch_all(monkeypatch, test_db)
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id="default_user")
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=20,
    )
    client = TestClient(app)

    for index in range(50):
        wrong = _review_answers(lesson)
        correct = _review_answers(lesson)
        for answer in wrong:
            answer["client_submission_id"] = f"round-{index}-wrong"
        for answer in correct:
            answer["client_submission_id"] = f"round-{index}-correct"
        correct[0]["user_answer"] = "review"

        wrong_response = client.post("/api/review", json=wrong)
        wrong_retry = client.post("/api/review", json=wrong)
        correct_response = client.post("/api/review", json=correct)

        assert wrong_response.status_code == 200
        assert wrong_retry.status_code == 200
        assert correct_response.status_code == 200

    with test_db.get_connection() as conn:
        event_count = conn.execute(
            """
            SELECT COUNT(1) AS count
            FROM learning_session_events
            WHERE session_id = ? AND event_type = 'review_answered'
            """,
            (session.session_id,),
        ).fetchone()["count"]
        completion_count = conn.execute(
            """
            SELECT COUNT(1) AS count
            FROM learning_session_events
            WHERE session_id = ? AND event_type = 'lesson_completed'
            """,
            (session.session_id,),
        ).fetchone()["count"]
        submission_count = conn.execute("SELECT COUNT(1) AS count FROM review_submissions").fetchone()["count"]

    assert event_count == 200
    assert completion_count == 1
    assert submission_count == 100


def test_explicit_lesson_start_records_once_and_generation_does_not_start(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "session-lesson-start.db"))
    _patch_all(monkeypatch, test_db)
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id="default_user")
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=20,
    )
    client = TestClient(app)
    lesson_id = lesson["metadata"]["lesson_id"]

    detail = client.get(f"/api/lessons/{lesson_id}")
    first_start = client.post(f"/api/lessons/{lesson_id}/start", json={})
    reloaded = client.get(f"/api/lessons/{lesson_id}")
    second_start = client.post(f"/api/lessons/{lesson_id}/start", json={})

    assert detail.status_code == 200
    assert first_start.status_code == 200
    assert reloaded.status_code == 200
    assert second_start.status_code == 200
    events = test_db.learning_session_repository.list_events(
        session_id=session.session_id,
        user_id="default_user",
        limit=20,
    ).events
    assert [event.event_type.value for event in events] == ["lesson_started"]


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


def test_legacy_srs_review_records_session_event_and_retries_once(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "session-legacy-srs.db"))
    _patch_all(monkeypatch, test_db)
    session = test_db.learning_session_repository.start_session(
        user_id="default_user",
        language="EN",
        planned_minutes=20,
    )
    test_db.update_srs_item(
        "default_user",
        "legacy",
        "EN",
        {
            "repetition": 0,
            "ease_factor": 2.5,
            "interval": 0,
            "next_review": local_now(),
        },
        {"definition_zh": "legacy"},
    )
    client = TestClient(app)

    first = client.post(
        "/api/srs/review",
        json={"word": "legacy", "language": "EN", "quality": 4, "client_operation_id": "legacy-srs-1"},
    )
    retry = client.post(
        "/api/srs/review",
        json={"word": "legacy", "language": "EN", "quality": 4, "client_operation_id": "legacy-srs-1"},
    )

    assert first.status_code == 200
    assert retry.status_code == 200
    events = test_db.learning_session_repository.list_events(
        session_id=session.session_id,
        user_id="default_user",
        limit=20,
    ).events
    assert [event.event_type.value for event in events] == ["srs_reviewed"]
    assert events[0].entity_id == "legacy:legacy"


def test_recorder_tolerant_lookup_failure_preserves_review_result(tmp_path, monkeypatch):
    monkeypatch.setenv("LEARNING_SESSION_RECORDER_MODE", "tolerant")
    test_db = Database(str(tmp_path / "session-lookup-failure.db"))
    _patch_all(monkeypatch, test_db)
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id="default_user")
    test_db.learning_session_repository.start_session(user_id="default_user", language="EN")

    def fail_lookup(*_: object, **__: object):
        raise sqlite3.OperationalError("lookup failed")

    monkeypatch.setattr(test_db.learning_session_repository, "find_active_session", fail_lookup)
    response = TestClient(app).post("/api/review", json=_review_answers(lesson))

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert test_db.get_exercise_result(
        user_id="default_user",
        lesson_id=lesson["metadata"]["lesson_id"],
        exercise_type="mixed",
    ) is not None


def test_recorder_tolerant_append_failures_preserve_review_result(tmp_path, monkeypatch):
    for exc in (
        sqlite3.OperationalError("append failed"),
        LearningSessionIdempotencyConflictError("conflict"),
    ):
        monkeypatch.setenv("LEARNING_SESSION_RECORDER_MODE", "tolerant")
        test_db = Database(str(tmp_path / f"session-append-failure-{type(exc).__name__}.db"))
        _patch_all(monkeypatch, test_db)
        lesson = _seed_textbook_lesson(test_db, tmp_path, user_id="default_user")
        test_db.learning_session_repository.start_session(user_id="default_user", language="EN")

        def fail_append(*_: object, **__: object):
            raise exc

        monkeypatch.setattr(test_db.learning_session_repository, "append_event", fail_append)
        response = TestClient(app).post("/api/review", json=_review_answers(lesson))

        assert response.status_code == 200
        assert response.json()["success"] is True


def test_recorder_strict_mode_raises_invalid_semantic_mapping(tmp_path):
    test_db = Database(str(tmp_path / "session-strict.db"))
    test_db.learning_session_repository.start_session(user_id="default_user", language="EN")
    recorder = build_learning_session_recorder(test_db, mode="strict")

    import pytest

    with pytest.raises(RuntimeError):
        recorder.record_event(
            user_id="default_user",
            language="EN",
            event_type="review_answered",
            entity_type="review",
            entity_id="review-1",
            idempotency_key="bad-review",
            metadata=LearningSessionEventMetadata(note="missing correct"),
        )
