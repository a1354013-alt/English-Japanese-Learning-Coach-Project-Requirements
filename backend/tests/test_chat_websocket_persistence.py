from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

from chat_handler import ChatManager
from database import Database
from fastapi.testclient import TestClient
from main import app


def _make_db(tmp_path) -> Database:
    return Database(str(tmp_path / "ws-chat.db"))


def _patch_chat_db(monkeypatch, temp_db: Database) -> None:
    import chat_handler

    monkeypatch.setattr(chat_handler, "db", temp_db, raising=True)


def _ready(ws) -> dict[str, Any]:
    event = ws.receive_json()
    assert event["type"] == "conversation.ready"
    return event


def _next_type(ws, event_type: str) -> dict[str, Any]:
    for _ in range(5):
        event = ws.receive_json()
        if event.get("type") == event_type:
            return event
    raise AssertionError(f"Did not receive {event_type}")


def test_websocket_auto_creates_conversation_and_accepts_legacy_payload(tmp_path, monkeypatch):
    temp_db = _make_db(tmp_path)
    _patch_chat_db(monkeypatch, temp_db)
    import chat_handler

    monkeypatch.setattr(
        chat_handler.ollama_client,
        "generate",
        AsyncMock(return_value={"success": True, "response": "Hello back."}),
    )

    with TestClient(app).websocket_connect("/ws/chat/EN") as ws:
        ready = _ready(ws)
        ws.send_json({"text": "Hello"})
        user_event = _next_type(ws, "chat.user.persisted")
        assistant_event = _next_type(ws, "chat.assistant")

    assert ready["conversation_id"] == user_event["conversation_id"] == assistant_event["conversation_id"]
    assert assistant_event["role"] == "assistant"
    assert assistant_event["text"] == "Hello back."
    messages = temp_db.chat_repository.get_messages_page(
        conversation_id=ready["conversation_id"],
        user_id="default_user",
        limit=10,
    ).messages
    assert [(message.role, message.content) for message in messages] == [
        ("user", "Hello"),
        ("assistant", "Hello back."),
    ]


def test_websocket_resumes_existing_conversation_and_isolates_language(tmp_path, monkeypatch):
    temp_db = _make_db(tmp_path)
    _patch_chat_db(monkeypatch, temp_db)
    conversation = temp_db.chat_repository.create_conversation(user_id="default_user", language="JP", title="JP")

    with TestClient(app).websocket_connect(f"/ws/chat/JP?conversation_id={conversation.conversation_id}") as ws:
        ready = _ready(ws)

    assert ready["conversation_id"] == conversation.conversation_id

    with TestClient(app).websocket_connect(f"/ws/chat/EN?conversation_id={conversation.conversation_id}") as ws:
        event = ws.receive_json()
        assert event["type"] == "chat.error"
        assert event["code"] == "conversation_language_mismatch"


def test_websocket_treats_wrong_owner_conversation_as_not_found(tmp_path, monkeypatch):
    temp_db = _make_db(tmp_path)
    _patch_chat_db(monkeypatch, temp_db)
    conversation = temp_db.chat_repository.create_conversation(user_id="other_user", language="EN", title="Other")

    with TestClient(app).websocket_connect(f"/ws/chat/EN?conversation_id={conversation.conversation_id}") as ws:
        event = ws.receive_json()
        assert event["type"] == "chat.error"
        assert event["code"] == "conversation_not_found"


def test_websocket_client_message_id_retry_reuses_messages(tmp_path, monkeypatch):
    temp_db = _make_db(tmp_path)
    _patch_chat_db(monkeypatch, temp_db)
    import chat_handler

    generate = AsyncMock(return_value={"success": True, "response": "Stable answer."})
    monkeypatch.setattr(chat_handler.ollama_client, "generate", generate)

    with TestClient(app).websocket_connect("/ws/chat/EN") as ws:
        ready = _ready(ws)
        payload = {"text": "Hello", "client_message_id": "client-1"}
        ws.send_json(payload)
        first_user = _next_type(ws, "chat.user.persisted")
        first_assistant = _next_type(ws, "chat.assistant")
        ws.send_json(payload)
        second_user = _next_type(ws, "chat.user.persisted")
        second_assistant = _next_type(ws, "chat.assistant")

    assert first_user["message_id"] == second_user["message_id"]
    assert first_assistant["message_id"] == second_assistant["message_id"]
    assert generate.await_count == 1
    messages = temp_db.chat_repository.get_messages_page(
        conversation_id=ready["conversation_id"],
        user_id="default_user",
        limit=10,
    ).messages
    assert len(messages) == 2


def test_websocket_incompatible_retry_reports_conflict(tmp_path, monkeypatch):
    temp_db = _make_db(tmp_path)
    _patch_chat_db(monkeypatch, temp_db)
    import chat_handler

    monkeypatch.setattr(
        chat_handler.ollama_client,
        "generate",
        AsyncMock(return_value={"success": True, "response": "First."}),
    )

    with TestClient(app).websocket_connect("/ws/chat/EN") as ws:
        _ready(ws)
        ws.send_json({"text": "Hello", "client_message_id": "client-1"})
        _next_type(ws, "chat.assistant")
        ws.send_json({"text": "Changed", "client_message_id": "client-1"})
        event = _next_type(ws, "chat.error")

    assert event["code"] == "idempotency_conflict"


def test_websocket_provider_failure_persists_user_without_assistant_and_retry_resumes(tmp_path, monkeypatch):
    temp_db = _make_db(tmp_path)
    _patch_chat_db(monkeypatch, temp_db)
    import chat_handler

    generate = AsyncMock(
        side_effect=[
            {"success": False, "error": "down"},
            {"success": True, "response": "Recovered."},
        ]
    )
    monkeypatch.setattr(chat_handler.ollama_client, "generate", generate)

    with TestClient(app).websocket_connect("/ws/chat/EN") as ws:
        ready = _ready(ws)
        payload = {"text": "Hello", "client_message_id": "client-1"}
        ws.send_json(payload)
        failure = _next_type(ws, "chat.error")
        ws.send_json(payload)
        assistant = _next_type(ws, "chat.assistant")

    assert failure["code"] == "provider_unavailable"
    assert assistant["text"] == "Recovered."
    messages = temp_db.chat_repository.get_messages_page(
        conversation_id=ready["conversation_id"],
        user_id="default_user",
        limit=10,
    ).messages
    assert [(message.role, message.content) for message in messages] == [
        ("user", "Hello"),
        ("assistant", "Recovered."),
    ]


def test_websocket_context_is_bounded_and_current_user_appears_once(tmp_path, monkeypatch):
    temp_db = _make_db(tmp_path)
    _patch_chat_db(monkeypatch, temp_db)
    import chat_handler

    conversation = temp_db.chat_repository.create_conversation(user_id="default_user", language="EN", title="EN")
    for index in range(1, 6):
        temp_db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user" if index % 2 else "assistant",
            content=f"old-{index}",
        )
    temp_db.chat_repository.update_conversation_summary(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        summary="Earlier summary",
        summary_through_sequence=4,
    )
    captured: dict[str, str] = {}

    async def _generate(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return {"success": True, "response": "Done."}

    monkeypatch.setattr(chat_handler.ollama_client, "generate", _generate)
    monkeypatch.setattr(chat_handler.settings, "chat_recent_message_limit", 3)
    monkeypatch.setattr(chat_handler.settings, "chat_context_max_chars", 200)

    with TestClient(app).websocket_connect(f"/ws/chat/EN?conversation_id={conversation.conversation_id}") as ws:
        _ready(ws)
        ws.send_json({"text": "current", "client_message_id": "client-current"})
        _next_type(ws, "chat.assistant")

    assert "Earlier summary" in captured["prompt"]
    assert captured["prompt"].count("User: current") == 1
    assert len(captured["prompt"]) <= 200
    assert "old-1" not in captured["prompt"]


def test_concurrent_duplicate_turns_share_one_provider_call(tmp_path, monkeypatch):
    temp_db = _make_db(tmp_path)
    _patch_chat_db(monkeypatch, temp_db)
    import chat_handler

    manager = ChatManager()
    conversation = temp_db.chat_repository.create_conversation(user_id="default_user", language="EN", title="EN")
    provider_started = asyncio.Event()
    release_provider = asyncio.Event()
    calls = 0

    async def _generate(**_kwargs):
        nonlocal calls
        calls += 1
        provider_started.set()
        await release_provider.wait()
        return {"success": True, "response": "One answer."}

    monkeypatch.setattr(chat_handler.ollama_client, "generate", _generate)

    class _Socket:
        def __init__(self) -> None:
            self.events: list[dict[str, Any]] = []

        async def send_json(self, event: dict[str, Any]) -> None:
            self.events.append(event)

    async def _run() -> tuple[_Socket, _Socket]:
        first = _Socket()
        second = _Socket()
        kwargs = {
            "user_id": "default_user",
            "conversation_id": conversation.conversation_id,
            "language": "EN",
            "scenario": "Daily Conversation",
            "user_text": "Hello",
            "client_message_id": "same-client-id",
        }
        lock = manager._turn_locks.setdefault(f"{conversation.conversation_id}:same-client-id", asyncio.Lock())

        async def _locked(socket: _Socket) -> None:
            async with lock:
                await manager._handle_turn(websocket=socket, **kwargs)

        first_task = asyncio.create_task(_locked(first))
        await provider_started.wait()
        second_task = asyncio.create_task(_locked(second))
        await asyncio.sleep(0)
        release_provider.set()
        await asyncio.gather(first_task, second_task)
        return first, second

    first_socket, second_socket = asyncio.run(_run())

    assert calls == 1
    assert [event["type"] for event in first_socket.events][-1] == "chat.assistant"
    assert [event["type"] for event in second_socket.events][-1] == "chat.assistant"
    assert first_socket.events[-1]["message_id"] == second_socket.events[-1]["message_id"]
