"""WebSocket handler for AI role-play chat."""
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config import settings
from database import db
from fastapi import WebSocket, WebSocketDisconnect
from ollama_client import ollama_client
from repositories.errors import (
    ConversationNotFoundError,
    IdempotencyConflictError,
    InvalidIdempotencyKeyError,
)
from services.chat_context_builder import ChatContextBuilder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatScenario:
    identifier: str
    label: str
    prompt: str


SCENARIOS: dict[str, ChatScenario] = {
    "daily_conversation": ChatScenario(
        identifier="daily_conversation",
        label="Daily Conversation",
        prompt="Practice a natural everyday conversation with practical follow-up questions.",
    ),
    "travel": ChatScenario(
        identifier="travel",
        label="Travel",
        prompt="Practice travel situations such as transit, hotels, directions, and polite requests.",
    ),
    "restaurant": ChatScenario(
        identifier="restaurant",
        label="Restaurant",
        prompt="Practice ordering food, asking about dishes, and handling restaurant conversations.",
    ),
    "workplace": ChatScenario(
        identifier="workplace",
        label="Workplace",
        prompt="Practice professional workplace conversation with clear, respectful phrasing.",
    ),
}


class ChatManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._turn_locks: dict[str, asyncio.Lock] = {}
        # Local single-process scope: one retained lock per conversation for this manager lifetime.

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def build_prompt(self, history: List[Dict[str, Any]], user_text: str) -> str:
        prompt_messages = (history + [{"role": "user", "content": user_text}])[-8:]
        lines = []
        for msg in prompt_messages:
            role = msg["role"]
            if role == "user":
                lines.append(f"User: {msg['content']}")
            elif role == "assistant":
                lines.append(f"Assistant: {msg['content']}")
        return "\n".join(lines)

    async def handle_chat(
        self,
        websocket: WebSocket,
        language: str,
        scenario: str,
        conversation_id: Optional[str] = None,
    ) -> None:
        user_id = settings.default_user_id
        scenario_result = self._resolve_scenario(scenario)
        if isinstance(scenario_result, dict):
            try:
                await websocket.accept()
                self.active_connections.append(websocket)
                await websocket.send_json(scenario_result)
                await websocket.close(code=1008)
            finally:
                self.disconnect(websocket)
            return
        scenario_config = scenario_result
        try:
            conversation = self._resolve_conversation(
                user_id=user_id,
                language=language,
                scenario=scenario_config,
                conversation_id=conversation_id,
            )
        except ConversationNotFoundError:
            await self._send_startup_error(
                websocket,
                {"type": "chat.error", "code": "conversation_not_found", "message": "Conversation not found."},
            )
            return
        except ValueError as exc:
            await self._send_startup_error(
                websocket,
                {
                    "type": "chat.error",
                    "code": "conversation_language_mismatch",
                    "message": str(exc),
                },
            )
            return

        try:
            await self.connect(websocket)
            await websocket.send_json(
                {
                    "type": "conversation.ready",
                    "conversation_id": conversation.conversation_id,
                    "language": conversation.language,
                }
            )
            while True:
                raw = await websocket.receive_text()
                parsed = self._parse_payload(raw)
                if parsed.get("error"):
                    await websocket.send_json(parsed["error"])
                    continue
                user_text = parsed["text"]
                client_message_id = parsed.get("client_message_id")
                lock = self._conversation_lock(conversation.conversation_id)
                async with lock:
                    await self._handle_turn(
                        websocket=websocket,
                        user_id=user_id,
                        conversation_id=conversation.conversation_id,
                        language=language,
                        scenario=scenario_config.prompt,
                        user_text=user_text,
                        client_message_id=client_message_id,
                    )
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("chat_websocket_failed", extra={"conversation_id": conversation.conversation_id})
            try:
                await websocket.send_json(
                    {
                        "type": "chat.error",
                        "role": "system",
                        "code": "internal_error",
                        "text": "Chat is temporarily unavailable.",
                        "message": "Chat is temporarily unavailable.",
                        "conversation_id": conversation.conversation_id,
                    }
                )
                await websocket.close(code=1011)
            except Exception:
                logger.exception("chat_websocket_error_delivery_failed", extra={"conversation_id": conversation.conversation_id})
        finally:
            self.disconnect(websocket)

    def _conversation_lock(self, conversation_id: str) -> asyncio.Lock:
        lock = self._turn_locks.get(conversation_id)
        if lock is None:
            lock = asyncio.Lock()
            self._turn_locks[conversation_id] = lock
        return lock

    async def _send_startup_error(self, websocket: WebSocket, event: dict[str, Any]) -> None:
        try:
            await self.connect(websocket)
            await websocket.send_json(event)
            await websocket.close(code=1008)
        finally:
            self.disconnect(websocket)

    def _resolve_scenario(self, scenario: str) -> ChatScenario | dict[str, str]:
        normalized = scenario.strip().lower()
        if not normalized:
            normalized = "daily_conversation"
        if len(normalized) > 40 or "\n" in scenario or "\r" in scenario:
            return self._validation_error("invalid_scenario", "Unsupported chat scenario.")
        normalized = normalized.replace("-", "_").replace(" ", "_")
        if normalized not in SCENARIOS:
            return self._validation_error("invalid_scenario", "Unsupported chat scenario.")
        return SCENARIOS[normalized]

    def _resolve_conversation(self, *, user_id: str, language: str, scenario: ChatScenario, conversation_id: Optional[str]):
        if not conversation_id:
            return db.chat_repository.create_conversation(
                user_id=user_id,
                language=language,
                title=f"{language} {scenario.label}".strip(),
            )
        conversation = db.chat_repository.get_conversation(conversation_id=conversation_id, user_id=user_id)
        if conversation.language != language:
            raise ValueError("Conversation language does not match the WebSocket language.")
        return conversation

    def _parse_payload(self, raw: str) -> Dict[str, Any]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"error": self._validation_error("invalid_json", 'Invalid message format. Send JSON: {"text":"your message"}.')}
        if not isinstance(payload, dict):
            return {"error": self._validation_error("invalid_payload", 'Message must be a JSON object with a "text" field.')}
        unknown = set(payload) - {"text", "client_message_id"}
        if unknown:
            return {"error": self._validation_error("unknown_fields", f"Unknown fields are not supported: {', '.join(sorted(unknown))}.")}
        user_text = str(payload.get("text", "")).strip()
        if not user_text:
            return {"error": self._validation_error("blank_text", "Text must not be blank.")}
        if len(user_text) > settings.chat_message_max_chars:
            return {
                "error": self._validation_error(
                    "text_too_long",
                    f"Text must be at most {settings.chat_message_max_chars} characters.",
                )
            }
        client_message_id = payload.get("client_message_id")
        if client_message_id is not None:
            client_message_id = str(client_message_id).strip()
            if not client_message_id:
                return {"error": self._validation_error("blank_client_message_id", "client_message_id must not be blank.")}
            if len(client_message_id) > settings.chat_client_message_id_max_chars:
                return {
                    "error": self._validation_error(
                        "client_message_id_too_long",
                        f"client_message_id must be at most {settings.chat_client_message_id_max_chars} characters.",
                    )
                }
        return {"text": user_text, "client_message_id": client_message_id}

    def _validation_error(self, code: str, message: str) -> Dict[str, str]:
        return {"type": "chat.validation_error", "role": "system", "code": code, "text": message, "message": message}

    async def _handle_turn(
        self,
        *,
        websocket: WebSocket,
        user_id: str,
        conversation_id: str,
        language: str,
        scenario: str,
        user_text: str,
        client_message_id: Optional[str],
    ) -> None:
        user_key = f"user:{client_message_id}" if client_message_id else None
        try:
            user_message = db.chat_repository.append_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="user",
                content=user_text,
                metadata={"source": "websocket", "client_message_id": client_message_id} if client_message_id else {"source": "websocket"},
                idempotency_key=user_key,
            )
        except (IdempotencyConflictError, InvalidIdempotencyKeyError):
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "role": "system",
                    "code": "idempotency_conflict",
                    "text": "This client_message_id was already used for a different chat turn.",
                    "message": "This client_message_id was already used for a different chat turn.",
                    "conversation_id": conversation_id,
                }
            )
            return

        await websocket.send_json(
            {
                "type": "chat.user.persisted",
                "conversation_id": conversation_id,
                "message_id": user_message.message_id,
                "sequence_number": user_message.sequence_number,
                "client_message_id": client_message_id,
            }
        )

        assistant_key = f"assistant:{user_message.message_id}"
        existing_assistant = db.chat_repository.get_message_by_idempotency_key(
            conversation_id=conversation_id,
            user_id=user_id,
            idempotency_key=assistant_key,
        )
        if existing_assistant is not None:
            await self._send_assistant(websocket, existing_assistant)
            return

        conversation = db.chat_repository.get_conversation(conversation_id=conversation_id, user_id=user_id)
        context = ChatContextBuilder(db.chat_repository).build(
            conversation=conversation,
            user_id=user_id,
            scenario=scenario,
        )
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
                }
            )
            return

        ai_text = str(response.get("response", "")).strip()
        if not ai_text:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "role": "system",
                    "code": "empty_provider_response",
                    "text": "AI chat returned an empty response. Please retry.",
                    "message": "AI chat returned an empty response. Please retry.",
                    "conversation_id": conversation_id,
                    "user_message_id": user_message.message_id,
                }
            )
            return
        if len(ai_text) > settings.chat_assistant_response_max_chars:
            ai_text = ai_text[: settings.chat_assistant_response_max_chars].rstrip()
        assistant_message = db.chat_repository.append_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=ai_text,
            metadata={"source": "ollama", "user_message_id": user_message.message_id},
            idempotency_key=assistant_key,
        )
        await self._send_assistant(websocket, assistant_message)

    async def _send_assistant(self, websocket: WebSocket, message: Any) -> None:
        await websocket.send_json(
            {
                "type": "chat.assistant",
                "role": "assistant",
                "text": message.content,
                "conversation_id": message.conversation_id,
                "message_id": message.message_id,
                "sequence_number": message.sequence_number,
            }
        )


chat_manager = ChatManager()
