"""Repository-boundary protocols and chat persistence exports."""

from .chat_repository import ChatRepository
from .errors import (
    ChatRepositoryError,
    ConversationNotFoundError,
    IdempotencyConflictError,
    InvalidChatLanguageError,
    InvalidChatPaginationError,
    InvalidChatRoleError,
    LessonLinkNotFoundError,
)
from .protocols import LearningSessionRepositoryProtocol, PersistedChatRepositoryProtocol

__all__ = [
    "ChatRepository",
    "ChatRepositoryError",
    "ConversationNotFoundError",
    "IdempotencyConflictError",
    "InvalidChatLanguageError",
    "InvalidChatPaginationError",
    "InvalidChatRoleError",
    "LearningSessionRepositoryProtocol",
    "LessonLinkNotFoundError",
    "PersistedChatRepositoryProtocol",
]
