"""Persisted WebSocket chat workflow for learner conversations."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from typing import Any

from chat_contract import USER_MESSAGE_IDEMPOTENCY_PREFIX
from chat_scenarios import DEFAULT_SCENARIO_ID, get_scenario
from config import settings
from database import db
from fastapi import WebSocket, WebSocketDisconnect
from models import ChatScenarioId, LanguageCode
from ollama_client import ollama_client
from repositories.errors import (
    ConversationNotFoundError,
    IdempotencyConflictError,
    InvalidChatScenarioError,
    InvalidIdempotencyKeyError,
)
from services.chat_context_builder import ChatContextBuilder
from services.learning_session_recorder import build_learning_session_recorder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatSocketSession:
    conversation_id: str
    language: str
    scenario_id: str
    scenario_label: str
    scenario_prompt: str


class ConversationLanguageMismatchError(ValueError):
    """Raised when a conversation language does not match the active socket language."""


class ConversationScenarioMismatchError(ValueError):
    """Raised when a reconnect attempts to change a persisted conversation scenario."""


class ChatManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._turn_locks: dict[str, asyncio.Lock] = {}
        self._active_handlers = 0
        self._handler_idle = asyncio.Condition()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def build_prompt(self, history: list[dict[str, Any]], user_text: str) -> str:
        prompt_messages = (history + [{"role": "user", "content": user_text}])[-8:]
        lines: list[str] = []
        for message in prompt_messages:
            role = str(message.get("role", "")).strip().lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            if role == "user":
                lines.append(f"User: {content}")
            elif role == "assistant":
                lines.append(f"Assistant: {content}")
        return "\n".join(lines)

    def _mock_chat_response(
        self,
        *,
        language: str,
        scenario_id: str | None,
        user_text: str,
    ) -> dict[str, Any]:
        normalized_language: LanguageCode = db.chat_repository._normalize_language(language)  # type: ignore[assignment]
        resolved_scenario_id = scenario_id or DEFAULT_SCENARIO_ID
        scenario = get_scenario(normalized_language, resolved_scenario_id)
        scenario_label = str(scenario["label"]) if scenario is not None else resolved_scenario_id
        return {"success": True, "response": f"[{scenario_label}] I heard: {user_text}"}

    async def handle_chat(
        self,
        websocket: WebSocket,
        *,
        user_id: str,
        language: str,
        conversation_id: str | None,
        scenario_id: str | None,
    ) -> None:
        async with self._handler_idle:
            self._active_handlers += 1

        try:
            session = self._resolve_session(
                user_id=user_id,
                language=language,
                conversation_id=conversation_id,
                scenario_id=scenario_id,
            )
        except ConversationNotFoundError:
            await self._send_startup_error(
                websocket,
                {"type": "chat.error", "code": "conversation_not_found", "message": "Conversation not found."},
            )
            await self._handler_finished()
            return
        except ConversationLanguageMismatchError as exc:
            await self._send_startup_error(
                websocket,
                {"type": "chat.error", "code": "conversation_language_mismatch", "message": str(exc)},
            )
            await self._handler_finished()
            return
        except ConversationScenarioMismatchError as exc:
            await self._send_startup_error(
                websocket,
                {"type": "chat.error", "code": "conversation_scenario_mismatch", "message": str(exc)},
            )
            await self._handler_finished()
            return
        except InvalidChatScenarioError as exc:
            await self._send_startup_error(
                websocket,
                {"type": "chat.validation_error", "code": "invalid_scenario", "message": str(exc)},
            )
            await self._handler_finished()
            return

        try:
            await self.connect(websocket)
            await websocket.send_json(
                {
                    "type": "conversation.ready",
                    "conversation_id": session.conversation_id,
                    "language": session.language,
                    "scenario_id": session.scenario_id,
                    "scenario_label": session.scenario_label,
                }
            )
            lock = self._conversation_lock(session.conversation_id)
            while True:
                raw = await websocket.receive_text()
                parsed = self._parse_payload(raw)
                if parsed.get("error"):
                    await websocket.send_json(parsed["error"])
                    continue
                async with lock:
                    await self._handle_turn(
                        websocket=websocket,
                        user_id=user_id,
                        conversation_id=session.conversation_id,
                        language=session.language,
                        scenario=session.scenario_prompt,
                        scenario_id=session.scenario_id,
                        user_text=str(parsed["text"]),
                        client_message_id=parsed.get("client_message_id"),
                    )
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("chat_websocket_failed", extra={"conversation_id": session.conversation_id})
            try:
                await websocket.send_json(
                    {
                        "type": "chat.error",
                        "role": "system",
                        "code": "internal_error",
                        "text": "Chat is temporarily unavailable.",
                        "message": "Chat is temporarily unavailable.",
                        "conversation_id": session.conversation_id,
                    }
                )
                await websocket.close(code=1011)
            except Exception:
                logger.exception(
                    "chat_websocket_error_delivery_failed",
                    extra={"conversation_id": session.conversation_id},
                )
        finally:
            self.disconnect(websocket)
            await self._handler_finished()

    def _resolve_session(
        self,
        *,
        user_id: str,
        language: str,
        conversation_id: str | None,
        scenario_id: str | None,
    ) -> ChatSocketSession:
        normalized_language: LanguageCode = db.chat_repository._normalize_language(language)  # type: ignore[assignment]
        requested_scenario_id: ChatScenarioId = db.chat_repository._normalize_scenario_id(  # type: ignore[assignment]
            scenario_id if scenario_id is not None else DEFAULT_SCENARIO_ID
        )

        if conversation_id:
            conversation = db.chat_repository.get_conversation(conversation_id=conversation_id, user_id=user_id)
            if conversation.language != normalized_language:
                raise ConversationLanguageMismatchError(
                    "Conversation language does not match the WebSocket language."
                )
            if scenario_id is not None and conversation.scenario_id != requested_scenario_id:
                raise ConversationScenarioMismatchError(
                    "Conversation scenario does not match the WebSocket scenario."
                )
            resolved_scenario_id = conversation.scenario_id
        else:
            resolved_scenario_id = requested_scenario_id
            scenario = get_scenario(normalized_language, resolved_scenario_id)
            if scenario is None:
                raise InvalidChatScenarioError(
                    f"Unsupported chat scenario {resolved_scenario_id!r} for language {normalized_language}"
                )
            conversation = db.chat_repository.create_conversation(
                user_id=user_id,
                language=normalized_language,
                scenario_id=resolved_scenario_id,
                title=str(scenario["label"]),
            )

        scenario = get_scenario(normalized_language, resolved_scenario_id)
        if scenario is None:
            raise InvalidChatScenarioError(
                f"Unsupported chat scenario {resolved_scenario_id!r} for language {normalized_language}"
            )
        return ChatSocketSession(
            conversation_id=conversation.conversation_id,
            language=normalized_language,
            scenario_id=resolved_scenario_id,
            scenario_label=str(scenario["label"]),
            scenario_prompt=str(scenario["system_prompt"]),
        )

    def _parse_payload(self, raw: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "error": self._validation_error(
                    "invalid_json",
                    'Invalid message format. Send JSON: {"text":"your message"}.',
                )
            }
        if not isinstance(payload, dict):
            return {
                "error": self._validation_error(
                    "invalid_payload",
                    'Message must be a JSON object with a "text" field.',
                )
            }
        client_message_id = payload.get("client_message_id")
        if client_message_id is not None:
            client_message_id = str(client_message_id).strip()
            if not client_message_id:
                return {
                    "error": self._validation_error(
                        "blank_client_message_id",
                        "client_message_id must not be blank.",
                    )
                }
            if len(client_message_id) > settings.chat_client_message_id_max_chars:
                return {
                    "error": self._validation_error(
                        "client_message_id_too_long",
                        f"client_message_id must be at most {settings.chat_client_message_id_max_chars} characters.",
                    )
                }

        unknown = set(payload) - {"text", "client_message_id"}
        if unknown:
            return {
                "error": self._validation_error(
                    "unknown_fields",
                    f"Unknown fields are not supported: {', '.join(sorted(unknown))}.",
                    client_message_id=client_message_id,
                )
            }

        user_text = str(payload.get("text", "")).strip()
        if not user_text:
            return {
                "error": self._validation_error(
                    "blank_text",
                    "Text must not be blank.",
                    client_message_id=client_message_id,
                )
            }
        if len(user_text) > settings.chat_message_max_chars:
            return {
                "error": self._validation_error(
                    "text_too_long",
                    f"Text must be at most {settings.chat_message_max_chars} characters.",
                    client_message_id=client_message_id,
                )
            }

        return {"text": user_text, "client_message_id": client_message_id}

    def _validation_error(
        self,
        code: str,
        message: str,
        *,
        client_message_id: str | None = None,
    ) -> dict[str, str]:
        event = {"type": "chat.validation_error", "role": "system", "code": code, "text": message, "message": message}
        if client_message_id is not None:
            event["client_message_id"] = client_message_id
        return event

    def _conversation_lock(self, conversation_id: str) -> asyncio.Lock:
        lock = self._turn_locks.get(conversation_id)
        if lock is None:
            lock = asyncio.Lock()
            self._turn_locks[conversation_id] = lock
        return lock

    async def _handler_finished(self) -> None:
        async with self._handler_idle:
            self._active_handlers -= 1
            if self._active_handlers == 0:
                self._handler_idle.notify_all()

    async def _send_startup_error(self, websocket: WebSocket, event: dict[str, Any]) -> None:
        try:
            await self.connect(websocket)
            await websocket.send_json(event)
            await websocket.close(code=1008)
        finally:
            self.disconnect(websocket)

    async def shutdown(self) -> None:
        sockets = list(self.active_connections)
        for socket in sockets:
            with contextlib.suppress(Exception):
                await socket.close(code=1001)
        async with self._handler_idle:
            await self._handler_idle.wait_for(lambda: self._active_handlers == 0)
        self.active_connections.clear()
        self._turn_locks.clear()

    def forget_conversation(self, conversation_id: str) -> bool:
        lock = self._turn_locks.get(conversation_id)
        if lock is None:
            return False
        if lock.locked():
            return False
        del self._turn_locks[conversation_id]
        return True

    async def _handle_turn(
        self,
        *,
        websocket: WebSocket,
        user_id: str,
        conversation_id: str,
        language: str,
        scenario: str,
        scenario_id: str | None = None,
        user_text: str,
        client_message_id: str | None,
    ) -> None:
        user_key = f"{USER_MESSAGE_IDEMPOTENCY_PREFIX}{client_message_id}" if client_message_id else None
        metadata = {"source": "websocket"}
        if client_message_id:
            metadata["client_message_id"] = client_message_id

        try:
            user_message = db.chat_repository.append_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="user",
                content=user_text,
                metadata=metadata,
                idempotency_key=user_key,
            )
        except InvalidIdempotencyKeyError:
            await websocket.send_json(
                {
                    "type": "chat.validation_error",
                    "role": "system",
                    "code": "client_message_id_too_long",
                    "text": f"client_message_id must be at most {settings.chat_client_message_id_max_chars} characters.",
                    "message": f"client_message_id must be at most {settings.chat_client_message_id_max_chars} characters.",
                    "conversation_id": conversation_id,
                    "client_message_id": client_message_id,
                }
            )
            return
        except IdempotencyConflictError:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "role": "system",
                    "code": "idempotency_conflict",
                    "text": "This client_message_id was already used for a different chat turn.",
                    "message": "This client_message_id was already used for a different chat turn.",
                    "conversation_id": conversation_id,
                    "client_message_id": client_message_id,
                }
            )
            return

        await websocket.send_json(
            {
                "type": "chat.user.persisted",
                "conversation_id": conversation_id,
                "scenario_id": scenario_id,
                "message": self._message_payload(user_message),
                "client_message_id": client_message_id,
                "message_id": user_message.message_id,
                "sequence_number": user_message.sequence_number,
            }
        )

        assistant_key = f"assistant:{user_message.message_id}"
        existing_assistant = db.chat_repository.get_message_by_idempotency_key(
            conversation_id=conversation_id,
            user_id=user_id,
            idempotency_key=assistant_key,
        )
        if existing_assistant is not None:
            await self._send_assistant(
                websocket=websocket,
                message=existing_assistant,
                client_message_id=client_message_id,
                scenario_id=scenario_id,
            )
            return

        conversation = db.chat_repository.get_conversation(conversation_id=conversation_id, user_id=user_id)
        context = ChatContextBuilder(db.chat_repository).build(
            conversation=conversation,
            user_id=user_id,
            scenario=scenario,
        )
        if settings.chat_provider_mode == "mock":
            response = self._mock_chat_response(
                language=language,
                scenario_id=scenario_id,
                user_text=user_text,
            )
        else:
            response = await ollama_client.generate(
                prompt=context.prompt,
                system_prompt=context.system_prompt,
                model=settings.small_model_name,
                format="text",
                use_cache=False,
                timeout_profile="chat",
            )
        if not response.get("success"):
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "role": "system",
                    "code": "provider_unavailable",
                    "text": "AI chat is currently unavailable.",
                    "message": "AI chat is currently unavailable.",
                    "conversation_id": conversation_id,
                    "user_message_id": user_message.message_id,
                    "client_message_id": client_message_id,
                }
            )
            return

        assistant_text = str(response.get("response", "")).strip()
        if not assistant_text:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "role": "system",
                    "code": "empty_provider_response",
                    "text": "AI chat returned an empty response. Please retry.",
                    "message": "AI chat returned an empty response. Please retry.",
                    "conversation_id": conversation_id,
                    "user_message_id": user_message.message_id,
                    "client_message_id": client_message_id,
                }
            )
            return
        if len(assistant_text) > settings.chat_assistant_response_max_chars:
            assistant_text = assistant_text[: settings.chat_assistant_response_max_chars].rstrip()

        assistant_message = db.chat_repository.append_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_text,
            metadata={"source": "ollama", "user_message_id": user_message.message_id},
            idempotency_key=assistant_key,
        )
        build_learning_session_recorder(db).record_event(
            user_id=user_id,
            language=language,
            event_type="chat_turn_completed",
            entity_type="conversation",
            entity_id=conversation_id,
            idempotency_key=f"chat-turn:{assistant_message.message_id}",
        )
        await self._send_assistant(
            websocket=websocket,
            message=assistant_message,
            client_message_id=client_message_id,
            scenario_id=scenario_id,
        )

    async def _send_assistant(
        self,
        *,
        websocket: WebSocket,
        message: Any,
        client_message_id: str | None,
        scenario_id: str | None,
    ) -> None:
        await websocket.send_json(
            {
                "type": "chat.assistant.persisted",
                "conversation_id": message.conversation_id,
                "scenario_id": scenario_id,
                "message": self._message_payload(message),
                "client_message_id": client_message_id,
                "role": "assistant",
                "text": message.content,
                "message_id": message.message_id,
                "sequence_number": message.sequence_number,
            }
        )

    def _message_payload(self, message: Any) -> dict[str, Any]:
        return {
            "message_id": message.message_id,
            "conversation_id": message.conversation_id,
            "role": message.role,
            "content": message.content,
            "sequence_number": message.sequence_number,
            "metadata": message.metadata,
            "created_at": message.created_at.isoformat(),
        }


chat_manager = ChatManager()
