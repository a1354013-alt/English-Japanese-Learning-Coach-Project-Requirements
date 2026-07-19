"""Explicit repository/domain exceptions for persisted chat storage."""

from __future__ import annotations


class ChatRepositoryError(Exception):
    """Base class for chat repository failures."""


class ConversationNotFoundError(ChatRepositoryError):
    """Raised when a conversation cannot be found for the requested user."""


class InvalidChatLanguageError(ChatRepositoryError):
    """Raised when a persisted-chat language is unsupported."""


class InvalidChatRoleError(ChatRepositoryError):
    """Raised when a persisted-chat role is unsupported."""


class InvalidChatPaginationError(ChatRepositoryError):
    """Raised when persisted-chat pagination arguments are invalid."""


class LessonLinkNotFoundError(ChatRepositoryError):
    """Raised when a requested lesson link target does not exist."""


class LessonLinkIntegrityError(ChatRepositoryError):
    """Raised when a requested lesson link is incompatible with the conversation."""


class IdempotencyConflictError(ChatRepositoryError):
    """Raised when an idempotency key is retried with incompatible content."""


class InvalidIdempotencyKeyError(ChatRepositoryError):
    """Raised when a persisted-chat idempotency key is blank or exceeds policy."""


class InvalidChatSummaryCheckpointError(ChatRepositoryError):
    """Raised when a persisted-chat summary checkpoint is outside valid bounds."""
