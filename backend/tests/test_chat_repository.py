from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from database import Database
from repositories.errors import (
    ConversationNotFoundError,
    IdempotencyConflictError,
    InvalidChatLanguageError,
    InvalidChatPaginationError,
    InvalidChatRoleError,
    LessonLinkNotFoundError,
)


def _make_db(tmp_path) -> Database:
    return Database(str(tmp_path / "chat.db"))


def _insert_lesson(db: Database, lesson_id: str = "lesson-1") -> None:
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO lessons (
                lesson_id, user_id, language, level, topic, generated_at,
                estimated_duration_minutes, key_points, file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson_id,
                "default_user",
                "EN",
                "A1",
                "Greetings",
                "2026-07-18T09:00:00+08:00",
                15,
                "[]",
                "lesson.json",
            ),
        )


def _create_conversation(db: Database, language: str = "EN"):
    return db.chat_repository.create_conversation(
        user_id="default_user",
        language=language,
        title=f"{language} chat",
    )


def test_create_and_list_conversations_isolate_by_language(tmp_path):
    db = _make_db(tmp_path)

    en_conversation = _create_conversation(db, "EN")
    jp_conversation = _create_conversation(db, "JP")

    en_list = db.chat_repository.list_conversations(user_id="default_user", language="EN")
    jp_list = db.chat_repository.list_conversations(user_id="default_user", language="JP")

    assert [conversation.conversation_id for conversation in en_list] == [en_conversation.conversation_id]
    assert [conversation.conversation_id for conversation in jp_list] == [jp_conversation.conversation_id]


def test_database_compatibility_methods_delegate_to_chat_repository(tmp_path):
    db = _make_db(tmp_path)

    session_id = db.create_chat_session(user_id="default_user", language="EN", title="Compat")
    message_id = db.append_chat_message(
        session_id=session_id,
        user_id="default_user",
        role="user",
        content="hello",
        metadata={"source": "test"},
    )
    messages = db.list_chat_messages(session_id=session_id, user_id="default_user", limit=10)

    assert session_id
    assert message_id
    assert len(messages) == 1
    assert messages[0]["content"] == "hello"


def test_rename_link_unlink_and_summary_update(tmp_path):
    db = _make_db(tmp_path)
    _insert_lesson(db)
    conversation = _create_conversation(db)

    renamed = db.chat_repository.rename_conversation(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        title="Renamed chat",
    )
    linked = db.chat_repository.set_conversation_lesson_link(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        lesson_id="lesson-1",
    )
    summarized = db.chat_repository.update_conversation_summary(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        summary="Conversation summary",
    )
    unlinked = db.chat_repository.set_conversation_lesson_link(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        lesson_id=None,
    )

    assert renamed.title == "Renamed chat"
    assert linked.lesson_id == "lesson-1"
    assert summarized.summary == "Conversation summary"
    assert unlinked.lesson_id is None


def test_invalid_lesson_link_raises_explicit_error(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)

    with pytest.raises(LessonLinkNotFoundError):
        db.chat_repository.set_conversation_lesson_link(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            lesson_id="missing-lesson",
        )


def test_message_ordering_pagination_and_recent_window(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)

    for index in range(1, 6):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user" if index % 2 else "assistant",
            content=f"message-{index}",
        )

    page_forward = db.chat_repository.get_messages_page(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        limit=2,
        after_sequence=2,
    )
    page_backward = db.chat_repository.get_messages_page(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        limit=2,
        before_sequence=5,
        descending=True,
    )
    recent = db.chat_repository.get_recent_messages(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        limit=3,
    )

    assert [message.sequence_number for message in page_forward.messages] == [3, 4]
    assert [message.content for message in page_backward.messages] == ["message-4", "message-3"]
    assert [message.sequence_number for message in recent] == [3, 4, 5]


def test_delete_conversation_cascades_messages(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="to be deleted",
    )

    db.chat_repository.delete_conversation(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
    )

    with pytest.raises(ConversationNotFoundError):
        db.chat_repository.get_conversation(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
        )
    with db.get_connection() as conn:
        remaining = conn.execute(
            "SELECT COUNT(1) AS count FROM chat_messages WHERE conversation_id = ?",
            (conversation.conversation_id,),
        ).fetchone()
    assert int(remaining["count"]) == 0


def test_clear_all_behavior_is_scoped_to_demo_user(tmp_path):
    db = _make_db(tmp_path)
    _create_conversation(db, "EN")
    db.chat_repository.create_conversation(user_id="other_user", language="EN", title="Other")

    deleted = db.chat_repository.clear_conversations_for_demo_user(user_id="default_user")

    assert deleted == 1
    assert db.chat_repository.list_conversations(user_id="default_user", language="EN") == []
    assert len(db.chat_repository.list_conversations(user_id="other_user", language="EN")) == 1


def test_invalid_language_role_and_pagination_raise_explicit_errors(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)

    with pytest.raises(InvalidChatLanguageError):
        db.chat_repository.create_conversation(user_id="default_user", language="FR", title="Bad")
    with pytest.raises(InvalidChatRoleError):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="tool",
            content="bad role",
        )
    with pytest.raises(InvalidChatPaginationError):
        db.chat_repository.list_conversations(user_id="default_user", language="EN", limit=0)
    with pytest.raises(InvalidChatPaginationError):
        db.chat_repository.get_messages_page(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            limit=1,
            before_sequence=2,
            after_sequence=2,
        )


def test_idempotent_message_retry_returns_original_message(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)

    first = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="same request",
        metadata={"turn": 1},
        idempotency_key="retry-1",
    )
    second = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="same request",
        metadata={"turn": 1},
        idempotency_key="retry-1",
    )

    with db.get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(1) AS count FROM chat_messages WHERE conversation_id = ?",
            (conversation.conversation_id,),
        ).fetchone()

    assert first.message_id == second.message_id
    assert first.sequence_number == second.sequence_number
    assert int(count["count"]) == 1


def test_idempotency_key_conflict_raises_explicit_error(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="original",
        metadata={"turn": 1},
        idempotency_key="retry-1",
    )

    with pytest.raises(IdempotencyConflictError):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="assistant",
            content="changed",
            metadata={"turn": 2},
            idempotency_key="retry-1",
        )


def test_transaction_rollback_on_message_insert_failure(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    before = db.chat_repository.get_conversation(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
    )

    with db.get_connection() as conn:
        conn.execute(
            """
            CREATE TRIGGER chat_messages_abort_insert
            AFTER INSERT ON chat_messages
            BEGIN
                SELECT RAISE(ABORT, 'forced failure');
            END;
            """
        )

    with pytest.raises(Exception, match="forced failure"):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user",
            content="should rollback",
        )

    with db.get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(1) AS count FROM chat_messages WHERE conversation_id = ?",
            (conversation.conversation_id,),
        ).fetchone()
        conn.execute("DROP TRIGGER chat_messages_abort_insert")
    after = db.chat_repository.get_conversation(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
    )

    assert int(count["count"]) == 0
    assert after.updated_at == before.updated_at
    assert after.last_message_at is None


def test_concurrent_appends_allocate_unique_contiguous_sequences(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    count = 10
    barrier = Barrier(count)

    def _append(index: int):
        barrier.wait()
        return db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user",
            content=f"content-{index}",
            metadata={"index": index},
            idempotency_key=f"key-{index}",
        )

    with ThreadPoolExecutor(max_workers=count) as executor:
        results = list(executor.map(_append, range(count)))

    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT message_id, sequence_number, content
            FROM chat_messages
            WHERE conversation_id = ?
            ORDER BY sequence_number ASC
            """,
            (conversation.conversation_id,),
        ).fetchall()
    updated = db.chat_repository.get_conversation(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
    )

    assert len(results) == count
    assert len(rows) == count
    assert [int(row["sequence_number"]) for row in rows] == list(range(1, count + 1))
    assert len({row["message_id"] for row in rows}) == count
    assert {result.message_id for result in results} == {row["message_id"] for row in rows}
    assert {row["content"] for row in rows} == {f"content-{index}" for index in range(count)}
    assert updated.last_message_at is not None


def test_concurrent_retries_with_same_idempotency_key_persist_one_message(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    count = 10
    barrier = Barrier(count)

    def _append(_index: int):
        barrier.wait()
        return db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user",
            content="same content",
            metadata={"shared": True},
            idempotency_key="shared-key",
        )

    with ThreadPoolExecutor(max_workers=count) as executor:
        results = list(executor.map(_append, range(count)))

    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT message_id, sequence_number FROM chat_messages WHERE conversation_id = ?",
            (conversation.conversation_id,),
        ).fetchall()

    assert len(results) == count
    assert len(rows) == 1
    assert len({result.message_id for result in results}) == 1
    assert rows[0]["message_id"] == results[0].message_id
    assert int(rows[0]["sequence_number"]) == 1
