"""Repository protocols for feature-based extraction from the Database facade."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from models import ChatConversationRecord, ChatMessagePage, ChatMessageRecord


class PersistedChatRepositoryProtocol(Protocol):
    """Persistence contract for persisted multi-message chat history storage."""

    def create_chat_session(
        self,
        *,
        user_id: str,
        language: str,
        scenario_id: str = "daily_conversation",
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str: ...

    def append_chat_message(
        self,
        *,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> str: ...

    def list_chat_messages(self, *, session_id: str, user_id: str, limit: int = 100) -> List[Dict[str, Any]]: ...

    def create_conversation(
        self,
        *,
        user_id: str,
        language: str,
        title: Optional[str] = None,
        lesson_id: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> ChatConversationRecord: ...

    def list_conversations(
        self,
        *,
        user_id: str,
        language: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ChatConversationRecord]: ...

    def get_conversation(self, *, conversation_id: str, user_id: str) -> ChatConversationRecord: ...

    def rename_conversation(
        self,
        *,
        conversation_id: str,
        user_id: str,
        title: str,
    ) -> ChatConversationRecord: ...

    def set_conversation_lesson_link(
        self,
        *,
        conversation_id: str,
        user_id: str,
        lesson_id: Optional[str],
    ) -> ChatConversationRecord: ...

    def update_conversation_summary(
        self,
        *,
        conversation_id: str,
        user_id: str,
        summary: Optional[str],
        summary_through_sequence: Optional[int] = None,
    ) -> ChatConversationRecord: ...

    def delete_conversation(self, *, conversation_id: str, user_id: str) -> None: ...

    def clear_conversations_for_demo_user(self, *, user_id: str = "default_user") -> int: ...

    def get_messages_page(
        self,
        *,
        conversation_id: str,
        user_id: str,
        limit: int = 100,
        before_sequence: Optional[int] = None,
        after_sequence: Optional[int] = None,
        descending: bool = False,
    ) -> ChatMessagePage: ...

    def get_recent_messages(
        self,
        *,
        conversation_id: str,
        user_id: str,
        limit: int = 20,
    ) -> List[ChatMessageRecord]: ...


class LearningSessionRepositoryProtocol(Protocol):
    """Persistence contract reserved for future long-lived guided learning sessions."""

    def create_learning_session(
        self,
        *,
        user_id: str,
        language: str,
        session_type: str,
        lesson_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str: ...

    def record_learning_session_step(
        self,
        *,
        session_id: str,
        user_id: str,
        step_type: str,
        payload: Dict[str, Any],
    ) -> str: ...

    def complete_learning_session(
        self,
        *,
        session_id: str,
        user_id: str,
        outcome: Dict[str, Any],
    ) -> None: ...
