"""Lesson file loading and review scoring / progress side effects."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException

from database import db
from models import ReviewAnswer
from srs import srs_engine


def load_lesson_payload(lesson_id: str) -> Dict[str, Any]:
    lesson_meta = db.get_lesson(lesson_id)
    if not lesson_meta:
        raise HTTPException(status_code=404, detail="Lesson not found")

    file_path = Path(lesson_meta["file_path"]).resolve()
    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Lesson file is missing")

    return json.loads(file_path.read_text(encoding="utf-8"))


def score_answers(lesson_data: Dict[str, Any], answers: List[ReviewAnswer]) -> Dict[str, Any]:
    incorrect_items: List[Dict[str, str]] = []
    correct_count = 0

    # Calculate total questions from the lesson structure (not from submitted answers)
    grammar_exercises = lesson_data.get("grammar", {}).get("exercises", [])
    reading_questions = lesson_data.get("reading", {}).get("questions", [])
    total_grammar = len(grammar_exercises)
    total_reading = len(reading_questions)
    total_questions = total_grammar + total_reading

    # Build a map of submitted answers by (exercise_type, question_index)
    answer_map: Dict[tuple, ReviewAnswer] = {}
    for answer in answers:
        answer_map[(answer.exercise_type, answer.question_index)] = answer

    # Score grammar exercises
    for idx, exercise in enumerate(grammar_exercises):
        answer = answer_map.get(("grammar", idx))
        if answer is None:
            # Unanswered question counts as wrong
            incorrect_items.append(
                {
                    "question": str(exercise.get("question", "")),
                    "user_answer": "(no answer)",
                    "correct_answer": str(exercise.get("correct_answer", "")),
                    "explanation": str(exercise.get("explanation", "")),
                }
            )
            continue

        user_text = str(answer.user_answer).strip().lower()
        correct_text = str(exercise.get("correct_answer", "")).strip().lower()
        if user_text == correct_text:
            correct_count += 1
        else:
            incorrect_items.append(
                {
                    "question": str(exercise.get("question", "")),
                    "user_answer": str(answer.user_answer),
                    "correct_answer": str(exercise.get("correct_answer", "")),
                    "explanation": str(exercise.get("explanation", "")),
                }
            )

    # Score reading questions
    for idx, question in enumerate(reading_questions):
        answer = answer_map.get(("reading", idx))
        if answer is None:
            # Unanswered question counts as wrong
            incorrect_items.append(
                {
                    "question": str(question.get("question", "")),
                    "user_answer": "(no answer)",
                    "correct_answer": str(question.get("correct_answer", "")),
                    "explanation": str(question.get("explanation", "")),
                }
            )
            continue

        user_text = str(answer.user_answer).strip().lower()
        correct_text = str(question.get("correct_answer", "")).strip().lower()
        if user_text == correct_text:
            correct_count += 1
        else:
            incorrect_items.append(
                {
                    "question": str(question.get("question", "")),
                    "user_answer": str(answer.user_answer),
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
) -> Dict[str, Any]:
    progress = db.get_progress(user_id)
    key = "english_progress" if language == "EN" else "japanese_progress"

    target = progress[key]
    if increment_completed_lessons:
        target["completed_lessons"] += 1
    target["total_exercises"] += total
    target["correct_exercises"] += correct
    target["last_study_date"] = datetime.now().isoformat()
    target["accuracy_rate"] = (
        (target["correct_exercises"] / target["total_exercises"] * 100) if target["total_exercises"] else 0.0
    )

    db.save_progress(progress)
    return progress


def update_srs_after_review(
    user_id: str, language: str, lesson_data: Dict[str, Any], accuracy_rate: float
) -> None:
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
