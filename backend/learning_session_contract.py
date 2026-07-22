"""Shared validation helpers for the Phase 1 learning-session contract."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

STABLE_RELEASE_VERSION = "1.5.0"
_DEV_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+-dev\.\d+$")
_RC_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+-rc\d+$")
_FINAL_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class LearningSessionContractViolation(ValueError):
    """Raised when a learning-session payload breaks the Phase 1 contract."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class LearningSessionEventRule:
    event_type: str
    entity_type: str | None
    entity_id_required: bool
    requires_correct: bool = False
    requires_note: bool = False
    allows_note: bool = False


EVENT_RULES: dict[str, LearningSessionEventRule] = {
    "lesson_started": LearningSessionEventRule(
        event_type="lesson_started",
        entity_type="lesson",
        entity_id_required=True,
    ),
    "lesson_completed": LearningSessionEventRule(
        event_type="lesson_completed",
        entity_type="lesson",
        entity_id_required=True,
    ),
    "review_answered": LearningSessionEventRule(
        event_type="review_answered",
        entity_type="review",
        entity_id_required=True,
        requires_correct=True,
        allows_note=True,
    ),
    "srs_reviewed": LearningSessionEventRule(
        event_type="srs_reviewed",
        entity_type="srs_item",
        entity_id_required=True,
    ),
    "chat_turn_completed": LearningSessionEventRule(
        event_type="chat_turn_completed",
        entity_type="conversation",
        entity_id_required=True,
    ),
    "feynman_completed": LearningSessionEventRule(
        event_type="feynman_completed",
        entity_type="feynman_response",
        entity_id_required=True,
    ),
    "micro_lesson_completed": LearningSessionEventRule(
        event_type="micro_lesson_completed",
        entity_type="micro_lesson",
        entity_id_required=True,
    ),
    "session_note": LearningSessionEventRule(
        event_type="session_note",
        entity_type=None,
        entity_id_required=False,
        requires_note=True,
        allows_note=True,
    ),
}


def classify_version(version: str) -> str:
    if _DEV_VERSION_RE.fullmatch(version):
        return "development"
    if _RC_VERSION_RE.fullmatch(version):
        return "release_candidate"
    if _FINAL_VERSION_RE.fullmatch(version):
        return "final"
    raise ValueError(f"Unsupported project version format: {version}")


def validate_event_contract(
    *,
    event_type: str,
    entity_type: str | None,
    entity_id: str | None,
    metadata: Mapping[str, Any] | None,
) -> None:
    rule = EVENT_RULES.get(event_type)
    if rule is None:
        raise LearningSessionContractViolation(
            f"Unsupported learning-session event type: {event_type}",
            code="invalid_learning_session_event_type",
        )

    if rule.entity_type is None:
        if entity_type is not None or entity_id is not None:
            raise LearningSessionContractViolation(
                f"{event_type} does not allow entity_type or entity_id",
                code="invalid_learning_session_semantics",
            )
    else:
        if entity_type != rule.entity_type:
            raise LearningSessionContractViolation(
                f"{event_type} requires entity_type {rule.entity_type}",
                code="invalid_learning_session_semantics",
            )
        if rule.entity_id_required and entity_id is None:
            raise LearningSessionContractViolation(
                f"{event_type} requires entity_id",
                code="invalid_learning_session_semantics",
            )

    payload = dict(metadata or {})
    note = payload.get("note")
    has_note = note is not None
    has_correct = payload.get("correct") is not None

    if rule.requires_note and not has_note:
        raise LearningSessionContractViolation(
            f"{event_type} requires metadata.note",
            code="invalid_learning_session_semantics",
        )
    if rule.requires_correct and not has_correct:
        raise LearningSessionContractViolation(
            f"{event_type} requires metadata.correct",
            code="invalid_learning_session_semantics",
        )
    if has_note and not rule.allows_note:
        raise LearningSessionContractViolation(
            f"{event_type} does not allow metadata.note",
            code="invalid_learning_session_semantics",
        )
    if has_correct and not rule.requires_correct:
        raise LearningSessionContractViolation(
            f"{event_type} does not allow metadata.correct",
            code="invalid_learning_session_semantics",
        )
