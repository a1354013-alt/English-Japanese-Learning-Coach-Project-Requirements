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
    LessonLinkNotFoundError,
)

if TYPE_CHECKING:
    from database import Database

VALID_CHAT_LANGUAGES = {"EN", "JP"}
VALID_CHAT_ROLES = {"system", "user", "assistant"}


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
        if lesson_id:
            self._assert_lesson_exists(lesson_id)

        now = _as_isoformat(local_now())
        conversation_id = str(uuid4())
        conversation_title = title.strip() if title and title.strip() else "New conversation"

        conn = self._database.get_connection()
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
            self._assert_lesson_exists(lesson_id)
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
    ) -> ChatConversationRecord:
        self._update_conversation_fields(
            conversation_id=conversation_id,
            user_id=user_id,
            assignments={"summary": summary, "updated_at": _as_isoformat(local_now())},
        )
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

        conn = self._database.get_connection()
        message_id = str(uuid4())
        created_at = _as_isoformat(local_now())
        metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True) if metadata is not None else None

        conn.execute("BEGIN IMMEDIATE")
        try:
            existing = None
            if idempotency_key:
                existing = conn.execute(
                    """
                    SELECT message_id, conversation_id, role, content, sequence_number,
                           metadata_json, idempotency_key, created_at
                    FROM chat_messages
                    WHERE conversation_id = ? AND idempotency_key = ?
                    """,
                    (conversation_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    existing_message = self._row_to_message(existing)
                    if (
                        existing_message.role != normalized_role
                        or existing_message.content != content
                        or existing_message.metadata != (metadata or None)
                    ):
                        raise IdempotencyConflictError(
                            f"Idempotency key conflict for conversation {conversation_id}"
                        )
                    conn.execute("COMMIT")
                    return existing_message

            conversation_row = conn.execute(
                "SELECT conversation_id FROM chat_conversations WHERE conversation_id = ? AND user_id = ?",
                (conversation_id, user_id),
            ).fetchone()
            if conversation_row is None:
                raise ConversationNotFoundError(f"Conversation not found: {conversation_id}")

            next_sequence = self._allocate_next_sequence(conn=conn, conversation_id=conversation_id)
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
                    idempotency_key,
                    created_at,
                ),
            )
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

        predicates = ["conversation_id = ?"]
        params: List[Any] = [conversation_id]
        if before_sequence is not None:
            predicates.append("sequence_number < ?")
            params.append(before_sequence)
        if after_sequence is not None:
            predicates.append("sequence_number > ?")
            params.append(after_sequence)
        order = "DESC" if descending else "ASC"
        conn = self._database.get_connection()
        rows = conn.execute(
            f"""
            SELECT message_id, conversation_id, role, content, sequence_number,
                   metadata_json, idempotency_key, created_at
            FROM chat_messages
            WHERE {" AND ".join(predicates)}
            ORDER BY sequence_number {order}, created_at {order}, message_id {order}
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        messages = [self._row_to_message(row) for row in rows]
        return ChatMessagePage(messages=messages, limit=limit, descending=descending)

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

    def _assert_lesson_exists(self, lesson_id: str) -> None:
        conn = self._database.get_connection()
        row = conn.execute("SELECT lesson_id FROM lessons WHERE lesson_id = ?", (lesson_id,)).fetchone()
        if row is None:
            raise LessonLinkNotFoundError(f"Lesson not found: {lesson_id}")

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
        if before_sequence is not None and after_sequence is not None and after_sequence >= before_sequence:
            raise InvalidChatPaginationError("after_sequence must be less than before_sequence")

    def _row_to_conversation(self, row: sqlite3.Row) -> ChatConversationRecord:
        return ChatConversationRecord.model_validate(dict(row))

    def _row_to_message(self, row: sqlite3.Row) -> ChatMessageRecord:
        payload = dict(row)
        payload["metadata"] = _decode_metadata(payload.pop("metadata_json", None))
        return ChatMessageRecord.model_validate(payload)
