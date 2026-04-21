"""Exercise review, SRS due items, and generation task history."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from config import settings

from database import db
from gamification_engine import gamification_engine
from models import ReviewAnswer, UserRPGStats
from services.lesson_ops import (
    load_lesson_payload,
    score_answers,
    update_progress_after_review,
    update_srs_after_review,
)

router = APIRouter(prefix="/api", tags=["review"])


@router.post("/review", response_model=dict)
async def submit_review(
    answers: List[ReviewAnswer],
    user_id: str = Query(default=settings.default_user_id),
    error_type: Optional[str] = None,
):
    if not answers:
        raise HTTPException(status_code=400, detail="No answers provided")

    lesson_id = answers[0].lesson_id
    lesson_data = load_lesson_payload(lesson_id)
    review_data = score_answers(lesson_data, answers)
    was_completed = db.has_exercise_result(user_id=user_id, lesson_id=lesson_id)

    # Any review submission counts as a learning activity (one per local day).
    db.record_learning_activity(user_id=user_id, activity_type="review")

    db.save_exercise_result(
        user_id=user_id,
        lesson_id=lesson_id,
        exercise_type="mixed",
        total_questions=review_data["total_questions"],
        correct_count=review_data["correct_count"],
        accuracy_rate=review_data["accuracy_rate"],
    )

    xp_amount = (review_data["correct_count"] * 10) + (
        (review_data["total_questions"] - review_data["correct_count"]) * 2
    )
    # Apply XP first so DB holds updated level/XP, then merge error_distribution on a fresh snapshot.
    xp_result = gamification_engine.add_xp(user_id, xp_amount)
    stats = UserRPGStats(**db.get_rpg_stats(user_id))
    if error_type and review_data["correct_count"] < review_data["total_questions"]:
        stats.error_distribution[error_type] = stats.error_distribution.get(error_type, 0) + (
            review_data["total_questions"] - review_data["correct_count"]
        )
    db.save_rpg_stats(user_id, stats.model_dump(mode="json"))

    language = lesson_data["metadata"]["language"]
    update_progress_after_review(
        user_id,
        language,
        review_data["total_questions"],
        review_data["correct_count"],
        increment_completed_lessons=not was_completed,
    )
    update_srs_after_review(user_id, language, lesson_data, review_data["accuracy_rate"])

    # Wrong Answer Notebook: persist each incorrect answer with dedupe/upsert.
    answer_map = {(a.exercise_type, a.question_index): a for a in answers}
    grammar_exercises = lesson_data.get("grammar", {}).get("exercises", [])
    for idx, exercise in enumerate(grammar_exercises):
        submitted = answer_map.get(("grammar", idx))
        user_answer = str(submitted.user_answer) if submitted is not None else "(no answer)"
        user_text = user_answer.strip().lower()
        correct_answer = str(exercise.get("correct_answer", ""))
        correct_text = correct_answer.strip().lower()
        if user_text == correct_text:
            continue
        db.upsert_wrong_answer(
            user_id=user_id,
            language=language,
            question_type="grammar",
            question=str(exercise.get("question", "")),
            user_answer=user_answer,
            correct_answer=correct_answer,
            source_lesson_id=lesson_id,
        )

    reading_questions = lesson_data.get("reading", {}).get("questions", [])
    for idx, question in enumerate(reading_questions):
        submitted = answer_map.get(("reading", idx))
        user_answer = str(submitted.user_answer) if submitted is not None else "(no answer)"
        user_text = user_answer.strip().lower()
        correct_answer = str(question.get("correct_answer", ""))
        correct_text = correct_answer.strip().lower()
        if user_text == correct_text:
            continue
        db.upsert_wrong_answer(
            user_id=user_id,
            language=language,
            question_type="reading",
            question=str(question.get("question", "")),
            user_answer=user_answer,
            correct_answer=correct_answer,
            source_lesson_id=lesson_id,
        )

    return {
        "success": True,
        **review_data,
        "gamification": {"xp_added": xp_amount, "leveled_up": xp_result.get("leveled_up")},
    }


@router.get("/srs/due")
async def get_due_items(
    language: Optional[str] = None,
    user_id: str = Query(default=settings.default_user_id),
):
    return {"success": True, "items": db.get_due_srs_items(user_id, language=language)}


@router.get("/tasks")
async def get_tasks(limit: int = 10, user_id: str = Query(default=settings.default_user_id)):
    return {"success": True, "tasks": db.get_generation_tasks(user_id, limit)}
