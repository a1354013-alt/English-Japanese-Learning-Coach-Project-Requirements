"""Persisted-chat repository implementation backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from models import ChatConversationRecord, ChatMessagePage, ChatMessageRecord
from time_utils import local_now

from repositories.errors import (
    ConversationNotFoundError,
    IdempotencyConflictError,
    InvalidChatLanguageError,
    InvalidChatPaginationError,
    InvalidChatRoleError,
    InvalidChatSummaryCheckpointError,
    InvalidIdempotencyKeyError,
    LessonLinkIntegrityError,
    LessonLinkNotFoundError,
)

if TYPE_CHECKING:
    from database import Database

VALID_CHAT_LANGUAGES = {"EN", "JP"}
VALID_CHAT_ROLES = {"system", "user", "assistant"}
MAX_IDEMPOTENCY_KEY_LENGTH = 255


def _as_isoformat(value: datetime) -> str:
    return value.isoformat()


def _decode_metadata(value: Any) -> Optional[Dict[str, Any]]:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _encode_metadata(value: Optional[Dict[str, Any]]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _max_isoformat(*values: Optional[str]) -> Optional[str]:
    present = [value for value in values if value]
    return max(present) if present else None


class ChatRepository:
    """Repository for persisted chat conversations and messages."""

    def __init__(self, database: "Database"):
        self._database = database

    def create_chat_session(
        self,
        *,
        user_id: str,
        language: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        conversation = self.create_conversation(
            user_id=user_id,
            language=language,
            title=title,
            lesson_id=str(metadata["lesson_id"]) if metadata and metadata.get("lesson_id") else None,
            summary=str(metadata["summary"]) if metadata and metadata.get("summary") else None,
        )
        return conversation.conversation_id

    def append_chat_message(
        self,
        *,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> str:
        message = self.append_message(
            conversation_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
        return message.message_id

    def list_chat_messages(self, *, session_id: str, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return [
            message.model_dump()
            for message in self.get_messages_page(
                conversation_id=session_id,
                user_id=user_id,
                limit=limit,
            ).messages
        ]

    def create_conversation(
        self,
        *,
        user_id: str,
        language: str,
        title: Optional[str] = None,
        lesson_id: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> ChatConversationRecord:
        normalized_language = self._normalize_language(language)
        now = _as_isoformat(local_now())
        conversation_id = str(uuid4())
        conversation_title = title.strip() if title and title.strip() else "New conversation"

        conn = self._database.get_connection()
        if lesson_id:
            self._validate_lesson_link(
                conn=conn,
                lesson_id=lesson_id,
                user_id=user_id,
                conversation_language=normalized_language,
            )
        conn.execute(
            """
            INSERT INTO chat_conversations (
                conversation_id, user_id, language, title, lesson_id, summary,
                created_at, updated_at, last_message_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                conversation_id,
                user_id,
                normalized_language,
                conversation_title,
                lesson_id,
                summary,
                now,
                now,
            ),
        )
        return self.get_conversation(conversation_id=conversation_id, user_id=user_id)

    def list_conversations(
        self,
        *,
        user_id: str,
        language: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ChatConversationRecord]:
        normalized_language = self._normalize_language(language)
        self._validate_pagination(limit=limit, offset=offset)
        conn = self._database.get_connection()
        rows = conn.execute(
            """
            SELECT conversation_id, user_id, language, title, lesson_id, summary,
                   summary_through_sequence, summary_updated_at,
                   created_at, updated_at, last_message_at
            FROM chat_conversations
            WHERE user_id = ? AND language = ?
            ORDER BY COALESCE(last_message_at, updated_at) DESC, created_at DESC, conversation_id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, normalized_language, limit, offset),
        ).fetchall()
        return [self._row_to_conversation(row) for row in rows]

    def get_conversation(self, *, conversation_id: str, user_id: str) -> ChatConversationRecord:
        conn = self._database.get_connection()
        row = conn.execute(
            """
            SELECT conversation_id, user_id, language, title, lesson_id, summary,
                   summary_through_sequence, summary_updated_at,
                   created_at, updated_at, last_message_at
            FROM chat_conversations
            WHERE conversation_id = ? AND user_id = ?
            """,
            (conversation_id, user_id),
        ).fetchone()
        if row is None:
            raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")
        return self._row_to_conversation(row)

    def rename_conversation(
        self,
        *,
        conversation_id: str,
        user_id: str,
        title: str,
    ) -> ChatConversationRecord:
        self._update_conversation_fields(
            conversation_id=conversation_id,
            user_id=user_id,
            assignments={"title": title.strip() or "New conversation", "updated_at": _as_isoformat(local_now())},
        )
        return self.get_conversation(conversation_id=conversation_id, user_id=user_id)

    def set_conversation_lesson_link(
        self,
        *,
        conversation_id: str,
        user_id: str,
        lesson_id: Optional[str],
    ) -> ChatConversationRecord:
        if lesson_id:
            conversation = self.get_conversation(conversation_id=conversation_id, user_id=user_id)
            self._validate_lesson_link(
                conn=self._database.get_connection(),
                lesson_id=lesson_id,
                user_id=user_id,
                conversation_language=str(conversation.language),
            )
        self._update_conversation_fields(
            conversation_id=conversation_id,
            user_id=user_id,
            assignments={"lesson_id": lesson_id, "updated_at": _as_isoformat(local_now())},
        )
        return self.get_conversation(conversation_id=conversation_id, user_id=user_id)

    def update_conversation_summary(
        self,
        *,
        conversation_id: str,
        user_id: str,
        summary: Optional[str],
        summary_through_sequence: Optional[int] = None,
    ) -> ChatConversationRecord:
        return self.update_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            summary=summary,
            summary_through_sequence=summary_through_sequence,
            set_summary=True,
        )

    def update_conversation(
        self,
        *,
        conversation_id: str,
        user_id: str,
        title: Optional[str] = None,
        lesson_id: Optional[str] = None,
        set_lesson_id: bool = False,
        summary: Optional[str] = None,
        summary_through_sequence: Optional[int] = None,
        set_summary: bool = False,
    ) -> ChatConversationRecord:
        conn = self._database.get_connection()
        now = _as_isoformat(local_now())
        conn.execute("BEGIN IMMEDIATE")
        try:
            conversation = conn.execute(
                """
                SELECT conversation_id, language, summary, summary_through_sequence
                FROM chat_conversations
                WHERE conversation_id = ? AND user_id = ?
                """,
                (conversation_id, user_id),
            ).fetchone()
            if conversation is None:
                raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")

            assignments: Dict[str, Any] = {"updated_at": now}
            if title is not None:
                assignments["title"] = title.strip() or "New conversation"

            if set_lesson_id:
                if lesson_id:
                    self._validate_lesson_link(
                        conn=conn,
                        lesson_id=lesson_id,
                        user_id=user_id,
                        conversation_language=str(conversation["language"]),
                    )
                assignments["lesson_id"] = lesson_id

            if set_summary:
                if summary is None:
                    assignments["summary"] = None
                    assignments["summary_through_sequence"] = 0
                    assignments["summary_updated_at"] = None
                else:
                    checkpoint = 0 if summary_through_sequence is None else summary_through_sequence
                    self._validate_summary_checkpoint(
                        conn=conn,
                        conversation_id=conversation_id,
                        current_summary=str(conversation["summary"]) if conversation["summary"] is not None else None,
                        current_summary_through_sequence=int(conversation["summary_through_sequence"]),
                        summary_through_sequence=checkpoint,
                    )
                    assignments["summary"] = summary
                    assignments["summary_through_sequence"] = checkpoint
                    assignments["summary_updated_at"] = now

            self._update_conversation_fields(
                conversation_id=conversation_id,
                user_id=user_id,
                assignments=assignments,
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return self.get_conversation(conversation_id=conversation_id, user_id=user_id)

    def delete_conversation(self, *, conversation_id: str, user_id: str) -> None:
        conn = self._database.get_connection()
        cur = conn.execute(
            "DELETE FROM chat_conversations WHERE conversation_id = ? AND user_id = ?",
            (conversation_id, user_id),
        )
        if cur.rowcount == 0:
            raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")

    def clear_conversations_for_demo_user(self, *, user_id: str = "default_user") -> int:
        conn = self._database.get_connection()
        cur = conn.execute("DELETE FROM chat_conversations WHERE user_id = ?", (user_id,))
        return int(cur.rowcount or 0)

    def append_message(
        self,
        *,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> ChatMessageRecord:
        normalized_role = self._normalize_role(role)
        normalized_idempotency_key = self._normalize_idempotency_key(idempotency_key)

        conn = self._database.get_connection()
        message_id = str(uuid4())
        metadata_json = _encode_metadata(metadata)

        conn.execute("BEGIN IMMEDIATE")
        try:
            conversation_row = conn.execute(
                """
                SELECT conversation_id, updated_at, last_message_at
                FROM chat_conversations
                WHERE conversation_id = ? AND user_id = ?
                """,
                (conversation_id, user_id),
            ).fetchone()
            if conversation_row is None:
                raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")

            existing = None
            if normalized_idempotency_key is not None:
                existing = conn.execute(
                    """
                    SELECT message_id, conversation_id, role, content, sequence_number,
                           metadata_json, idempotency_key, created_at
                    FROM chat_messages
                    WHERE conversation_id = ? AND idempotency_key = ?
                    """,
                    (conversation_id, normalized_idempotency_key),
                ).fetchone()
                if existing is not None:
                    if (
                        str(existing["role"]) != normalized_role
                        or str(existing["content"]) != content
                        or existing["metadata_json"] != metadata_json
                    ):
                        raise IdempotencyConflictError(
                            f"Idempotency key conflict for conversation {conversation_id}"
                        )
                    existing_message = self._row_to_message(existing)
                    conn.execute("COMMIT")
                    return existing_message

            created_at = _max_isoformat(
                _as_isoformat(local_now()),
                conversation_row["last_message_at"],
                conversation_row["updated_at"],
            )
            if created_at is None:
                created_at = _as_isoformat(local_now())
            next_sequence = self._allocate_next_sequence(conn=conn, conversation_id=conversation_id)
            try:
                conn.execute(
                    """
                    INSERT INTO chat_messages (
                        message_id, conversation_id, role, content, sequence_number,
                        metadata_json, idempotency_key, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message_id,
                        conversation_id,
                        normalized_role,
                        content,
                        next_sequence,
                        metadata_json,
                        normalized_idempotency_key,
                        created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                if normalized_idempotency_key is None:
                    raise
                existing = conn.execute(
                    """
                    SELECT message_id, conversation_id, role, content, sequence_number,
                           metadata_json, idempotency_key, created_at
                    FROM chat_messages
                    WHERE conversation_id = ? AND idempotency_key = ?
                    """,
                    (conversation_id, normalized_idempotency_key),
                ).fetchone()
                if existing is None:
                    raise IdempotencyConflictError(
                        f"Idempotency key conflict for conversation {conversation_id}"
                    ) from exc
                if (
                    str(existing["role"]) != normalized_role
                    or str(existing["content"]) != content
                    or existing["metadata_json"] != metadata_json
                ):
                    raise IdempotencyConflictError(
                        f"Idempotency key conflict for conversation {conversation_id}"
                    ) from exc
                existing_message = self._row_to_message(existing)
                conn.execute("COMMIT")
                return existing_message
            cur = conn.execute(
                """
                UPDATE chat_conversations
                SET updated_at = ?, last_message_at = ?
                WHERE conversation_id = ? AND user_id = ?
                """,
                (created_at, created_at, conversation_id, user_id),
            )
            if cur.rowcount == 0:
                raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")
            row = conn.execute(
                """
                SELECT message_id, conversation_id, role, content, sequence_number,
                       metadata_json, idempotency_key, created_at
                FROM chat_messages
                WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        if row is None:
            raise ConversationNotFoundError(f"Message insert failed: {conversation_id}")
        return self._row_to_message(row)

    def get_messages_page(
        self,
        *,
        conversation_id: str,
        user_id: str,
        limit: int = 100,
        before_sequence: Optional[int] = None,
        after_sequence: Optional[int] = None,
        descending: bool = False,
    ) -> ChatMessagePage:
        self._validate_message_page(limit=limit, before_sequence=before_sequence, after_sequence=after_sequence)
        self.get_conversation(conversation_id=conversation_id, user_id=user_id)

        conn = self._database.get_connection()
        conn.execute("SAVEPOINT chat_message_page")
        try:
            page = self._read_message_page(
                conn=conn,
                conversation_id=conversation_id,
                limit=limit,
                before_sequence=before_sequence,
                after_sequence=after_sequence,
                descending=descending,
            )
            conn.execute("RELEASE SAVEPOINT chat_message_page")
        except Exception:
            conn.execute("ROLLBACK TO SAVEPOINT chat_message_page")
            conn.execute("RELEASE SAVEPOINT chat_message_page")
            raise
        return page

    def get_recent_messages(
        self,
        *,
        conversation_id: str,
        user_id: str,
        limit: int = 20,
    ) -> List[ChatMessageRecord]:
        page = self.get_messages_page(
            conversation_id=conversation_id,
            user_id=user_id,
            limit=limit,
            descending=True,
        )
        return list(reversed(page.messages))

    def get_message_by_idempotency_key(
        self,
        *,
        conversation_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[ChatMessageRecord]:
        normalized_idempotency_key = self._normalize_idempotency_key(idempotency_key)
        self.get_conversation(conversation_id=conversation_id, user_id=user_id)
        row = self._database.get_connection().execute(
            """
            SELECT message_id, conversation_id, role, content, sequence_number,
                   metadata_json, idempotency_key, created_at
            FROM chat_messages
            WHERE conversation_id = ? AND idempotency_key = ?
            """,
            (conversation_id, normalized_idempotency_key),
        ).fetchone()
        return self._row_to_message(row) if row is not None else None

    def _update_conversation_fields(
        self,
        *,
        conversation_id: str,
        user_id: str,
        assignments: Dict[str, Any],
    ) -> None:
        conn = self._database.get_connection()
        columns = list(assignments.keys())
        params = [assignments[column] for column in columns]
        set_clause = ", ".join(f"{column} = ?" for column in columns)
        params.extend([conversation_id, user_id])
        cur = conn.execute(
            f"UPDATE chat_conversations SET {set_clause} WHERE conversation_id = ? AND user_id = ?",
            params,
        )
        if cur.rowcount == 0:
            raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")

    def _validate_lesson_link(
        self,
        *,
        conn: sqlite3.Connection,
        lesson_id: str,
        user_id: str,
        conversation_language: str,
    ) -> None:
        row = conn.execute(
            "SELECT lesson_id, user_id, language FROM lessons WHERE lesson_id = ?",
            (lesson_id,),
        ).fetchone()
        if row is None:
            raise LessonLinkNotFoundError(f"Lesson not found: {lesson_id}")
        if str(row["user_id"]) != user_id:
            raise LessonLinkNotFoundError(f"Lesson not found: {lesson_id}")
        if str(row["language"]).strip().upper() != conversation_language:
            raise LessonLinkIntegrityError("Lesson language must match the conversation language.")

    def _validate_summary_checkpoint(
        self,
        *,
        conn: sqlite3.Connection,
        conversation_id: str,
        current_summary: Optional[str],
        current_summary_through_sequence: int,
        summary_through_sequence: int,
    ) -> None:
        if summary_through_sequence < 0:
            raise InvalidChatSummaryCheckpointError("summary_through_sequence must be >= 0")
        row = conn.execute(
            """
            SELECT COALESCE(MAX(sequence_number), 0) AS max_sequence
            FROM chat_messages
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        ).fetchone()
        max_sequence = int(row["max_sequence"]) if row is not None else 0
        if summary_through_sequence > max_sequence:
            raise InvalidChatSummaryCheckpointError(
                "summary_through_sequence must not exceed the current maximum message sequence"
            )
        if current_summary is not None and summary_through_sequence < current_summary_through_sequence:
            raise InvalidChatSummaryCheckpointError(
                "summary_through_sequence must not move backward for a persisted summary"
            )

    def _allocate_next_sequence(self, *, conn: sqlite3.Connection, conversation_id: str) -> int:
        row = conn.execute(
            "SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_sequence FROM chat_messages WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return int(row["next_sequence"]) if row is not None else 1

    def _normalize_language(self, language: str) -> str:
        normalized = language.strip().upper()
        if normalized not in VALID_CHAT_LANGUAGES:
            raise InvalidChatLanguageError(f"Unsupported chat language: {language}")
        return normalized

    def _normalize_role(self, role: str) -> str:
        normalized = role.strip().lower()
        if normalized not in VALID_CHAT_ROLES:
            raise InvalidChatRoleError(f"Unsupported chat role: {role}")
        return normalized

    def _normalize_idempotency_key(self, idempotency_key: Optional[str]) -> Optional[str]:
        if idempotency_key is None:
            return None
        normalized = idempotency_key.strip()
        if not normalized:
            raise InvalidIdempotencyKeyError("Idempotency key must not be blank.")
        if len(normalized) > MAX_IDEMPOTENCY_KEY_LENGTH:
            raise InvalidIdempotencyKeyError(
                f"Idempotency key must be at most {MAX_IDEMPOTENCY_KEY_LENGTH} characters."
            )
        return normalized

    def _validate_pagination(self, *, limit: int, offset: int) -> None:
        if limit <= 0 or offset < 0:
            raise InvalidChatPaginationError("limit must be > 0 and offset must be >= 0")

    def _validate_message_page(
        self,
        *,
        limit: int,
        before_sequence: Optional[int],
        after_sequence: Optional[int],
    ) -> None:
        if limit <= 0:
            raise InvalidChatPaginationError("limit must be > 0")
        if before_sequence is not None and before_sequence <= 0:
            raise InvalidChatPaginationError("before_sequence must be > 0")
        if after_sequence is not None and after_sequence <= 0:
            raise InvalidChatPaginationError("after_sequence must be > 0")
        if before_sequence is not None and after_sequence is not None:
            raise InvalidChatPaginationError("before_sequence and after_sequence cannot be used together")

    def _read_message_page(
        self,
        *,
        conn: sqlite3.Connection,
        conversation_id: str,
        limit: int,
        before_sequence: Optional[int],
        after_sequence: Optional[int],
        descending: bool,
    ) -> ChatMessagePage:
        fetch_limit = limit + 1
        if before_sequence is not None:
            rows = conn.execute(
                """
                SELECT message_id, conversation_id, role, content, sequence_number,
                       metadata_json, idempotency_key, created_at
                FROM chat_messages
                WHERE conversation_id = ? AND sequence_number < ?
                ORDER BY sequence_number DESC, created_at DESC, message_id DESC
                LIMIT ?
                """,
                (conversation_id, before_sequence, fetch_limit),
            ).fetchall()
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]
            rows = list(reversed(rows))
        elif after_sequence is not None:
            rows = conn.execute(
                """
                SELECT message_id, conversation_id, role, content, sequence_number,
                       metadata_json, idempotency_key, created_at
                FROM chat_messages
                WHERE conversation_id = ? AND sequence_number > ?
                ORDER BY sequence_number ASC, created_at ASC, message_id ASC
                LIMIT ?
                """,
                (conversation_id, after_sequence, fetch_limit),
            ).fetchall()
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]
        else:
            rows = conn.execute(
                """
                SELECT message_id, conversation_id, role, content, sequence_number,
                       metadata_json, idempotency_key, created_at
                FROM chat_messages
                WHERE conversation_id = ?
                ORDER BY sequence_number DESC, created_at DESC, message_id DESC
                LIMIT ?
                """,
                (conversation_id, fetch_limit),
            ).fetchall()
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]
            rows = list(reversed(rows))

        messages = [self._row_to_message(row) for row in rows]
        if descending:
            messages = list(reversed(messages))

        next_before_sequence: Optional[int] = None
        next_after_sequence: Optional[int] = None
        if messages:
            first_sequence = messages[0].sequence_number if not descending else messages[-1].sequence_number
            last_sequence = messages[-1].sequence_number if not descending else messages[0].sequence_number
            older_exists = conn.execute(
                """
                SELECT 1
                FROM chat_messages
                WHERE conversation_id = ? AND sequence_number < ?
                LIMIT 1
                """,
                (conversation_id, first_sequence),
            ).fetchone()
            newer_exists = conn.execute(
                """
                SELECT 1
                FROM chat_messages
                WHERE conversation_id = ? AND sequence_number > ?
                LIMIT 1
                """,
                (conversation_id, last_sequence),
            ).fetchone()
            if older_exists is not None:
                next_before_sequence = first_sequence
            if newer_exists is not None:
                next_after_sequence = last_sequence

        return ChatMessagePage(
            messages=messages,
            limit=limit,
            has_more=has_more,
            next_before_sequence=next_before_sequence,
            next_after_sequence=next_after_sequence,
            descending=descending,
        )

    def _row_to_conversation(self, row: sqlite3.Row) -> ChatConversationRecord:
        return ChatConversationRecord.model_validate(dict(row))

    def _row_to_message(self, row: sqlite3.Row) -> ChatMessageRecord:
        payload = dict(row)
        payload["metadata"] = _decode_metadata(payload.pop("metadata_json", None))
        return ChatMessageRecord.model_validate(payload)
