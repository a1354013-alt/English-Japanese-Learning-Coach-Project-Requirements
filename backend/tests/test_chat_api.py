from __future__ import annotations

import database as database_module
import pytest
from database import Database
from fastapi.testclient import TestClient
from main import app
from models import ChatConversationUpdateRequest
from pydantic import ValidationError
from routers import chat as chat_router


def _patch_chat_db(monkeypatch, tmp_path) -> Database:
    test_db = Database(str(tmp_path / "chat-api.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(chat_router, "db", test_db, raising=False)
    return test_db


def _insert_lesson(
    db: Database,
    lesson_id: str,
    *,
    user_id: str = "default_user",
    language: str = "EN",
) -> None:
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO lessons (
                lesson_id, user_id, language, level, topic, generated_at,
                estimated_duration_minutes, key_points, file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson_id,
                user_id,
                language,
                "A1" if language == "EN" else "N5",
                "linked lesson",
                "2026-07-19T09:00:00+08:00",
                15,
                "[]",
                "lesson.json",
            ),
        )


def _append_messages(db: Database, conversation_id: str, contents: list[str]) -> None:
    for index, content in enumerate(contents, start=1):
        db.chat_repository.append_message(
            conversation_id=conversation_id,
            user_id="default_user",
            role="user" if index % 2 else "assistant",
            content=content,
            idempotency_key=f"msg-{index}",
        )


def test_chat_conversation_crud_and_language_isolation(monkeypatch, tmp_path):
    db = _patch_chat_db(monkeypatch, tmp_path)
    _insert_lesson(db, "lesson-en", language="EN")
    _insert_lesson(db, "lesson-jp", language="JP")
    client = TestClient(app)

    created_en = client.post(
        "/api/chat/conversations",
        json={"language": "EN", "title": "  English chat  ", "lesson_id": "lesson-en"},
    )
    created_jp = client.post(
        "/api/chat/conversations",
        json={"language": "JP", "title": "Japanese chat", "lesson_id": "lesson-jp"},
    )

    assert created_en.status_code == 201
    assert created_jp.status_code == 201
    en_body = created_en.json()["conversation"]
    jp_body = created_jp.json()["conversation"]
    assert en_body["language"] == "EN"
    assert en_body["scenario_id"] == "daily_conversation"
    assert en_body["title"] == "English chat"
    assert jp_body["language"] == "JP"
    assert jp_body["scenario_id"] == "daily_conversation"

    listed_en = client.get("/api/chat/conversations?language=EN")
    listed_jp = client.get("/api/chat/conversations?language=JP")
    assert listed_en.status_code == 200
    assert listed_jp.status_code == 200
    assert [item["conversation_id"] for item in listed_en.json()["conversations"]] == [en_body["conversation_id"]]
    assert [item["conversation_id"] for item in listed_jp.json()["conversations"]] == [jp_body["conversation_id"]]

    fetched = client.get(f"/api/chat/conversations/{en_body['conversation_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["conversation"]["conversation_id"] == en_body["conversation_id"]
    assert fetched.json()["conversation"]["scenario_id"] == "daily_conversation"


def test_chat_conversation_create_list_and_detail_include_scenario(monkeypatch, tmp_path):
    _patch_chat_db(monkeypatch, tmp_path)
    client = TestClient(app)

    created = client.post(
        "/api/chat/conversations",
        json={"language": "EN", "scenario_id": "travel", "title": "Travel chat"},
    )

    assert created.status_code == 201
    body = created.json()["conversation"]
    assert body["scenario_id"] == "travel"

    listed = client.get("/api/chat/conversations?language=EN")
    assert listed.status_code == 200
    assert listed.json()["conversations"][0]["scenario_id"] == "travel"

    fetched = client.get(f"/api/chat/conversations/{body['conversation_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["conversation"]["scenario_id"] == "travel"

    invalid = client.post(
        "/api/chat/conversations",
        json={"language": "EN", "scenario_id": "write a custom prompt", "title": "Bad"},
    )
    assert invalid.status_code == 422


def test_chat_conversation_patch_supports_rename_link_summary_and_unlink(monkeypatch, tmp_path):
    db = _patch_chat_db(monkeypatch, tmp_path)
    _insert_lesson(db, "lesson-en", language="EN")
    conversation = db.chat_repository.create_conversation(
        user_id="default_user",
        language="EN",
        title="Original",
    )
    _append_messages(db, conversation.conversation_id, ["one", "two", "three"])
    client = TestClient(app)

    updated = client.patch(
        f"/api/chat/conversations/{conversation.conversation_id}",
        json={
            "title": "Renamed",
            "lesson_id": "lesson-en",
            "summary": "Checkpointed summary",
            "summary_through_sequence": 3,
        },
    )
    assert updated.status_code == 200
    body = updated.json()["conversation"]
    assert body["title"] == "Renamed"
    assert body["lesson_id"] == "lesson-en"
    assert body["summary"] == "Checkpointed summary"
    assert body["summary_through_sequence"] == 3
    assert body["summary_updated_at"] is not None

    cleared = client.patch(
        f"/api/chat/conversations/{conversation.conversation_id}",
        json={"lesson_id": None, "summary": None},
    )
    assert cleared.status_code == 200
    cleared_body = cleared.json()["conversation"]
    assert cleared_body["lesson_id"] is None
    assert cleared_body["summary"] is None
    assert cleared_body["summary_through_sequence"] == 0
    assert cleared_body["summary_updated_at"] is None


def test_chat_delete_cascades_messages(monkeypatch, tmp_path):
    db = _patch_chat_db(monkeypatch, tmp_path)
    conversation = db.chat_repository.create_conversation(
        user_id="default_user",
        language="EN",
        title="Delete me",
    )
    _append_messages(db, conversation.conversation_id, ["a", "b"])
    client = TestClient(app)

    deleted = client.delete(f"/api/chat/conversations/{conversation.conversation_id}")
    assert deleted.status_code == 200
    assert deleted.json()["conversation_id"] == conversation.conversation_id

    missing = client.get(f"/api/chat/conversations/{conversation.conversation_id}")
    assert missing.status_code == 404
    with db.get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(1) AS count FROM chat_messages WHERE conversation_id = ?",
            (conversation.conversation_id,),
        ).fetchone()
    assert int(count["count"]) == 0


def test_chat_messages_pagination_returns_cursors_without_idempotency_keys(monkeypatch, tmp_path):
    db = _patch_chat_db(monkeypatch, tmp_path)
    conversation = db.chat_repository.create_conversation(
        user_id="default_user",
        language="EN",
        title="Paged",
    )
    _append_messages(db, conversation.conversation_id, ["m1", "m2", "m3", "m4", "m5"])
    client = TestClient(app)

    first_page = client.get(f"/api/chat/conversations/{conversation.conversation_id}/messages?limit=2")
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert [item["sequence_number"] for item in first_body["messages"]] == [4, 5]
    assert first_body["has_more"] is True
    assert first_body["next_before_sequence"] == 4
    assert first_body["next_after_sequence"] is None
    assert "idempotency_key" not in first_body["messages"][0]

    newer_page = client.get(
        f"/api/chat/conversations/{conversation.conversation_id}/messages?limit=2&after_sequence=2"
    )
    assert newer_page.status_code == 200
    newer_body = newer_page.json()
    assert [item["sequence_number"] for item in newer_body["messages"]] == [3, 4]
    assert newer_body["has_more"] is True
    assert newer_body["next_before_sequence"] == 3
    assert newer_body["next_after_sequence"] == 4

    older_page = client.get(
        f"/api/chat/conversations/{conversation.conversation_id}/messages?limit=2&before_sequence=5"
    )
    assert older_page.status_code == 200
    older_body = older_page.json()
    assert [item["sequence_number"] for item in older_body["messages"]] == [3, 4]
    assert older_body["has_more"] is True
    assert older_body["next_before_sequence"] == 3
    assert older_body["next_after_sequence"] == 4


def test_chat_api_rejects_invalid_inputs_and_user_id(monkeypatch, tmp_path):
    db = _patch_chat_db(monkeypatch, tmp_path)
    _insert_lesson(db, "lesson-jp", language="JP")
    conversation = db.chat_repository.create_conversation(
        user_id="other_user",
        language="EN",
        title="Other owner",
    )
    client = TestClient(app)

    bad_language = client.post("/api/chat/conversations", json={"language": "FR", "title": "Bad"})
    assert bad_language.status_code == 422
    assert bad_language.json()["code"] == "invalid_chat_language"

    long_title = client.post("/api/chat/conversations", json={"language": "EN", "title": "x" * 121})
    assert long_title.status_code == 422

    user_in_body = client.post(
        "/api/chat/conversations",
        json={"language": "EN", "title": "Bad", "user_id": "other_user"},
    )
    assert user_in_body.status_code == 422

    user_in_query = client.get("/api/chat/conversations?language=EN&user_id=other_user")
    assert user_in_query.status_code == 422
    assert user_in_query.json()["code"] == "user_id_not_allowed"

    missing = client.get(f"/api/chat/conversations/{conversation.conversation_id}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "conversation_not_found"

    lesson_mismatch = client.post(
        "/api/chat/conversations",
        json={"language": "EN", "title": "Mismatch", "lesson_id": "lesson-jp"},
    )
    assert lesson_mismatch.status_code == 409
    assert lesson_mismatch.json()["code"] == "lesson_language_mismatch"

    invalid_summary = client.patch(
        f"/api/chat/conversations/{conversation.conversation_id}",
        json={"summary": "Missing checkpoint"},
    )
    assert invalid_summary.status_code == 422


def test_chat_patch_validation_rejects_ambiguous_or_empty_updates(monkeypatch, tmp_path):
    db = _patch_chat_db(monkeypatch, tmp_path)
    conversation = db.chat_repository.create_conversation(
        user_id="default_user",
        language="EN",
        title="Patch validation",
    )
    _append_messages(db, conversation.conversation_id, ["m1", "m2", "m3"])
    client = TestClient(app)

    empty = client.patch(f"/api/chat/conversations/{conversation.conversation_id}", json={})
    assert empty.status_code == 422

    null_title = client.patch(f"/api/chat/conversations/{conversation.conversation_id}", json={"title": None})
    assert null_title.status_code == 422

    bad_clear = client.patch(
        f"/api/chat/conversations/{conversation.conversation_id}",
        json={"summary": None, "summary_through_sequence": 2},
    )
    assert bad_clear.status_code == 422

    clear_ok = client.patch(
        f"/api/chat/conversations/{conversation.conversation_id}",
        json={"summary": None, "summary_through_sequence": 0},
    )
    assert clear_ok.status_code == 200


def test_chat_update_request_model_rejects_invalid_patch_shapes():
    with pytest.raises(ValidationError):
        ChatConversationUpdateRequest.model_validate({})
    with pytest.raises(ValidationError):
        ChatConversationUpdateRequest.model_validate({"title": None})
    with pytest.raises(ValidationError):
        ChatConversationUpdateRequest.model_validate({"summary": None, "summary_through_sequence": 2})

    valid = ChatConversationUpdateRequest.model_validate({"lesson_id": None, "summary": None})
    assert valid.lesson_id is None
    assert valid.summary is None


def test_chat_summary_checkpoint_validation_and_message_limits(monkeypatch, tmp_path):
    db = _patch_chat_db(monkeypatch, tmp_path)
    conversation = db.chat_repository.create_conversation(
        user_id="default_user",
        language="EN",
        title="Summary validation",
    )
    _append_messages(db, conversation.conversation_id, ["m1", "m2"])
    client = TestClient(app)

    invalid_checkpoint = client.patch(
        f"/api/chat/conversations/{conversation.conversation_id}",
        json={"summary": "Too far", "summary_through_sequence": 3},
    )
    assert invalid_checkpoint.status_code == 422
    assert invalid_checkpoint.json()["code"] == "invalid_summary_checkpoint"

    invalid_limit = client.get(f"/api/chat/conversations/{conversation.conversation_id}/messages?limit=101")
    assert invalid_limit.status_code == 422

    invalid_cursor = client.get(
        f"/api/chat/conversations/{conversation.conversation_id}/messages?before_sequence=0"
    )
    assert invalid_cursor.status_code == 422


def test_chat_openapi_exposes_typed_schemas(monkeypatch, tmp_path):
    _patch_chat_db(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()
    paths = openapi["paths"]
    schemas = openapi["components"]["schemas"]

    assert (
        paths["/api/chat/conversations"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
        .endswith("/ChatConversationDetailResponse")
    )
    assert (
        paths["/api/chat/conversations/{conversation_id}/messages"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"].endswith("/ChatMessageListResponse")
    )
    assert (
        paths["/api/chat/conversations/{conversation_id}"]["patch"]["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"].endswith("/ChatConversationUpdateRequest")
    )
    assert "ChatConversationCreateRequest" in schemas
    assert "ChatConversationUpdateRequest" in schemas
    assert "ChatConversationResponse" in schemas
    assert "ChatMessageListResponse" in schemas
