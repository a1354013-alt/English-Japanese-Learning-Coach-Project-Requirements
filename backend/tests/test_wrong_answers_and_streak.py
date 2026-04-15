"""Database-level tests for Wrong Answer Notebook + Daily Learning Streak."""

from datetime import date

from database import Database


def test_wrong_answer_upsert_dedupes_active(tmp_path):
    db = Database(str(tmp_path / "t.db"))

    first = db.upsert_wrong_answer(
        user_id="u1",
        language="EN",
        question_type="grammar",
        question="Choose A",
        user_answer="B",
        correct_answer="A",
        source_lesson_id="l1",
    )
    assert first["status"] == "active"
    assert first["wrong_count"] == 1

    second = db.upsert_wrong_answer(
        user_id="u1",
        language="EN",
        question_type="grammar",
        question="Choose A",
        user_answer="C",
        correct_answer="A",
        source_lesson_id="l1",
    )
    assert second["id"] == first["id"]
    assert second["wrong_count"] == 2
    assert second["user_answer"] == "C"

    mastered = db.update_wrong_answer_status(user_id="u1", wrong_answer_id=int(first["id"]), status="mastered")
    assert mastered is not None
    assert mastered["status"] == "mastered"

    third = db.upsert_wrong_answer(
        user_id="u1",
        language="EN",
        question_type="grammar",
        question="Choose A",
        user_answer="D",
        correct_answer="A",
        source_lesson_id="l1",
    )
    assert third["status"] == "active"
    assert third["wrong_count"] == 1
    assert third["id"] != first["id"]


def test_streak_counts_consecutive_days(tmp_path):
    db = Database(str(tmp_path / "t.db"))

    db.record_learning_activity(user_id="u1", activity_type="review", activity_date="2026-04-13")
    db.record_learning_activity(user_id="u1", activity_type="review", activity_date="2026-04-14")

    info = db.get_streak_info("u1", today=date(2026, 4, 15))
    assert info["today_completed"] is False
    assert info["current_streak"] == 2
    assert info["longest_streak"] == 2
    assert info["last_active_date"] == "2026-04-14"

    db.record_learning_activity(user_id="u1", activity_type="generate_lesson", activity_date="2026-04-15")
    info2 = db.get_streak_info("u1", today=date(2026, 4, 15))
    assert info2["today_completed"] is True
    assert info2["current_streak"] == 3
    assert info2["longest_streak"] == 3
    assert info2["last_active_date"] == "2026-04-15"

