"""Repository-boundary protocols reserved for incremental v1.5 extraction work."""

from .protocols import LearningSessionRepositoryProtocol, PersistedChatRepositoryProtocol

__all__ = [
    "LearningSessionRepositoryProtocol",
    "PersistedChatRepositoryProtocol",
]
