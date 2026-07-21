from __future__ import annotations

import chat_handler as chat_handler_module
import database as database_module
from database import Database
from fastapi.testclient import TestClient
from main import app
from routers import ai_tools as ai_tools_router
from routers import chat as chat_router


class _FakeOllama:
    async def generate(self, **_: object) -> dict[str, object]:
        return {"success": True, "response": "Persisted assistant reply?"}


def _patch_chat_db(monkeypatch, tmp_path) -> Database:
    test_db = Database(str(tmp_path / "chat-ws.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(chat_handler_module, "db", test_db, raising=False)
    monkeypatch.setattr(chat_router, "db", test_db, raising=False)
    monkeypatch.setattr(ai_tools_router, "db", test_db, raising=False)
    return test_db


def test_chat_websocket_persists_messages_and_reuses_canonical_ids(monkeypatch, tmp_path):
    db = _patch_chat_db(monkeypatch, tmp_path)
    monkeypatch.setattr("chat_handler.ollama_client", _FakeOllama(), raising=False)
    client = TestClient(app)

    with client.websocket_connect("/ws/chat/EN?scenario_id=travel") as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "conversation.ready"
        assert ready["scenario_id"] == "travel"
        conversation_id = ready["conversation_id"]

        websocket.send_json({"text": "Hello", "client_message_id": "turn-1"})
        user_persisted = websocket.receive_json()
        assistant_persisted = websocket.receive_json()

        assert user_persisted["type"] == "chat.user.persisted"
        assert user_persisted["message"]["message_id"]
        assert assistant_persisted["type"] == "chat.assistant.persisted"

        websocket.send_json({"text": "Hello", "client_message_id": "turn-1"})
        retried_user = websocket.receive_json()
        retried_assistant = websocket.receive_json()

        assert retried_user["message"]["message_id"] == user_persisted["message"]["message_id"]
        assert retried_assistant["message"]["message_id"] == assistant_persisted["message"]["message_id"]

    page = db.chat_repository.get_messages_page(
        conversation_id=conversation_id,
        user_id="default_user",
        limit=10,
    )
    assert [item.content for item in page.messages] == [
        "Hello",
        "Persisted assistant reply?",
    ]


def test_chat_websocket_rejects_language_mismatch_conversation(monkeypatch, tmp_path):
    db = _patch_chat_db(monkeypatch, tmp_path)
    conversation = db.chat_repository.create_conversation(
        user_id="default_user",
        language="EN",
        scenario_id="travel",
        title="English Travel",
    )
    client = TestClient(app)

    with client.websocket_connect(f"/ws/chat/JP?conversation_id={conversation.conversation_id}") as websocket:
        payload = websocket.receive_json()
        assert payload["type"] == "chat.error"
        assert payload["code"] == "conversation_language_mismatch"
