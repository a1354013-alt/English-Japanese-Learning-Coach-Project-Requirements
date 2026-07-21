"""Persisted WebSocket chat workflow for learner conversations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from chat_scenarios import DEFAULT_SCENARIO_ID, get_scenario
from config import settings
from database import db
from fastapi import WebSocket, WebSocketDisconnect
from ollama_client import ollama_client
from repositories.errors import (
    ConversationNotFoundError,
    IdempotencyConflictError,
    InvalidChatScenarioError,
    InvalidIdempotencyKeyError,
)


@dataclass(frozen=True)
class ChatSocketSession:
    conversation_id: str
    language: str
    scenario_id: str
    scenario_label: str


class ChatManager:
    async def handle_chat(
        self,
        websocket: WebSocket,
        *,
        user_id: str,
        language: str,
        conversation_id: str | None,
        scenario_id: str | None,
    ) -> None:
        await websocket.accept()

        try:
            session = self._resolve_session(
                user_id=user_id,
                language=language,
                conversation_id=conversation_id,
                scenario_id=scenario_id,
            )
        except (ConversationNotFoundError, InvalidChatScenarioError) as exc:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "code": "conversation_bootstrap_failed",
                    "message": str(exc),
                }
            )
            await websocket.close(code=1008)
            return

        await websocket.send_json(
            {
                "type": "conversation.ready",
                "conversation_id": session.conversation_id,
                "scenario_id": session.scenario_id,
                "scenario_label": session.scenario_label,
                "language": session.language,
            }
        )

        try:
            while True:
                raw = await websocket.receive_text()
                await self._handle_turn(
                    websocket=websocket,
                    user_id=user_id,
                    session=session,
                    raw=raw,
                )
        except WebSocketDisconnect:
            return

    def _resolve_session(
        self,
        *,
        user_id: str,
        language: str,
        conversation_id: str | None,
        scenario_id: str | None,
    ) -> ChatSocketSession:
        normalized_language = db.chat_repository._normalize_language(language)

        if conversation_id:
            conversation = db.chat_repository.get_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
            )
            if conversation.language != normalized_language:
                raise InvalidChatScenarioError(
                    f"Conversation language {conversation.language} does not match active language {normalized_language}"
                )
            scenario = get_scenario(normalized_language, conversation.scenario_id)
            if scenario is None:
                raise InvalidChatScenarioError(
                    f"Unsupported chat scenario {conversation.scenario_id!r} for language {normalized_language}"
                )
            return ChatSocketSession(
                conversation_id=conversation.conversation_id,
                language=normalized_language,
                scenario_id=conversation.scenario_id,
                scenario_label=str(scenario["label"]),
            )

        requested_scenario_id = scenario_id or DEFAULT_SCENARIO_ID
        scenario = get_scenario(normalized_language, requested_scenario_id)
        if scenario is None:
            raise InvalidChatScenarioError(
                f"Unsupported chat scenario {requested_scenario_id!r} for language {normalized_language}"
            )
        conversation = db.chat_repository.create_conversation(
            user_id=user_id,
            language=normalized_language,
            scenario_id=requested_scenario_id,
            title=str(scenario["label"]),
        )
        return ChatSocketSession(
            conversation_id=conversation.conversation_id,
            language=normalized_language,
            scenario_id=conversation.scenario_id,
            scenario_label=str(scenario["label"]),
        )

    async def _handle_turn(
        self,
        *,
        websocket: WebSocket,
        user_id: str,
        session: ChatSocketSession,
        raw: str,
    ) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "code": "invalid_message_format",
                    "message": 'Invalid message format. Send JSON with "text" and "client_message_id".',
                }
            )
            return

        if not isinstance(payload, dict):
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "code": "invalid_message_shape",
                    "message": 'Message must be a JSON object with "text" and "client_message_id".',
                }
            )
            return

        text = str(payload.get("text", "")).strip()
        client_message_id = str(payload.get("client_message_id", "")).strip()
        if not text:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "code": "message_text_required",
                    "message": "text is required",
                    "client_message_id": client_message_id or None,
                }
            )
            return
        if not client_message_id:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "code": "client_message_id_required",
                    "message": "client_message_id is required",
                }
            )
            return

        try:
            persisted_user = db.chat_repository.append_message(
                conversation_id=session.conversation_id,
                user_id=user_id,
                role="user",
                content=text,
                metadata={"client_message_id": client_message_id},
                idempotency_key=client_message_id,
            )
        except (IdempotencyConflictError, InvalidIdempotencyKeyError) as exc:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "code": "idempotency_conflict",
                    "message": str(exc),
                    "client_message_id": client_message_id,
                }
            )
            return

        await websocket.send_json(
            {
                "type": "chat.user.persisted",
                "conversation_id": session.conversation_id,
                "scenario_id": session.scenario_id,
                "message": self._message_payload(persisted_user),
                "client_message_id": client_message_id,
            }
        )

        assistant_idempotency_key = f"assistant:{client_message_id}"
        try:
            assistant_message = db.chat_repository.append_message(
                conversation_id=session.conversation_id,
                user_id=user_id,
                role="assistant",
                content=await self._generate_assistant_text(
                    user_id=user_id,
                    session=session,
                    user_text=text,
                ),
                metadata={"client_message_id": client_message_id},
                idempotency_key=assistant_idempotency_key,
            )
        except IdempotencyConflictError as exc:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "code": "assistant_idempotency_conflict",
                    "message": str(exc),
                    "client_message_id": client_message_id,
                }
            )
            return
        except Exception:
            await websocket.send_json(
                {
                    "type": "chat.error",
                    "code": "provider_failure",
                    "message": "AI chat is currently unavailable.",
                    "client_message_id": client_message_id,
                }
            )
            return

        await websocket.send_json(
            {
                "type": "chat.assistant.persisted",
                "conversation_id": session.conversation_id,
                "scenario_id": session.scenario_id,
                "message": self._message_payload(assistant_message),
                "client_message_id": client_message_id,
            }
        )

    async def _generate_assistant_text(
        self,
        *,
        user_id: str,
        session: ChatSocketSession,
        user_text: str,
    ) -> str:
        if settings.chat_provider_mode.strip().lower() == "mock":
            return f"[{session.scenario_label}] I heard: {user_text}. What would you say next?"

        scenario = get_scenario(session.language, session.scenario_id)
        scenario_prompt = str(scenario["system_prompt"]) if scenario else "Practice a natural conversation."
        recent_messages = db.chat_repository.get_recent_messages(
            conversation_id=session.conversation_id,
            user_id=user_id,
            limit=8,
        )
        prompt_lines = []
        for item in recent_messages:
            if item.role == "system":
                continue
            speaker = "User" if item.role == "user" else "Assistant"
            prompt_lines.append(f"{speaker}: {item.content}")
        if not prompt_lines or prompt_lines[-1] != f"User: {user_text}":
            prompt_lines.append(f"User: {user_text}")

        response = await ollama_client.generate(
            prompt="\n".join(prompt_lines),
            system_prompt=(
                "You are a supportive language coach. "
                f"Scenario: {session.scenario_label}. "
                f"Language: {session.language}. "
                f"Instruction: {scenario_prompt} "
                "Respond in 1-3 sentences and end with one follow-up question."
            ),
            model=settings.small_model_name,
            format="text",
            use_cache=False,
            timeout_profile="chat",
        )
        if not response.get("success"):
            raise RuntimeError("chat provider unavailable")
        text = str(response.get("response", "")).strip()
        if not text:
            raise RuntimeError("empty assistant response")
        return text

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
