"""Static typing assertions for repository protocol conformance."""

from __future__ import annotations

from repositories.learning_session_repository import LearningSessionRepository
from repositories.protocols import LearningSessionRepositoryProtocol


def require_learning_session_repository_protocol(
    repository: LearningSessionRepository,
) -> LearningSessionRepositoryProtocol:
    return repository
