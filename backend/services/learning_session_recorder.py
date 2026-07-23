"""Integration boundary for optional learning-session event recording."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Literal

from models import LearningSessionEntityType, LearningSessionEventMetadata, LearningSessionEventType

logger = logging.getLogger(__name__)
LearningSessionRecorderMode = Literal["strict", "tolerant"]


@dataclass(frozen=True)
class LearningSessionRecorderFailurePolicy:
    """Control whether optional session telemetry failures should fail primary operations."""

    mode: LearningSessionRecorderMode = "tolerant"

    @property
    def strict(self) -> bool:
        return self.mode == "strict"


class LearningSessionRecorder:
    """Append canonical learning-session events for existing feature workflows."""

    def __init__(self, database: Any, *, failure_policy: LearningSessionRecorderFailurePolicy | None = None) -> None:
        self._db = database
        self._failure_policy = failure_policy or LearningSessionRecorderFailurePolicy(mode=_recorder_mode_from_env())

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
        try:
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
                        "idempotency_key": idempotency_key,
                    },
                )
                return None
            event = self._db.learning_session_repository.append_event(
                session_id=active_session.session_id,
                user_id=user_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                idempotency_key=idempotency_key,
                metadata=metadata,
            )
        except Exception as exc:
            logger.exception(
                "learning_session_recording_failed",
                extra={
                    "user_id": user_id,
                    "language": normalized_language,
                    "event_type": str(event_type),
                    "entity_id": entity_id,
                    "idempotency_key": idempotency_key,
                    "mode": self._failure_policy.mode,
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


def _recorder_mode_from_env() -> LearningSessionRecorderMode:
    configured = os.environ.get("LEARNING_SESSION_RECORDER_MODE", "").strip().lower()
    if configured in {"strict", "tolerant"}:
        return configured  # type: ignore[return-value]
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return "strict"
    return "tolerant"


def build_learning_session_recorder(
    database: Any,
    *,
    strict: bool | None = None,
    mode: LearningSessionRecorderMode | None = None,
) -> LearningSessionRecorder:
    if mode is None:
        mode = "strict" if strict is True else "tolerant" if strict is False else _recorder_mode_from_env()
    policy = LearningSessionRecorderFailurePolicy(mode=mode)
    return LearningSessionRecorder(database, failure_policy=policy)
