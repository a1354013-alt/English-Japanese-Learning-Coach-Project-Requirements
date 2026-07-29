"""Integration boundary for optional learning-session event recording."""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Literal

from models import LearningSessionEntityType, LearningSessionEventMetadata, LearningSessionEventType
from time_utils import local_now

logger = logging.getLogger(__name__)
LearningSessionRecorderMode = Literal["strict", "tolerant"]


@dataclass(frozen=True)
class LearningSessionRecorderFailurePolicy:
    """Control whether optional session telemetry failures should fail primary operations."""

    mode: LearningSessionRecorderMode = "tolerant"

    @property
    def strict(self) -> bool:
        return self.mode == "strict"


@dataclass
class LearningSessionRecorderDiagnostics:
    total_successes: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_failure_error: str | None = None
    last_failure_event_type: str | None = None
    last_failure_entity_type: str | None = None
    last_failure_entity_id: str | None = None


class LearningSessionRecorderHealthState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._diagnostics = LearningSessionRecorderDiagnostics()

    def record_success(self) -> None:
        now = local_now().isoformat()
        with self._lock:
            self._diagnostics.total_successes += 1
            self._diagnostics.consecutive_failures = 0
            self._diagnostics.last_success_at = now

    def record_failure(
        self,
        *,
        event_type: LearningSessionEventType | str,
        entity_type: LearningSessionEntityType | str | None,
        entity_id: str | None,
        error: Exception,
    ) -> None:
        now = local_now().isoformat()
        with self._lock:
            self._diagnostics.total_failures += 1
            self._diagnostics.consecutive_failures += 1
            self._diagnostics.last_failure_at = now
            self._diagnostics.last_failure_error = type(error).__name__
            self._diagnostics.last_failure_event_type = str(event_type)
            self._diagnostics.last_failure_entity_type = None if entity_type is None else str(entity_type)
            self._diagnostics.last_failure_entity_id = entity_id

    def snapshot(self, *, mode: LearningSessionRecorderMode | None = None) -> dict[str, Any]:
        with self._lock:
            data = LearningSessionRecorderDiagnostics(**self._diagnostics.__dict__)
        return {
            "mode": mode,
            "degraded": data.consecutive_failures > 0,
            "total_successes": data.total_successes,
            "total_failures": data.total_failures,
            "consecutive_failures": data.consecutive_failures,
            "last_success_at": data.last_success_at,
            "last_failure_at": data.last_failure_at,
            "last_failure_error": data.last_failure_error,
            "last_failure_event_type": data.last_failure_event_type,
            "last_failure_entity_type": data.last_failure_entity_type,
            "last_failure_entity_id": data.last_failure_entity_id,
        }

    def reset(self) -> None:
        with self._lock:
            self._diagnostics = LearningSessionRecorderDiagnostics()


RECORDER_HEALTH = LearningSessionRecorderHealthState()


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
            RECORDER_HEALTH.record_failure(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                error=exc,
            )
            logger.exception(
                "learning_session_recording_failed",
                extra={
                    "user_id": user_id,
                    "language": normalized_language,
                    "event_type": str(event_type),
                    "entity_type": None if entity_type is None else str(entity_type),
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
                "entity_type": None if event.entity_type is None else str(event.entity_type.value),
                "entity_id": entity_id,
                "idempotency_key": idempotency_key,
                "sequence_number": event.sequence_number,
            },
        )
        RECORDER_HEALTH.record_success()
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


def get_learning_session_recorder_health(*, mode: LearningSessionRecorderMode | None = None) -> dict[str, Any]:
    return RECORDER_HEALTH.snapshot(mode=mode or _recorder_mode_from_env())
