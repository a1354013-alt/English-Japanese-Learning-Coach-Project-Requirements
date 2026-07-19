from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from database import Database
from repositories import chat_repository as chat_repository_module
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


def _make_db(tmp_path) -> Database:
    return Database(str(tmp_path / "chat.db"))


def _insert_lesson(
    db: Database,
    lesson_id: str = "lesson-1",
    *,
    user_id: str = "default_user",
    language: str = "EN",
) -> None:
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
                user_id,
                language,
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
    db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="first",
    )
    db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="assistant",
        content="second",
    )

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
        summary_through_sequence=2,
    )
    cleared = db.chat_repository.update_conversation_summary(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        summary=None,
    )
    unlinked = db.chat_repository.set_conversation_lesson_link(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        lesson_id=None,
    )

    assert renamed.title == "Renamed chat"
    assert linked.lesson_id == "lesson-1"
    assert summarized.summary == "Conversation summary"
    assert summarized.summary_through_sequence == 2
    assert summarized.summary_updated_at is not None
    assert cleared.summary is None
    assert cleared.summary_through_sequence == 0
    assert cleared.summary_updated_at is None
    assert unlinked.lesson_id is None


def test_summary_checkpoint_rejects_negative_or_future_sequence(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="only",
    )

    with pytest.raises(InvalidChatSummaryCheckpointError):
        db.chat_repository.update_conversation_summary(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            summary="bad",
            summary_through_sequence=-1,
        )
    with pytest.raises(InvalidChatSummaryCheckpointError):
        db.chat_repository.update_conversation_summary(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            summary="too far",
            summary_through_sequence=2,
        )


def test_invalid_lesson_link_raises_explicit_error(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)

    with pytest.raises(LessonLinkNotFoundError):
        db.chat_repository.set_conversation_lesson_link(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            lesson_id="missing-lesson",
        )


def test_create_conversation_validates_lesson_ownership_and_language(tmp_path):
    db = _make_db(tmp_path)
    _insert_lesson(db, "en-owned", user_id="default_user", language="EN")
    _insert_lesson(db, "jp-owned", user_id="default_user", language="JP")
    _insert_lesson(db, "other-owned", user_id="other_user", language="EN")

    linked = db.chat_repository.create_conversation(
        user_id="default_user",
        language="EN",
        title="Linked",
        lesson_id="en-owned",
    )

    assert linked.lesson_id == "en-owned"

    with pytest.raises(LessonLinkNotFoundError):
        db.chat_repository.create_conversation(
            user_id="default_user",
            language="EN",
            title="Wrong owner",
            lesson_id="other-owned",
        )
    with pytest.raises(LessonLinkIntegrityError):
        db.chat_repository.create_conversation(
            user_id="default_user",
            language="EN",
            title="Wrong language",
            lesson_id="jp-owned",
        )
    with pytest.raises(LessonLinkNotFoundError):
        db.chat_repository.create_conversation(
            user_id="default_user",
            language="EN",
            title="Missing",
            lesson_id="missing-lesson",
        )


def test_set_conversation_lesson_link_validates_ownership_language_and_unlink(tmp_path):
    db = _make_db(tmp_path)
    _insert_lesson(db, "en-owned", user_id="default_user", language="EN")
    _insert_lesson(db, "jp-owned", user_id="default_user", language="JP")
    _insert_lesson(db, "other-owned", user_id="other_user", language="EN")
    conversation = _create_conversation(db, "EN")

    linked = db.chat_repository.set_conversation_lesson_link(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        lesson_id="en-owned",
    )
    assert linked.lesson_id == "en-owned"

    with pytest.raises(LessonLinkNotFoundError):
        db.chat_repository.set_conversation_lesson_link(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            lesson_id="other-owned",
        )
    with pytest.raises(LessonLinkIntegrityError):
        db.chat_repository.set_conversation_lesson_link(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            lesson_id="jp-owned",
        )
    with pytest.raises(LessonLinkNotFoundError):
        db.chat_repository.set_conversation_lesson_link(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            lesson_id="missing-lesson",
        )

    unlinked = db.chat_repository.set_conversation_lesson_link(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        lesson_id=None,
    )
    assert unlinked.lesson_id is None


def test_deleting_linked_lesson_sets_conversation_link_to_null(tmp_path):
    db = _make_db(tmp_path)
    _insert_lesson(db, "lesson-1")
    conversation = db.chat_repository.create_conversation(
        user_id="default_user",
        language="EN",
        title="Linked",
        lesson_id="lesson-1",
    )

    with db.get_connection() as conn:
        conn.execute("DELETE FROM lessons WHERE lesson_id = ?", ("lesson-1",))

    refreshed = db.chat_repository.get_conversation(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
    )
    assert refreshed.lesson_id is None


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


def test_idempotency_isolation_rejects_other_user_exact_retry(tmp_path):
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

    with pytest.raises(ConversationNotFoundError):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="other_user",
            role="user",
            content="same request",
            metadata={"turn": 1},
            idempotency_key="retry-1",
        )

    owner_retry = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="same request",
        metadata={"turn": 1},
        idempotency_key="retry-1",
    )
    assert owner_retry.message_id == first.message_id


@pytest.mark.parametrize(
    ("content", "metadata", "idempotency_key"),
    (
        ("different content", {"turn": 1}, "retry-1"),
        ("same request", {"turn": 2}, "retry-1"),
        ("same request", {"turn": 1}, "retry-2"),
    ),
)
def test_idempotency_isolation_rejects_other_user_variants(tmp_path, content, metadata, idempotency_key):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="same request",
        metadata={"turn": 1},
        idempotency_key="retry-1",
    )

    with pytest.raises(ConversationNotFoundError):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="other_user",
            role="user",
            content=content,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )


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


@pytest.mark.parametrize("bad_key", ("", "   "))
def test_blank_idempotency_keys_raise_explicit_domain_error(tmp_path, bad_key):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)

    with pytest.raises(InvalidIdempotencyKeyError):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user",
            content="hello",
            idempotency_key=bad_key,
        )


def test_overlong_idempotency_key_raises_explicit_domain_error(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)

    with pytest.raises(InvalidIdempotencyKeyError):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user",
            content="hello",
            idempotency_key="x" * 256,
        )


def test_idempotency_key_trims_surrounding_whitespace(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)

    first = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="hello",
        idempotency_key="  retry-1  ",
    )
    second = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="hello",
        idempotency_key="retry-1",
    )

    assert first.message_id == second.message_id
    assert second.idempotency_key == "retry-1"


def test_metadata_none_empty_and_key_ordering_are_canonicalized_for_retries(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)

    none_first = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="none",
        metadata=None,
        idempotency_key="none-key",
    )
    none_retry = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="none",
        metadata=None,
        idempotency_key="none-key",
    )
    empty_first = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="assistant",
        content="empty",
        metadata={},
        idempotency_key="empty-key",
    )
    empty_retry = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="assistant",
        content="empty",
        metadata={},
        idempotency_key="empty-key",
    )
    nested_first = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="nested",
        metadata={"b": {"y": True, "x": [1, 2]}, "a": 1},
        idempotency_key="nested-key",
    )
    nested_retry = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="nested",
        metadata={"a": 1, "b": {"x": [1, 2], "y": True}},
        idempotency_key="nested-key",
    )

    assert none_first.message_id == none_retry.message_id
    assert none_retry.metadata is None
    assert empty_first.message_id == empty_retry.message_id
    assert empty_retry.metadata == {}
    assert nested_first.message_id == nested_retry.message_id
    assert nested_retry.metadata == {"a": 1, "b": {"x": [1, 2], "y": True}}


def test_metadata_idempotency_conflict_raises_explicit_error(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="nested",
        metadata={"flags": [True, False], "score": 1},
        idempotency_key="nested-key",
    )

    with pytest.raises(IdempotencyConflictError):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user",
            content="nested",
            metadata={"flags": [True], "score": 1},
            idempotency_key="nested-key",
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


def test_message_timestamps_are_assigned_after_lock_and_remain_monotonic(tmp_path, monkeypatch):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    timestamps = iter(
        (
            datetime(2026, 7, 19, 9, 0, 5, tzinfo=ZoneInfo("Asia/Taipei")),
            datetime(2026, 7, 19, 9, 0, 4, tzinfo=ZoneInfo("Asia/Taipei")),
        )
    )
    monkeypatch.setattr(chat_repository_module, "local_now", lambda: next(timestamps))

    first = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="first",
        idempotency_key="time-1",
    )
    second = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="assistant",
        content="second",
        idempotency_key="time-2",
    )
    updated = db.chat_repository.get_conversation(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
    )

    assert first.sequence_number == 1
    assert second.sequence_number == 2
    assert second.created_at >= first.created_at
    assert updated.updated_at == second.created_at
    assert updated.last_message_at == second.created_at


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


def test_concurrent_retries_with_same_idempotency_key_and_conflicting_payload_raise_domain_error(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    barrier = Barrier(2)

    def _append(content: str):
        barrier.wait()
        return db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user",
            content=content,
            metadata={"shared": True},
            idempotency_key="shared-key",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_append, value) for value in ("same content", "different content")]
        results = []
        errors = []
        for future in futures:
            try:
                results.append(future.result())
            except IdempotencyConflictError as exc:
                errors.append(exc)

    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT message_id, sequence_number, content FROM chat_messages WHERE conversation_id = ?",
            (conversation.conversation_id,),
        ).fetchall()

    assert len(results) == 1
    assert len(errors) == 1
    assert len(rows) == 1
    assert rows[0]["content"] in {"same content", "different content"}
    assert results[0].message_id == rows[0]["message_id"]


def test_concurrent_appends_preserve_monotonic_timestamps_and_stable_ordering(tmp_path):
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
            idempotency_key=f"order-{index}",
        )

    with ThreadPoolExecutor(max_workers=count) as executor:
        results = list(executor.map(_append, range(count)))

    ordered = db.chat_repository.get_messages_page(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        limit=20,
    ).messages
    updated = db.chat_repository.get_conversation(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
    )

    assert [message.sequence_number for message in ordered] == list(range(1, count + 1))
    assert [message.created_at for message in ordered] == sorted(message.created_at for message in ordered)
    assert updated.last_message_at == ordered[-1].created_at
    assert updated.updated_at == ordered[-1].created_at
    assert len({result.message_id for result in results}) == count


def test_concurrent_append_stress_rounds_keep_sequences_contiguous(tmp_path):
    db = _make_db(tmp_path)
    conversation = _create_conversation(db)
    rounds = 3
    per_round = 10

    for round_index in range(rounds):
        barrier = Barrier(per_round)

        def _append(index: int):
            barrier.wait()
            return db.chat_repository.append_message(
                conversation_id=conversation.conversation_id,
                user_id="default_user",
                role="user",
                content=f"round-{round_index}-content-{index}",
                idempotency_key=f"round-{round_index}-key-{index}",
            )

        with ThreadPoolExecutor(max_workers=per_round) as executor:
            list(executor.map(_append, range(per_round)))

    messages = db.chat_repository.get_messages_page(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        limit=rounds * per_round + 5,
    ).messages

    assert len(messages) == rounds * per_round
    assert [message.sequence_number for message in messages] == list(range(1, rounds * per_round + 1))
