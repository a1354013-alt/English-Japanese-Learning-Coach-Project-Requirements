"""Integration boundary for optional learning-session event recording."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from models import LearningSessionEntityType, LearningSessionEventMetadata, LearningSessionEventType
from repositories.errors import (
    InvalidLearningSessionEventError,
    LearningSessionIdempotencyConflictError,
    LearningSessionNotFoundError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LearningSessionRecorderFailurePolicy:
    """Control whether optional session telemetry failures should fail primary operations."""

    strict: bool = False


class LearningSessionRecorder:
    """Append canonical learning-session events for existing feature workflows."""

    def __init__(self, database: Any, *, failure_policy: LearningSessionRecorderFailurePolicy | None = None) -> None:
        self._db = database
        self._failure_policy = failure_policy or LearningSessionRecorderFailurePolicy(
            strict=bool(os.environ.get("PYTEST_CURRENT_TEST"))
        )

    def record_event(
        self,
        *,
        user_id: str,
        language: str,
        event_type: LearningSessionEventType | str,
        entity_type: LearningSessionEntityType | str | None,
        entity_id: str | None,
        idempotency_key: str,
        metadata: LearningSessionEventMetadata | None = None,
    ):
        normalized_language = str(language).strip().upper()
        active_session = self._db.learning_session_repository.find_active_session(
            user_id=user_id,
            language=normalized_language,
        )
        if active_session is None:
            logger.info(
                "learning_session_recording_skipped_no_active_session",
                extra={
                    "user_id": user_id,
                    "language": normalized_language,
                    "event_type": str(event_type),
                    "entity_id": entity_id,
                },
            )
            return None

        try:
            event = self._db.learning_session_repository.append_event(
                session_id=active_session.session_id,
                user_id=user_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                idempotency_key=idempotency_key,
                metadata=metadata,
            )
        except (
            InvalidLearningSessionEventError,
            LearningSessionIdempotencyConflictError,
            LearningSessionNotFoundError,
            AssertionError,
        ):
            raise
        except Exception as exc:
            logger.exception(
                "learning_session_recording_failed",
                extra={
                    "user_id": user_id,
                    "language": normalized_language,
                    "event_type": str(event_type),
                    "entity_id": entity_id,
                    "idempotency_key": idempotency_key,
                    "strict": self._failure_policy.strict,
                },
            )
            if self._failure_policy.strict:
                raise RuntimeError("Learning session recording failed") from exc
            return None

        logger.info(
            "learning_session_recorded",
            extra={
                "session_id": active_session.session_id,
                "user_id": user_id,
                "language": normalized_language,
                "event_type": str(event.event_type.value),
                "entity_id": entity_id,
                "idempotency_key": idempotency_key,
                "sequence_number": event.sequence_number,
            },
        )
        return event


def build_learning_session_recorder(database: Any, *, strict: bool | None = None) -> LearningSessionRecorder:
    policy = LearningSessionRecorderFailurePolicy(
        strict=bool(os.environ.get("PYTEST_CURRENT_TEST")) if strict is None else strict
    )
    return LearningSessionRecorder(database, failure_policy=policy)
