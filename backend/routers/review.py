"""Exercise review, SRS due items, and generation task history."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException

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
    user_id: str = "default_user",
    error_type: Optional[str] = None,
):
    if not answers:
        raise HTTPException(status_code=400, detail="No answers provided")

    lesson_id = answers[0].lesson_id
    lesson_data = load_lesson_payload(lesson_id)
    review_data = score_answers(lesson_data, answers)

    db.save_exercise_result(
        user_id=user_id,
        lesson_id=lesson_id,
        exercise_type="mixed",
        total_questions=review_data["total_questions"],
        correct_count=review_data["correct_count"],
        accuracy_rate=review_data["accuracy_rate"],
    )

    stats = UserRPGStats(**db.get_rpg_stats(user_id))
    if error_type and review_data["correct_count"] < review_data["total_questions"]:
        stats.error_distribution[error_type] = stats.error_distribution.get(error_type, 0) + (
            review_data["total_questions"] - review_data["correct_count"]
        )

    xp_amount = (review_data["correct_count"] * 10) + (
        (review_data["total_questions"] - review_data["correct_count"]) * 2
    )
    xp_result = gamification_engine.add_xp(user_id, xp_amount)
    db.save_rpg_stats(user_id, stats.model_dump(mode="json"))

    language = lesson_data["metadata"]["language"]
    update_progress_after_review(user_id, language, review_data["total_questions"], review_data["correct_count"])
    update_srs_after_review(user_id, language, lesson_data, review_data["accuracy_rate"])

    return {
        "success": True,
        **review_data,
        "gamification": {"xp_added": xp_amount, "leveled_up": xp_result.get("leveled_up")},
    }


@router.get("/srs/due")
async def get_due_items(language: Optional[str] = None, user_id: str = "default_user"):
    return {"success": True, "items": db.get_due_srs_items(user_id, language=language)}


@router.get("/tasks")
async def get_tasks(limit: int = 10):
    return {"success": True, "tasks": db.get_generation_tasks("default_user", limit)}
