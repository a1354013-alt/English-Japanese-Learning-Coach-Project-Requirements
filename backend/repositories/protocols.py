"""Repository protocols for future feature-based extraction from the Database facade."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class PersistedChatRepositoryProtocol(Protocol):
    """Persistence contract reserved for future multi-message chat history storage."""

    def create_chat_session(
        self,
        *,
        user_id: str,
        language: str,
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
    ) -> str: ...

    def list_chat_messages(self, *, session_id: str, user_id: str, limit: int = 100) -> List[Dict[str, Any]]: ...


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
