"""Unit tests for services.lesson_ops (scoring and invariants)."""
import pytest

from models import ReviewAnswer
from services.lesson_ops import score_answers


@pytest.fixture
def minimal_lesson():
    return {
        "grammar": {
            "exercises": [
                {"question": "Choose A", "correct_answer": "A", "explanation": "because"},
            ]
        },
        "reading": {
            "questions": [
                {
                    "question": "Q1",
                    "options": ["X", "Y"],
                    "correct_answer": "Y",
                    "explanation": "read",
                }
            ]
        },
    }


def test_score_answers_all_correct(minimal_lesson):
    answers = [
        ReviewAnswer(
            lesson_id="l1",
            exercise_type="grammar",
            question_index=0,
            user_answer="A",
            correct_answer="A",
        ),
        ReviewAnswer(
            lesson_id="l1",
            exercise_type="reading",
            question_index=0,
            user_answer="Y",
            correct_answer="Y",
        ),
    ]
    r = score_answers(minimal_lesson, answers)
    assert r["total_questions"] == 2
    assert r["correct_count"] == 2
    assert r["accuracy_rate"] == 100.0
    assert r["incorrect_items"] == []


def test_score_answers_ignores_out_of_range_index(minimal_lesson):
    # When an answer has an out-of-range index, it is ignored.
    # All actual questions are then treated as unanswered (wrong).
    answers = [
        ReviewAnswer(
            lesson_id="l1",
            exercise_type="grammar",
            question_index=99,
            user_answer="A",
            correct_answer="A",
        ),
    ]
    r = score_answers(minimal_lesson, answers)
    # Both grammar (1) and reading (1) questions are unanswered, so correct_count=0
    assert r["correct_count"] == 0
    # Both questions appear in incorrect_items as unanswered
    assert len(r["incorrect_items"]) == 2
    assert all(item["user_answer"] == "(no answer)" for item in r["incorrect_items"])


def test_score_answers_case_insensitive_match(minimal_lesson):
    answers = [
        ReviewAnswer(
            lesson_id="l1",
            exercise_type="grammar",
            question_index=0,
            user_answer="  a ",
            correct_answer="A",
        ),
    ]
    r = score_answers(minimal_lesson, answers)
    assert r["correct_count"] == 1
