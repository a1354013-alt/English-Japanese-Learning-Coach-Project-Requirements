"""Repository protocols for feature-based extraction from the Database facade."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from models import (
    ChatConversationRecord,
    ChatMessagePage,
    ChatMessageRecord,
    LearningSessionEntityType,
    LearningSessionEventHistoryPage,
    LearningSessionEventMetadata,
    LearningSessionEventRecord,
    LearningSessionEventType,
    LearningSessionHistoryPage,
    LearningSessionRecord,
    LearningSessionSummary,
)


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
        scenario_id: str = "daily_conversation",
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
    """Persistence contract for Phase 1 learning-session storage and summaries."""

    def start_session(
        self,
        *,
        user_id: str,
        language: str,
        planned_minutes: Optional[int] = None,
    ) -> LearningSessionRecord: ...

    def get_session(self, *, session_id: str, user_id: str) -> LearningSessionRecord: ...

    def find_active_session(self, *, user_id: str, language: str) -> Optional[LearningSessionRecord]: ...

    def list_session_history(
        self,
        *,
        user_id: str,
        language: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> LearningSessionHistoryPage: ...

    def append_event(
        self,
        *,
        session_id: str,
        user_id: str,
        event_type: LearningSessionEventType | str,
        entity_type: LearningSessionEntityType | str | None = None,
        entity_id: Optional[str] = None,
        metadata: Optional[LearningSessionEventMetadata] = None,
        idempotency_key: Optional[str] = None,
    ) -> LearningSessionEventRecord: ...

    def list_events(
        self,
        *,
        session_id: str,
        user_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> LearningSessionEventHistoryPage: ...

    def complete_session(
        self,
        *,
        session_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> LearningSessionRecord: ...

    def abandon_session(
        self,
        *,
        session_id: str,
        user_id: str,
    ) -> LearningSessionRecord: ...

    def produce_summary(self, *, session_id: str, user_id: str) -> LearningSessionSummary: ...

    def delete_session(self, *, session_id: str, user_id: str) -> None: ...

    def clear_local_demo_user_session_data(self, *, user_id: str) -> int: ...
