"""Learning-session repository implementation backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from models import (
    MAX_LEARNING_SESSION_METADATA_BYTES,
    MAX_LEARNING_SESSION_PAGE_SIZE,
    MAX_LEARNING_SESSION_PLANNED_MINUTES,
    LearningSessionEntityType,
    LearningSessionEventHistoryPage,
    LearningSessionEventMetadata,
    LearningSessionEventRecord,
    LearningSessionEventType,
    LearningSessionEventTypeCounts,
    LearningSessionHistoryPage,
    LearningSessionRecord,
    LearningSessionStatus,
    LearningSessionSummary,
    validate_learning_session_idempotency_key,
)
from time_utils import local_now

from repositories.errors import (
    InvalidLearningSessionEventError,
    InvalidLearningSessionPaginationError,
    InvalidLearningSessionTransitionError,
    LearningSessionAlreadyActiveError,
    LearningSessionIdempotencyConflictError,
    LearningSessionNotActiveError,
    LearningSessionNotFoundError,
)

if TYPE_CHECKING:
    from database import Database


def _as_isoformat(value: datetime) -> str:
    return value.isoformat()


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Expected datetime string, received {type(value)!r}")
    return datetime.fromisoformat(value)


def _encode_metadata(value: Optional[LearningSessionEventMetadata]) -> Optional[str]:
    if value is None:
        return None
    payload = value.model_dump(mode="json", exclude_none=True)
    if not payload:
        return None
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_LEARNING_SESSION_METADATA_BYTES:
        raise InvalidLearningSessionEventError(
            f"metadata must be at most {MAX_LEARNING_SESSION_METADATA_BYTES} UTF-8 bytes when serialized"
        )
    return encoded


def _decode_metadata(value: Any) -> Optional[LearningSessionEventMetadata]:
    if value in (None, ""):
        return None
    if isinstance(value, LearningSessionEventMetadata):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:  # pragma: no cover - database constraint should prevent this
            raise InvalidLearningSessionEventError("Stored metadata is not valid JSON") from exc
    elif isinstance(value, dict):
        parsed = value
    else:
        raise InvalidLearningSessionEventError("Stored metadata has an unsupported shape")
    return LearningSessionEventMetadata.model_validate(parsed)


class LearningSessionRepository:
    """Repository for structured learning sessions and event logs."""

    def __init__(self, database: "Database"):
        self._database = database

    def start_session(
        self,
        *,
        user_id: str,
        language: str,
        planned_minutes: Optional[int] = None,
    ) -> LearningSessionRecord:
        normalized_language = self._normalize_language(language)
        self._validate_planned_minutes(planned_minutes)
        now = _as_isoformat(local_now())
        session_id = str(uuid4())
        conn = self._database.get_connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            self._ensure_no_active_session(conn=conn, user_id=user_id, language=normalized_language)
            conn.execute(
                """
                INSERT INTO learning_sessions (
                    session_id,
                    user_id,
                    language,
                    status,
                    planned_minutes,
                    started_at,
                    ended_at,
                    duration_seconds,
                    completion_idempotency_key,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
                """,
                (
                    session_id,
                    user_id,
                    normalized_language,
                    LearningSessionStatus.active.value,
                    planned_minutes,
                    now,
                    now,
                    now,
                ),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return self.get_session(session_id=session_id, user_id=user_id)

    def get_session(self, *, session_id: str, user_id: str) -> LearningSessionRecord:
        conn = self._database.get_connection()
        row = conn.execute(
            """
            SELECT session_id, language, status, planned_minutes, started_at, ended_at,
                   duration_seconds, created_at, updated_at
            FROM learning_sessions
            WHERE session_id = ? AND user_id = ?
            """,
            (session_id, user_id),
        ).fetchone()
        if row is None:
            raise LearningSessionNotFoundError(f"Learning session not found: {session_id}")
        return self._row_to_session(row)

    def find_active_session(self, *, user_id: str, language: str) -> Optional[LearningSessionRecord]:
        normalized_language = self._normalize_language(language)
        conn = self._database.get_connection()
        row = conn.execute(
            """
            SELECT session_id, language, status, planned_minutes, started_at, ended_at,
                   duration_seconds, created_at, updated_at
            FROM learning_sessions
            WHERE user_id = ? AND language = ? AND status = ?
            """,
            (user_id, normalized_language, LearningSessionStatus.active.value),
        ).fetchone()
        return None if row is None else self._row_to_session(row)

    def list_session_history(
        self,
        *,
        user_id: str,
        language: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> LearningSessionHistoryPage:
        self._validate_limit(limit)
        cursor_started_at, cursor_session_id = self._decode_session_cursor(cursor)
        args: list[Any] = [user_id]
        where = ["user_id = ?"]
        if language is not None:
            where.append("language = ?")
            args.append(self._normalize_language(language))
        if cursor_started_at is not None and cursor_session_id is not None:
            where.append("(started_at < ? OR (started_at = ? AND session_id < ?))")
            args.extend([cursor_started_at, cursor_started_at, cursor_session_id])
        args.append(limit + 1)
        conn = self._database.get_connection()
        rows = conn.execute(
            f"""
            SELECT session_id, language, status, planned_minutes, started_at, ended_at,
                   duration_seconds, created_at, updated_at
            FROM learning_sessions
            WHERE {' AND '.join(where)}
            ORDER BY started_at DESC, session_id DESC
            LIMIT ?
            """,
            tuple(args),
        ).fetchall()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        sessions = [self._row_to_session(row) for row in page_rows]
        next_cursor = None
        if has_more and sessions:
            tail = sessions[-1]
            next_cursor = self._encode_session_cursor(tail.started_at, tail.session_id)
        return LearningSessionHistoryPage(
            sessions=sessions,
            limit=limit,
            has_more=has_more,
            next_cursor=next_cursor,
        )

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
    ) -> LearningSessionEventRecord:
        normalized_event_type = self._normalize_event_type(event_type)
        normalized_entity_type = self._normalize_entity_type(entity_type)
        normalized_entity_id = self._normalize_entity_id(entity_id)
        if (normalized_entity_type is None) != (normalized_entity_id is None):
            raise InvalidLearningSessionEventError("entity_type and entity_id must be provided together")
        normalized_key = None if idempotency_key is None else validate_learning_session_idempotency_key(idempotency_key)
        metadata_json = _encode_metadata(metadata)
        conn = self._database.get_connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            session_row = self._get_owned_session_row(conn=conn, session_id=session_id, user_id=user_id)
            if str(session_row["status"]) != LearningSessionStatus.active.value:
                raise LearningSessionNotActiveError("Learning session is not active")
            if normalized_key is not None:
                existing = conn.execute(
                    """
                    SELECT event_id, session_id, event_type, entity_type, entity_id, sequence_number,
                           metadata_json, occurred_at, created_at
                    FROM learning_session_events
                    WHERE session_id = ? AND idempotency_key = ?
                    """,
                    (session_id, normalized_key),
                ).fetchone()
                if existing is not None:
                    self._ensure_event_idempotency_match(
                        row=existing,
                        event_type=normalized_event_type,
                        entity_type=normalized_entity_type,
                        entity_id=normalized_entity_id,
                        metadata_json=metadata_json,
                    )
                    conn.execute("COMMIT")
                    return self._row_to_event(existing)

            next_sequence = int(
                conn.execute(
                    "SELECT COALESCE(MAX(sequence_number), 0) AS max_sequence FROM learning_session_events WHERE session_id = ?",
                    (session_id,),
                ).fetchone()["max_sequence"]
            ) + 1
            now = _as_isoformat(local_now())
            event_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO learning_session_events (
                    event_id,
                    session_id,
                    event_type,
                    entity_type,
                    entity_id,
                    sequence_number,
                    idempotency_key,
                    metadata_json,
                    occurred_at,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    session_id,
                    normalized_event_type.value,
                    None if normalized_entity_type is None else normalized_entity_type.value,
                    normalized_entity_id,
                    next_sequence,
                    normalized_key,
                    metadata_json,
                    now,
                    now,
                ),
            )
            conn.execute(
                "UPDATE learning_sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
            row = conn.execute(
                """
                SELECT event_id, session_id, event_type, entity_type, entity_id, sequence_number,
                       metadata_json, occurred_at, created_at
                FROM learning_session_events
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        assert row is not None
        return self._row_to_event(row)

    def list_events(
        self,
        *,
        session_id: str,
        user_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> LearningSessionEventHistoryPage:
        self._validate_limit(limit)
        after_sequence = self._decode_event_cursor(cursor)
        self._get_owned_session_row(conn=self._database.get_connection(), session_id=session_id, user_id=user_id)
        conn = self._database.get_connection()
        rows = conn.execute(
            """
            SELECT event_id, session_id, event_type, entity_type, entity_id, sequence_number,
                   metadata_json, occurred_at, created_at
            FROM learning_session_events
            WHERE session_id = ? AND sequence_number > ?
            ORDER BY sequence_number ASC
            LIMIT ?
            """,
            (session_id, after_sequence, limit + 1),
        ).fetchall()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        events = [self._row_to_event(row) for row in page_rows]
        next_cursor = str(events[-1].sequence_number) if has_more and events else None
        return LearningSessionEventHistoryPage(
            events=events,
            limit=limit,
            has_more=has_more,
            next_cursor=next_cursor,
        )

    def complete_session(
        self,
        *,
        session_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> LearningSessionRecord:
        normalized_key = validate_learning_session_idempotency_key(idempotency_key)
        conn = self._database.get_connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._get_owned_session_row(conn=conn, session_id=session_id, user_id=user_id)
            status = LearningSessionStatus(str(row["status"]))
            existing_key = row["completion_idempotency_key"]
            if status is LearningSessionStatus.completed:
                if existing_key == normalized_key:
                    conn.execute("COMMIT")
                    return self._row_to_session(row)
                raise LearningSessionIdempotencyConflictError(
                    "Learning session was already completed with a different idempotency key"
                )
            if status is LearningSessionStatus.abandoned:
                raise InvalidLearningSessionTransitionError("Cannot complete an abandoned learning session")
            now_dt = local_now()
            ended_at = _as_isoformat(now_dt)
            started_at = _parse_datetime(row["started_at"])
            duration_seconds = max(0, int((now_dt - started_at).total_seconds()))
            conn.execute(
                """
                UPDATE learning_sessions
                SET status = ?,
                    ended_at = ?,
                    duration_seconds = ?,
                    completion_idempotency_key = ?,
                    updated_at = ?
                WHERE session_id = ?
                """,
                (
                    LearningSessionStatus.completed.value,
                    ended_at,
                    duration_seconds,
                    normalized_key,
                    ended_at,
                    session_id,
                ),
            )
            updated = conn.execute(
                """
                SELECT session_id, language, status, planned_minutes, started_at, ended_at,
                       duration_seconds, created_at, updated_at
                FROM learning_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        assert updated is not None
        return self._row_to_session(updated)

    def abandon_session(
        self,
        *,
        session_id: str,
        user_id: str,
        idempotency_key: Optional[str] = None,
    ) -> LearningSessionRecord:
        if idempotency_key is not None:
            validate_learning_session_idempotency_key(idempotency_key)
        conn = self._database.get_connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._get_owned_session_row(conn=conn, session_id=session_id, user_id=user_id)
            status = LearningSessionStatus(str(row["status"]))
            if status is LearningSessionStatus.abandoned:
                conn.execute("COMMIT")
                return self._row_to_session(row)
            if status is LearningSessionStatus.completed:
                raise InvalidLearningSessionTransitionError("Cannot abandon a completed learning session")
            now_dt = local_now()
            ended_at = _as_isoformat(now_dt)
            started_at = _parse_datetime(row["started_at"])
            duration_seconds = max(0, int((now_dt - started_at).total_seconds()))
            conn.execute(
                """
                UPDATE learning_sessions
                SET status = ?,
                    ended_at = ?,
                    duration_seconds = ?,
                    updated_at = ?
                WHERE session_id = ?
                """,
                (
                    LearningSessionStatus.abandoned.value,
                    ended_at,
                    duration_seconds,
                    ended_at,
                    session_id,
                ),
            )
            updated = conn.execute(
                """
                SELECT session_id, language, status, planned_minutes, started_at, ended_at,
                       duration_seconds, created_at, updated_at
                FROM learning_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        assert updated is not None
        return self._row_to_session(updated)

    def produce_summary(self, *, session_id: str, user_id: str) -> LearningSessionSummary:
        session = self.get_session(session_id=session_id, user_id=user_id)
        conn = self._database.get_connection()
        rows = conn.execute(
            """
            SELECT event_type, metadata_json, occurred_at
            FROM learning_session_events
            WHERE session_id = ?
            ORDER BY sequence_number ASC
            """,
            (session_id,),
        ).fetchall()
        counts = LearningSessionEventTypeCounts()
        first_event_at: Optional[datetime] = None
        last_event_at: Optional[datetime] = None
        correct_values: list[bool] = []
        for row in rows:
            event_type = LearningSessionEventType(str(row["event_type"]))
            setattr(counts, event_type.value, getattr(counts, event_type.value) + 1)
            occurred_at = _parse_datetime(row["occurred_at"])
            first_event_at = occurred_at if first_event_at is None else min(first_event_at, occurred_at)
            last_event_at = occurred_at if last_event_at is None else max(last_event_at, occurred_at)
            metadata = _decode_metadata(row["metadata_json"])
            if metadata is not None and metadata.correct is not None:
                correct_values.append(metadata.correct)
        planned_goal_reached = None
        if session.planned_minutes is not None and session.duration_seconds is not None:
            planned_goal_reached = session.duration_seconds >= session.planned_minutes * 60
        return LearningSessionSummary(
            session_id=session.session_id,
            language=session.language,
            status=session.status,
            started_at=session.started_at,
            ended_at=session.ended_at,
            duration_seconds=session.duration_seconds,
            planned_minutes=session.planned_minutes,
            total_event_count=len(rows),
            counts_by_event_type=counts,
            lesson_completion_count=counts.lesson_completed,
            review_answer_count=counts.review_answered,
            srs_review_count=counts.srs_reviewed,
            chat_turn_count=counts.chat_turn_completed,
            feynman_completion_count=counts.feynman_completed,
            micro_lesson_completion_count=counts.micro_lesson_completed,
            first_event_at=first_event_at,
            last_event_at=last_event_at,
            planned_duration_goal_reached=planned_goal_reached,
            correct_event_count=sum(1 for value in correct_values if value) if correct_values else None,
        )

    def delete_session(self, *, session_id: str, user_id: str) -> None:
        conn = self._database.get_connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._get_owned_session_row(conn=conn, session_id=session_id, user_id=user_id)
            if str(row["status"]) == LearningSessionStatus.active.value:
                raise InvalidLearningSessionTransitionError("Active learning sessions cannot be deleted")
            conn.execute("DELETE FROM learning_sessions WHERE session_id = ? AND user_id = ?", (session_id, user_id))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def clear_local_demo_user_session_data(self, *, user_id: str) -> int:
        conn = self._database.get_connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            deleted = int(
                conn.execute("SELECT COUNT(1) AS count FROM learning_sessions WHERE user_id = ?", (user_id,)).fetchone()[
                    "count"
                ]
            )
            conn.execute("DELETE FROM learning_sessions WHERE user_id = ?", (user_id,))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return deleted

    def _get_owned_session_row(
        self,
        *,
        conn: sqlite3.Connection,
        session_id: str,
        user_id: str,
    ) -> sqlite3.Row:
        row = conn.execute(
            """
            SELECT session_id, user_id, language, status, planned_minutes, started_at, ended_at,
                   duration_seconds, completion_idempotency_key, created_at, updated_at
            FROM learning_sessions
            WHERE session_id = ? AND user_id = ?
            """,
            (session_id, user_id),
        ).fetchone()
        if row is None:
            raise LearningSessionNotFoundError(f"Learning session not found: {session_id}")
        return row

    def _ensure_no_active_session(self, *, conn: sqlite3.Connection, user_id: str, language: str) -> None:
        active = conn.execute(
            """
            SELECT session_id
            FROM learning_sessions
            WHERE user_id = ? AND language = ? AND status = ?
            """,
            (user_id, language, LearningSessionStatus.active.value),
        ).fetchone()
        if active is not None:
            raise LearningSessionAlreadyActiveError("An active learning session already exists")

    def _normalize_language(self, language: str) -> str:
        normalized = language.strip().upper()
        if normalized not in {"EN", "JP"}:
            raise InvalidLearningSessionEventError(f"Unsupported learning-session language: {language}")
        return normalized

    def _normalize_event_type(self, event_type: LearningSessionEventType | str) -> LearningSessionEventType:
        try:
            return event_type if isinstance(event_type, LearningSessionEventType) else LearningSessionEventType(str(event_type))
        except ValueError as exc:
            raise InvalidLearningSessionEventError(f"Unsupported learning-session event type: {event_type}") from exc

    def _normalize_entity_type(
        self,
        entity_type: LearningSessionEntityType | str | None,
    ) -> Optional[LearningSessionEntityType]:
        if entity_type is None:
            return None
        try:
            return entity_type if isinstance(entity_type, LearningSessionEntityType) else LearningSessionEntityType(str(entity_type))
        except ValueError as exc:
            raise InvalidLearningSessionEventError(f"Unsupported learning-session entity type: {entity_type}") from exc

    def _normalize_entity_id(self, entity_id: Optional[str]) -> Optional[str]:
        if entity_id is None:
            return None
        normalized = entity_id.strip()
        if not normalized:
            raise InvalidLearningSessionEventError("entity_id must not be blank")
        return normalized

    def _validate_planned_minutes(self, planned_minutes: Optional[int]) -> None:
        if planned_minutes is None:
            return
        if planned_minutes <= 0 or planned_minutes > MAX_LEARNING_SESSION_PLANNED_MINUTES:
            raise InvalidLearningSessionEventError(
                f"planned_minutes must be between 1 and {MAX_LEARNING_SESSION_PLANNED_MINUTES}"
            )

    def _validate_limit(self, limit: int) -> None:
        if limit <= 0 or limit > MAX_LEARNING_SESSION_PAGE_SIZE:
            raise InvalidLearningSessionPaginationError(
                f"limit must be between 1 and {MAX_LEARNING_SESSION_PAGE_SIZE}"
            )

    def _decode_session_cursor(self, cursor: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if cursor is None:
            return None, None
        if "|" not in cursor:
            raise InvalidLearningSessionPaginationError("cursor must use the expected session history format")
        started_at, session_id = cursor.split("|", 1)
        if not started_at or not session_id:
            raise InvalidLearningSessionPaginationError("cursor must include both started_at and session_id")
        try:
            _parse_datetime(started_at)
        except ValueError as exc:
            raise InvalidLearningSessionPaginationError("cursor contains an invalid started_at timestamp") from exc
        return started_at, session_id

    def _encode_session_cursor(self, started_at: datetime, session_id: str) -> str:
        return f"{started_at.isoformat()}|{session_id}"

    def _decode_event_cursor(self, cursor: Optional[str]) -> int:
        if cursor is None:
            return 0
        if not cursor.isdigit():
            raise InvalidLearningSessionPaginationError("cursor must be a positive event sequence number")
        value = int(cursor)
        if value < 0:
            raise InvalidLearningSessionPaginationError("cursor must not be negative")
        return value

    def _ensure_event_idempotency_match(
        self,
        *,
        row: sqlite3.Row,
        event_type: LearningSessionEventType,
        entity_type: Optional[LearningSessionEntityType],
        entity_id: Optional[str],
        metadata_json: Optional[str],
    ) -> None:
        if (
            str(row["event_type"]) != event_type.value
            or row["entity_type"] != (None if entity_type is None else entity_type.value)
            or row["entity_id"] != entity_id
            or row["metadata_json"] != metadata_json
        ):
            raise LearningSessionIdempotencyConflictError(
                "Idempotency key was already used for a different learning-session event"
            )

    def _row_to_session(self, row: sqlite3.Row) -> LearningSessionRecord:
        return LearningSessionRecord.model_validate(
            {
                "session_id": row["session_id"],
                "language": row["language"],
                "status": row["status"],
                "planned_minutes": row["planned_minutes"],
                "started_at": _parse_datetime(row["started_at"]),
                "ended_at": None if row["ended_at"] is None else _parse_datetime(row["ended_at"]),
                "duration_seconds": row["duration_seconds"],
                "created_at": _parse_datetime(row["created_at"]),
                "updated_at": _parse_datetime(row["updated_at"]),
            }
        )

    def _row_to_event(self, row: sqlite3.Row) -> LearningSessionEventRecord:
        return LearningSessionEventRecord.model_validate(
            {
                "event_id": row["event_id"],
                "session_id": row["session_id"],
                "event_type": row["event_type"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "sequence_number": row["sequence_number"],
                "metadata": _decode_metadata(row["metadata_json"]),
                "occurred_at": _parse_datetime(row["occurred_at"]),
                "created_at": _parse_datetime(row["created_at"]),
            }
        )
