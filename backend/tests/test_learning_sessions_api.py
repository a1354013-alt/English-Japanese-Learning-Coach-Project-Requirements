from __future__ import annotations

import database as database_module
from database import Database
from fastapi.testclient import TestClient
from main import app
from routers import learning_sessions as learning_sessions_router


def _patch_learning_session_db(monkeypatch, tmp_path) -> Database:
    test_db = Database(str(tmp_path / "learning-sessions-api.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(learning_sessions_router, "db", test_db, raising=False)
    return test_db


def test_learning_sessions_api_crud_and_summary(monkeypatch, tmp_path):
    _patch_learning_session_db(monkeypatch, tmp_path)
    client = TestClient(app)

    created_en = client.post("/api/learning-sessions", json={"language": "EN", "planned_minutes": 20})
    created_jp = client.post("/api/learning-sessions", json={"language": "JP", "planned_minutes": 30})
    assert created_en.status_code == 201
    assert created_jp.status_code == 201
    en_session = created_en.json()["session"]
    jp_session = created_jp.json()["session"]
    assert "user_id" not in en_session
    assert en_session["language"] == "EN"
    assert jp_session["language"] == "JP"

    active_en = client.get("/api/learning-sessions/active?language=EN")
    assert active_en.status_code == 200
    assert active_en.json()["session"]["session_id"] == en_session["session_id"]

    event = client.post(
        f"/api/learning-sessions/{en_session['session_id']}/events",
        json={
            "event_type": "review_answered",
            "entity_type": "review",
            "entity_id": "review-1",
            "metadata": {"correct": True, "note": "nice"},
            "idempotency_key": "event-1",
        },
    )
    assert event.status_code == 200
    assert event.json()["event"]["sequence_number"] == 1

    second_event = client.post(
        f"/api/learning-sessions/{en_session['session_id']}/events",
        json={
            "event_type": "session_note",
            "metadata": {"note": "keep going"},
            "idempotency_key": "event-2",
        },
    )
    assert second_event.status_code == 200

    events_page = client.get(f"/api/learning-sessions/{en_session['session_id']}/events?limit=1")
    assert events_page.status_code == 200
    assert [item["sequence_number"] for item in events_page.json()["events"]] == [1]
    assert events_page.json()["next_cursor"] == "1"

    next_events = client.get(
        f"/api/learning-sessions/{en_session['session_id']}/events?limit=5&cursor=1"
    )
    assert next_events.status_code == 200
    assert [item["sequence_number"] for item in next_events.json()["events"]] == [2]

    listed = client.get("/api/learning-sessions?limit=10")
    assert listed.status_code == 200
    assert {item["session_id"] for item in listed.json()["sessions"]} == {
        en_session["session_id"],
        jp_session["session_id"],
    }

    completed = client.post(
        f"/api/learning-sessions/{en_session['session_id']}/complete",
        json={"idempotency_key": "complete-1"},
    )
    assert completed.status_code == 200
    assert completed.json()["session"]["status"] == "completed"

    summary = client.get(f"/api/learning-sessions/{en_session['session_id']}/summary")
    assert summary.status_code == 200
    assert summary.json()["summary"]["review_answer_count"] == 1
    assert summary.json()["summary"]["counts_by_event_type"]["session_note"] == 1
    assert summary.json()["summary"]["correct_event_count"] == 1

    abandoned = client.post(
        f"/api/learning-sessions/{jp_session['session_id']}/abandon",
        json={"idempotency_key": "abandon-1"},
    )
    assert abandoned.status_code == 200
    assert abandoned.json()["session"]["status"] == "abandoned"


def test_learning_sessions_api_conflicts_and_validation(monkeypatch, tmp_path):
    _patch_learning_session_db(monkeypatch, tmp_path)
    client = TestClient(app)

    created = client.post("/api/learning-sessions", json={"language": "EN"})
    assert created.status_code == 201
    session_id = created.json()["session"]["session_id"]

    duplicate = client.post("/api/learning-sessions", json={"language": "EN"})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "learning_session_active_conflict"

    same_event = client.post(
        f"/api/learning-sessions/{session_id}/events",
        json={
            "event_type": "session_note",
            "metadata": {"note": "same"},
            "idempotency_key": "event-same",
        },
    )
    assert same_event.status_code == 200

    conflict = client.post(
        f"/api/learning-sessions/{session_id}/events",
        json={
            "event_type": "session_note",
            "metadata": {"note": "different"},
            "idempotency_key": "event-same",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "learning_session_idempotency_conflict"

    invalid_language = client.post("/api/learning-sessions", json={"language": "FR"})
    assert invalid_language.status_code == 422
    assert invalid_language.json()["code"] == "invalid_learning_session_language"

    invalid_event_type = client.post(
        f"/api/learning-sessions/{session_id}/events",
        json={"event_type": "unknown"},
    )
    assert invalid_event_type.status_code == 422
    assert invalid_event_type.json()["code"] == "invalid_learning_session_event_type"

    invalid_entity_type = client.post(
        f"/api/learning-sessions/{session_id}/events",
        json={"event_type": "session_note", "entity_type": "bad", "entity_id": "x"},
    )
    assert invalid_entity_type.status_code == 422
    assert invalid_entity_type.json()["code"] == "invalid_learning_session_entity_type"

    invalid_metadata = client.post(
        f"/api/learning-sessions/{session_id}/events",
        json={"event_type": "session_note", "metadata": {}},
    )
    assert invalid_metadata.status_code == 422
    assert invalid_metadata.json()["code"] == "invalid_learning_session_metadata"

    invalid_pagination = client.get(f"/api/learning-sessions/{session_id}/events?cursor=bad")
    assert invalid_pagination.status_code == 422
    assert invalid_pagination.json()["code"] == "invalid_learning_session_pagination"

    user_in_body = client.post("/api/learning-sessions", json={"language": "EN", "user_id": "other"})
    assert user_in_body.status_code == 422

    user_in_query = client.get("/api/learning-sessions?user_id=other")
    assert user_in_query.status_code == 422
    assert user_in_query.json()["code"] == "user_id_not_allowed"

    missing = client.get("/api/learning-sessions/missing-session")
    assert missing.status_code == 404
    assert missing.json()["code"] == "learning_session_not_found"

    completed = client.post(f"/api/learning-sessions/{session_id}/complete", json={"idempotency_key": "done"})
    assert completed.status_code == 200

    invalid_transition = client.post(
        f"/api/learning-sessions/{session_id}/abandon",
        json={"idempotency_key": "late"},
    )
    assert invalid_transition.status_code == 409
    assert invalid_transition.json()["code"] == "invalid_learning_session_transition"

    append_after_completion = client.post(
        f"/api/learning-sessions/{session_id}/events",
        json={"event_type": "session_note", "metadata": {"note": "too late"}},
    )
    assert append_after_completion.status_code == 409
    assert append_after_completion.json()["code"] == "learning_session_not_active"

    completion_conflict = client.post(
        f"/api/learning-sessions/{session_id}/complete",
        json={"idempotency_key": "different"},
    )
    assert completion_conflict.status_code == 409
    assert completion_conflict.json()["code"] == "learning_session_idempotency_conflict"


def test_learning_sessions_openapi_exposes_typed_schemas(monkeypatch, tmp_path):
    _patch_learning_session_db(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()
    paths = openapi["paths"]
    schemas = openapi["components"]["schemas"]

    assert (
        paths["/api/learning-sessions"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        .endswith("/CreateLearningSessionRequest")
    )
    assert (
        paths["/api/learning-sessions/{session_id}/events"]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"].endswith("/LearningSessionEventDetailResponse")
    )
    assert (
        paths["/api/learning-sessions/{session_id}/summary"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"].endswith("/LearningSessionSummaryResponse")
    )
    assert "LearningSessionRecord" in schemas
    assert "LearningSessionEventRecord" in schemas
    assert "LearningSessionSummary" in schemas
    assert "user_id" not in schemas["CreateLearningSessionRequest"]["properties"]
    assert "user_id" not in schemas["LearningSessionRecord"]["properties"]
