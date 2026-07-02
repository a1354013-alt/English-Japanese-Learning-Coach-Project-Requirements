"""Lesson file loading and review scoring / progress side effects."""
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List

from api_errors import api_error
from config import settings
from database import db
from models import ReviewAnswer
from srs import srs_engine
from time_utils import local_now

_ANSWER_PUNCTUATION_MAP = str.maketrans(
    {
        "\u3002": ".",
        "\u3001": ",",
        "\uff0e": ".",
        "\uff0c": ",",
        "\uff01": "!",
        "\uff1f": "?",
    }
)


def normalize_answer(value: Any) -> str:
    """Normalize deterministic answer differences without fuzzy grading."""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.translate(_ANSWER_PUNCTUATION_MAP)
    text = re.sub(r"\s+", " ", text.strip())
    return text.lower()


def _iter_accepted_answers(item: Dict[str, Any]) -> Iterable[str]:
    yield str(item.get("correct_answer", ""))
    raw = item.get("accepted_answers", [])
    if isinstance(raw, str):
        for part in re.split(r"\s*(?:\||;)\s*", raw):
            if part:
                yield part
    elif isinstance(raw, list):
        for value in raw:
            if value is not None:
                yield str(value)


def is_answer_correct(user_answer: Any, item: Dict[str, Any]) -> bool:
    normalized_user = normalize_answer(user_answer)
    return any(normalized_user == normalize_answer(candidate) for candidate in _iter_accepted_answers(item))


def load_lesson_payload(lesson_id: str, *, user_id: str | None = None) -> Dict[str, Any]:
    lesson_meta = db.get_lesson(lesson_id, user_id=user_id)
    if not lesson_meta:
        raise api_error(404, "Lesson not found", "lesson_not_found")

    raw_path = str(lesson_meta["file_path"])
    p = Path(raw_path)
    if p.is_absolute():
        file_path = p.resolve()
    else:
        base = settings.data_path.resolve()
        file_path = (base / p).resolve()
        try:
            file_path.relative_to(base)
        except ValueError:
            raise api_error(500, "Invalid lesson file path", "invalid_lesson_file_path") from None
    if not file_path.exists():
        raise api_error(500, "Lesson file is missing", "lesson_file_missing")

    return json.loads(file_path.read_text(encoding="utf-8"))


def score_answers(lesson_data: Dict[str, Any], answers: List[ReviewAnswer]) -> Dict[str, Any]:
    incorrect_items: List[Dict[str, str]] = []
    correct_count = 0

    grammar_exercises = lesson_data.get("grammar", {}).get("exercises", [])
    reading_questions = lesson_data.get("reading", {}).get("questions", [])
    total_questions = len(grammar_exercises) + len(reading_questions)

    answer_map: Dict[tuple, ReviewAnswer] = {}
    for answer in answers:
        answer_map[(answer.exercise_type, answer.question_index)] = answer

    for idx, exercise in enumerate(grammar_exercises):
        submitted = answer_map.get(("grammar", idx))
        if submitted is None:
            incorrect_items.append(
                {
                    "question": str(exercise.get("question", "")),
                    "user_answer": "(no answer)",
                    "correct_answer": str(exercise.get("correct_answer", "")),
                    "explanation": str(exercise.get("explanation", "")),
                }
            )
            continue

        if is_answer_correct(submitted.user_answer, exercise):
            correct_count += 1
        else:
            incorrect_items.append(
                {
                    "question": str(exercise.get("question", "")),
                    "user_answer": str(submitted.user_answer),
                    "correct_answer": str(exercise.get("correct_answer", "")),
                    "explanation": str(exercise.get("explanation", "")),
                }
            )

    for idx, question in enumerate(reading_questions):
        submitted = answer_map.get(("reading", idx))
        if submitted is None:
            incorrect_items.append(
                {
                    "question": str(question.get("question", "")),
                    "user_answer": "(no answer)",
                    "correct_answer": str(question.get("correct_answer", "")),
                    "explanation": str(question.get("explanation", "")),
                }
            )
            continue

        if is_answer_correct(submitted.user_answer, question):
            correct_count += 1
        else:
            incorrect_items.append(
                {
                    "question": str(question.get("question", "")),
                    "user_answer": str(submitted.user_answer),
                    "correct_answer": str(question.get("correct_answer", "")),
                    "explanation": str(question.get("explanation", "")),
                }
            )

    accuracy_rate = (correct_count / total_questions * 100) if total_questions else 0.0
    return {
        "total_questions": total_questions,
        "correct_count": correct_count,
        "accuracy_rate": accuracy_rate,
        "incorrect_items": incorrect_items,
    }


def update_progress_after_review(
    user_id: str,
    language: str,
    total: int,
    correct: int,
    *,
    increment_completed_lessons: bool,
    previous_best_correct: int | None = None,
) -> Dict[str, Any]:
    progress = db.get_progress(user_id)
    key = "english_progress" if language == "EN" else "japanese_progress"

    target = progress[key]
    if increment_completed_lessons:
        target["completed_lessons"] += 1
    if previous_best_correct is None:
        target["total_exercises"] += total
        target["correct_exercises"] += correct
    elif correct > previous_best_correct:
        target["correct_exercises"] += correct - previous_best_correct
    target["last_study_date"] = local_now().isoformat()
    target["accuracy_rate"] = (
        (target["correct_exercises"] / target["total_exercises"] * 100) if target["total_exercises"] else 0.0
    )

    db.save_progress(progress)
    return progress


def update_srs_after_review(
    user_id: str, language: str, lesson_data: Dict[str, Any], accuracy_rate: float
) -> None:
    # TODO: Move from lesson-wide accuracy to per-vocabulary outcomes once the review UI
    # captures word-level recall. Keep the existing behavior stable until that contract exists.
    quality = 5 if accuracy_rate >= 80 else 3 if accuracy_rate >= 50 else 2
    for vocab in lesson_data.get("vocabulary", []):
        word = str(vocab.get("word", "")).strip()
        if not word:
            continue
        prev = db.get_srs_item(user_id, word, language)
        interval = int(prev["interval"]) if prev else 0
        ease_factor = float(prev["ease_factor"]) if prev else 2.5
        repetition = int(prev["srs_level"]) if prev else 0

        srs_data = srs_engine.calculate(
            quality=quality,
            prev_interval=interval,
            prev_ease_factor=ease_factor,
            repetition=repetition,
        )
        db.update_srs_item(user_id, word, language, srs_data, vocab)
