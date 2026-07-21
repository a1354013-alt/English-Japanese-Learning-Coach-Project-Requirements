"""Bounded persisted-chat context assembly for WebSocket turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from config import settings

if TYPE_CHECKING:
    from models import ChatConversationRecord, ChatMessageRecord
    from repositories.chat_repository import ChatRepository


@dataclass(frozen=True)
class ChatContext:
    system_prompt: str
    prompt: str
    messages: tuple["ChatMessageRecord", ...]


class ChatContextBuilder:
    """Build provider prompts from persisted messages with fixed bounds."""

    def __init__(
        self,
        repository: "ChatRepository",
        *,
        recent_message_limit: int | None = None,
        max_chars: int | None = None,
    ) -> None:
        self._repository = repository
        self._recent_message_limit = max(1, recent_message_limit or settings.chat_recent_message_limit)
        self._max_chars = max(1, max_chars or settings.chat_context_max_chars)

    def build(
        self,
        *,
        conversation: "ChatConversationRecord",
        user_id: str,
        scenario: str,
    ) -> ChatContext:
        system_prompt = (
            "You are a supportive language coach. "
            f"Scenario: {scenario}. Language: {conversation.language}. "
            "Memory fallback: No stored user memory is available in this build. "
            "Respond in 1-3 sentences and end with one follow-up question."
        )
        page = self._repository.get_messages_page(
            conversation_id=conversation.conversation_id,
            user_id=user_id,
            limit=self._recent_message_limit,
            after_sequence=conversation.summary_through_sequence or None,
        )
        messages = tuple(page.messages[-self._recent_message_limit :])
        lines: list[str] = []
        if conversation.summary:
            lines.append(f"Conversation summary through sequence {conversation.summary_through_sequence}:")
            lines.append(conversation.summary)
        for message in messages:
            if message.role == "user":
                lines.append(f"User: {message.content}")
            elif message.role == "assistant":
                lines.append(f"Assistant: {message.content}")

        prompt = self._trim_lines_to_budget(lines)
        return ChatContext(system_prompt=system_prompt, prompt=prompt, messages=messages)

    def _trim_lines_to_budget(self, lines: list[str]) -> str:
        kept: list[str] = []
        total = 0
        for line in reversed(lines):
            line_len = len(line) + 1
            if kept and total + line_len > self._max_chars:
                break
            if not kept and line_len > self._max_chars:
                kept.append(line[-self._max_chars :])
                break
            kept.append(line)
            total += line_len
        return "\n".join(reversed(kept))
