from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from database import Database
from models import LearningSessionEventMetadata, LearningSessionEventType
from repositories.errors import (
    InvalidLearningSessionPaginationError,
    InvalidLearningSessionTransitionError,
    LearningSessionAlreadyActiveError,
    LearningSessionIdempotencyConflictError,
    LearningSessionNotActiveError,
    LearningSessionNotFoundError,
)


def _make_db(tmp_path) -> Database:
    return Database(str(tmp_path / "learning-sessions.db"))


def _start_session(db: Database, *, user_id: str = "default_user", language: str = "EN", planned_minutes: int | None = 25):
    return db.learning_session_repository.start_session(
        user_id=user_id,
        language=language,
        planned_minutes=planned_minutes,
    )


def test_session_creation_active_lookup_and_language_isolation(tmp_path):
    db = _make_db(tmp_path)

    en_session = _start_session(db, language="EN", planned_minutes=20)
    jp_session = _start_session(db, language="JP", planned_minutes=30)

    assert en_session.language == "EN"
    assert jp_session.language == "JP"
    assert db.learning_session_repository.find_active_session(user_id="default_user", language="EN") == en_session
    assert db.learning_session_repository.find_active_session(user_id="default_user", language="JP") == jp_session


def test_one_active_session_per_user_and_language(tmp_path):
    db = _make_db(tmp_path)
    _start_session(db, language="EN")

    with pytest.raises(LearningSessionAlreadyActiveError):
        _start_session(db, language="EN")

    other_user = _start_session(db, user_id="other_user", language="EN")
    assert other_user.language == "EN"


def test_session_history_listing_uses_cursor_pagination(tmp_path):
    db = _make_db(tmp_path)
    first = _start_session(db, language="EN", planned_minutes=10)
    db.learning_session_repository.complete_session(
        session_id=first.session_id,
        user_id="default_user",
        idempotency_key="complete-first",
    )
    second = _start_session(db, language="EN", planned_minutes=20)
    db.learning_session_repository.complete_session(
        session_id=second.session_id,
        user_id="default_user",
        idempotency_key="complete-second",
    )
    third = _start_session(db, language="JP", planned_minutes=30)
    db.learning_session_repository.abandon_session(session_id=third.session_id, user_id="default_user")

    first_page = db.learning_session_repository.list_session_history(user_id="default_user", limit=2)
    assert [session.session_id for session in first_page.sessions] == [third.session_id, second.session_id]
    assert first_page.has_more is True
    assert first_page.next_cursor is not None

    second_page = db.learning_session_repository.list_session_history(
        user_id="default_user",
        limit=2,
        cursor=first_page.next_cursor,
    )
    assert [session.session_id for session in second_page.sessions] == [first.session_id]
    assert second_page.has_more is False


def test_event_append_pagination_ordering_and_metadata_canonicalization(tmp_path):
    db = _make_db(tmp_path)
    session = _start_session(db)

    first = db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type="lesson_started",
        entity_type="lesson",
        entity_id="lesson-1",
        metadata=LearningSessionEventMetadata(note="hello", correct=True),
        idempotency_key="event-1",
    )
    second = db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type="review_answered",
        entity_type="review",
        entity_id="review-1",
        metadata=LearningSessionEventMetadata(correct=False, note="retry"),
        idempotency_key="event-2",
    )

    page = db.learning_session_repository.list_events(session_id=session.session_id, user_id="default_user", limit=1)
    assert [event.sequence_number for event in page.events] == [1]
    assert page.has_more is True
    assert page.next_cursor == "1"

    next_page = db.learning_session_repository.list_events(
        session_id=session.session_id,
        user_id="default_user",
        limit=5,
        cursor=page.next_cursor,
    )
    assert [event.sequence_number for event in next_page.events] == [2]
    assert next_page.has_more is False

    with db.get_connection() as conn:
        stored = conn.execute(
            "SELECT metadata_json FROM learning_session_events WHERE event_id = ?",
            (first.event_id,),
        ).fetchone()
    assert stored["metadata_json"] == '{"correct":true,"note":"hello"}'
    assert second.metadata is not None
    assert second.metadata.correct is False


def test_event_idempotent_retry_and_conflict(tmp_path):
    db = _make_db(tmp_path)
    session = _start_session(db)

    first = db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type="session_note",
        metadata=LearningSessionEventMetadata(note="same payload"),
        idempotency_key="dup-key",
    )
    retried = db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type="session_note",
        metadata=LearningSessionEventMetadata(note="same payload"),
        idempotency_key="dup-key",
    )
    assert retried.event_id == first.event_id

    with pytest.raises(LearningSessionIdempotencyConflictError):
        db.learning_session_repository.append_event(
            session_id=session.session_id,
            user_id="default_user",
            event_type="session_note",
            metadata=LearningSessionEventMetadata(note="different payload"),
            idempotency_key="dup-key",
        )


def test_complete_retry_abandon_invalid_transitions_and_no_append_after_completion(tmp_path):
    db = _make_db(tmp_path)
    session = _start_session(db)
    completed = db.learning_session_repository.complete_session(
        session_id=session.session_id,
        user_id="default_user",
        idempotency_key="complete-1",
    )
    retried = db.learning_session_repository.complete_session(
        session_id=session.session_id,
        user_id="default_user",
        idempotency_key="complete-1",
    )

    assert completed.status.value == "completed"
    assert retried.ended_at == completed.ended_at
    assert retried.duration_seconds == completed.duration_seconds

    with pytest.raises(LearningSessionIdempotencyConflictError):
        db.learning_session_repository.complete_session(
            session_id=session.session_id,
            user_id="default_user",
            idempotency_key="complete-2",
        )
    with pytest.raises(LearningSessionNotActiveError):
        db.learning_session_repository.append_event(
            session_id=session.session_id,
            user_id="default_user",
            event_type="session_note",
            metadata=LearningSessionEventMetadata(note="late"),
        )

    active = _start_session(db, language="JP")
    abandoned = db.learning_session_repository.abandon_session(
        session_id=active.session_id,
        user_id="default_user",
        idempotency_key="abandon-1",
    )
    retried_abandon = db.learning_session_repository.abandon_session(
        session_id=active.session_id,
        user_id="default_user",
        idempotency_key="abandon-2",
    )
    assert abandoned.status.value == "abandoned"
    assert retried_abandon.ended_at == abandoned.ended_at

    with pytest.raises(InvalidLearningSessionTransitionError):
        db.learning_session_repository.abandon_session(
            session_id=session.session_id,
            user_id="default_user",
        )


def test_delete_cascade_summary_ownership_and_transaction_rollback(tmp_path):
    db = _make_db(tmp_path)
    session = _start_session(db)
    db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type=LearningSessionEventType.lesson_completed,
        entity_type="lesson",
        entity_id="lesson-1",
        metadata=LearningSessionEventMetadata(correct=True),
    )
    db.learning_session_repository.append_event(
        session_id=session.session_id,
        user_id="default_user",
        event_type=LearningSessionEventType.review_answered,
        entity_type="review",
        entity_id="review-1",
        metadata=LearningSessionEventMetadata(correct=False, note="miss"),
    )
    db.learning_session_repository.complete_session(
        session_id=session.session_id,
        user_id="default_user",
        idempotency_key="complete-summary",
    )

    summary = db.learning_session_repository.produce_summary(session_id=session.session_id, user_id="default_user")
    assert summary.total_event_count == 2
    assert summary.lesson_completion_count == 1
    assert summary.review_answer_count == 1
    assert summary.correct_event_count == 1
    assert summary == db.learning_session_repository.produce_summary(
        session_id=session.session_id,
        user_id="default_user",
    )

    with pytest.raises(LearningSessionNotFoundError):
        db.learning_session_repository.get_session(session_id=session.session_id, user_id="other_user")

    with pytest.raises(InvalidLearningSessionPaginationError):
        db.learning_session_repository.list_events(
            session_id=session.session_id,
            user_id="default_user",
            cursor="bad-cursor",
        )

    db.learning_session_repository.delete_session(session_id=session.session_id, user_id="default_user")
    with db.get_connection() as conn:
        remaining = conn.execute(
            "SELECT COUNT(1) AS count FROM learning_session_events WHERE session_id = ?",
            (session.session_id,),
        ).fetchone()
    assert remaining["count"] == 0

    active = _start_session(db, language="EN")
    with pytest.raises(InvalidLearningSessionTransitionError):
        db.learning_session_repository.delete_session(session_id=active.session_id, user_id="default_user")
    with db.get_connection() as conn:
        still_exists = conn.execute(
            "SELECT COUNT(1) AS count FROM learning_sessions WHERE session_id = ?",
            (active.session_id,),
        ).fetchone()
    assert still_exists["count"] == 1


def test_concurrent_event_appends_produce_unique_contiguous_sequences(tmp_path):
    db = _make_db(tmp_path)
    session = _start_session(db)
    barrier = Barrier(20)

    def append(index: int):
        barrier.wait()
        return db.learning_session_repository.append_event(
            session_id=session.session_id,
            user_id="default_user",
            event_type="session_note",
            metadata=LearningSessionEventMetadata(note=f"n-{index}"),
            idempotency_key=f"k-{index}",
        )

    with ThreadPoolExecutor(max_workers=20) as pool:
        events = list(pool.map(append, range(20)))

    sequences = sorted(event.sequence_number for event in events)
    assert sequences == list(range(1, 21))
    assert len({event.event_id for event in events}) == 20


def test_concurrent_idempotency_and_completion_races(tmp_path):
    db = _make_db(tmp_path)
    session = _start_session(db)
    barrier = Barrier(8)

    def append_same_key(note: str):
        barrier.wait()
        return db.learning_session_repository.append_event(
            session_id=session.session_id,
            user_id="default_user",
            event_type="session_note",
            metadata=LearningSessionEventMetadata(note=note),
            idempotency_key="same-key",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(append_same_key, "same") for _ in range(8)]
        results = [future.result() for future in futures]
    assert len({event.event_id for event in results}) == 1

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            db.learning_session_repository.append_event,
            session_id=session.session_id,
            user_id="default_user",
            event_type="session_note",
            metadata=LearningSessionEventMetadata(note="same"),
            idempotency_key="conflict-key",
        )
        second = pool.submit(
            db.learning_session_repository.append_event,
            session_id=session.session_id,
            user_id="default_user",
            event_type="session_note",
            metadata=LearningSessionEventMetadata(note="different"),
            idempotency_key="conflict-key",
        )
        winner = first.result()
        with pytest.raises(LearningSessionIdempotencyConflictError):
            second.result()
    assert winner.sequence_number >= 1

    race_session = _start_session(db, language="JP")
    completion_barrier = Barrier(2)

    def complete():
        completion_barrier.wait()
        return db.learning_session_repository.complete_session(
            session_id=race_session.session_id,
            user_id="default_user",
            idempotency_key="done-key",
        )

    def append_or_conflict():
        completion_barrier.wait()
        try:
            return db.learning_session_repository.append_event(
                session_id=race_session.session_id,
                user_id="default_user",
                event_type="session_note",
                metadata=LearningSessionEventMetadata(note="race"),
                idempotency_key="race-key",
            )
        except LearningSessionNotActiveError:
            return "not-active"

    with ThreadPoolExecutor(max_workers=2) as pool:
        completed_future = pool.submit(complete)
        raced_future = pool.submit(append_or_conflict)
        completed = completed_future.result()
        raced = raced_future.result()

    assert completed.status.value == "completed"
    final_session = db.learning_session_repository.get_session(
        session_id=race_session.session_id,
        user_id="default_user",
    )
    assert final_session.status.value == "completed"
    events_page = db.learning_session_repository.list_events(
        session_id=race_session.session_id,
        user_id="default_user",
        limit=10,
    )
    assert len(events_page.events) in {0, 1}
    assert raced == "not-active" or raced.sequence_number == 1


def test_concurrent_completion_requests_converge_on_one_canonical_state(tmp_path):
    db = _make_db(tmp_path)
    session = _start_session(db)
    barrier = Barrier(6)

    def complete_once():
        barrier.wait()
        return db.learning_session_repository.complete_session(
            session_id=session.session_id,
            user_id="default_user",
            idempotency_key="complete-once",
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: complete_once(), range(6)))

    ended_values = {result.ended_at for result in results}
    duration_values = {result.duration_seconds for result in results}
    assert len(ended_values) == 1
    assert len(duration_values) == 1


def test_clear_demo_user_session_data_and_different_sessions_can_progress(tmp_path):
    db = _make_db(tmp_path)
    en_session = _start_session(db, language="EN")
    jp_session = _start_session(db, language="JP")

    def append_one(session_id: str, key: str):
        return db.learning_session_repository.append_event(
            session_id=session_id,
            user_id="default_user",
            event_type="session_note",
            metadata=LearningSessionEventMetadata(note=key),
            idempotency_key=key,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(
            pool.map(
                lambda args: append_one(*args),
                [(en_session.session_id, "en-note"), (jp_session.session_id, "jp-note")],
            )
        )

    assert first.session_id != second.session_id
    assert db.learning_session_repository.clear_local_demo_user_session_data(user_id="default_user") == 2
    with pytest.raises(LearningSessionNotFoundError):
        db.learning_session_repository.get_session(session_id=en_session.session_id, user_id="default_user")
