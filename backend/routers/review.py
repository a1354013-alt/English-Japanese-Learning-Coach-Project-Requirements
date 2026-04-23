"""Exercise review, SRS due items, and generation task history."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from database import db
from gamification_engine import gamification_engine
from models import ErrorType, ReviewAnswer, UserRPGStats
from routers.deps import require_demo_user_id
from services.lesson_ops import (
    load_lesson_payload,
    score_answers,
    update_progress_after_review,
    update_srs_after_review,
)
from srs import srs_engine

router = APIRouter(prefix="/api", tags=["review"])

def _validate_review_submission(lesson_data: dict, answers: List[ReviewAnswer]) -> None:
    lesson_id = answers[0].lesson_id
    if any(a.lesson_id != lesson_id for a in answers):
        raise HTTPException(status_code=400, detail="Invalid review payload: mixed lesson_id")

    grammar_exercises = lesson_data.get("grammar", {}).get("exercises", []) or []
    reading_questions = lesson_data.get("reading", {}).get("questions", []) or []

    seen: set[tuple[str, int]] = set()
    for a in answers:
        # Disallow blank answers (avoid polluted wrong-answer notebook/analytics).
        if str(a.user_answer).strip() == "":
            raise HTTPException(status_code=400, detail="Invalid review payload: user_answer must be non-empty")

        key = (a.exercise_type, a.question_index)
        if key in seen:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid review payload: duplicate answer for {a.exercise_type}[{a.question_index}]",
            )
        seen.add(key)

        if a.question_index < 0:
            raise HTTPException(status_code=400, detail="Invalid review payload: question_index must be >= 0")

        if a.exercise_type == "grammar":
            if a.question_index >= len(grammar_exercises):
                raise HTTPException(status_code=400, detail="Invalid review payload: grammar question_index out of range")
            expected = str((grammar_exercises[a.question_index] or {}).get("correct_answer", ""))
        else:
            if a.question_index >= len(reading_questions):
                raise HTTPException(status_code=400, detail="Invalid review payload: reading question_index out of range")
            expected = str((reading_questions[a.question_index] or {}).get("correct_answer", ""))

        if str(a.correct_answer).strip() != expected.strip():
            raise HTTPException(status_code=400, detail="Invalid review payload: correct_answer mismatch")


@router.post("/review", response_model=dict)
async def submit_review(
    answers: List[ReviewAnswer],
    user_id: str = Depends(require_demo_user_id),
    error_type: ErrorType | None = Query(default=None),
):
    if not answers:
        raise HTTPException(status_code=400, detail="No answers provided")

    lesson_id = answers[0].lesson_id
    lesson_data = load_lesson_payload(lesson_id, user_id=user_id)
    _validate_review_submission(lesson_data, answers)
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

    # Demo rule: XP/progress/SRS side-effects are awarded only once per lesson.
    # Re-submitting a review updates the latest exercise_result but must not allow point farming.
    xp_amount = 0
    xp_result = {"leveled_up": False}
    if not was_completed:
        xp_amount = (review_data["correct_count"] * 10) + (
            (review_data["total_questions"] - review_data["correct_count"]) * 2
        )
        # Apply XP first so DB holds updated level/XP, then merge error_distribution on a fresh snapshot.
        xp_result = gamification_engine.add_xp(user_id, xp_amount)
    stats = UserRPGStats(**db.get_rpg_stats(user_id))
    if error_type and review_data["correct_count"] < review_data["total_questions"]:
        key = str(error_type.value)
        stats.error_distribution[key] = stats.error_distribution.get(key, 0) + (
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
        increment_exercise_totals=not was_completed,
    )
    if not was_completed:
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
    user_id: str = Depends(require_demo_user_id),
):
    raw = db.get_due_srs_items(user_id, language=language)
    items = []
    for r in raw:
        data = r.get("data") if isinstance(r.get("data"), dict) else {}
        items.append(
            {
                "word": r.get("word"),
                "language": r.get("language"),
                "definition_zh": data.get("definition_zh"),
                "next_review": r.get("next_review"),
                "interval": r.get("interval"),
                "ease_factor": r.get("ease_factor"),
                "srs_level": r.get("srs_level"),
            }
        )
    return {"success": True, "items": items}


@router.post("/srs/review", response_model=dict)
async def submit_srs_review(
    word: str,
    language: str,
    quality: int = Query(ge=0, le=5),
    user_id: str = Depends(require_demo_user_id),
):
    word = str(word).strip()
    if not word:
        raise HTTPException(status_code=400, detail="Missing word")
    prev = db.get_srs_item(user_id, word, language)
    if not prev:
        raise HTTPException(status_code=404, detail="SRS item not found")

    srs_data = srs_engine.calculate(
        quality=quality,
        prev_interval=int(prev["interval"]) if prev else 0,
        prev_ease_factor=float(prev["ease_factor"]) if prev else 2.5,
        repetition=int(prev["srs_level"]) if prev else 0,
    )
    vocab_info = prev.get("data") or {}
    db.update_srs_item(user_id, word, language, srs_data, vocab_info)
    db.record_learning_activity(user_id=user_id, activity_type="srs_review")
    return {"success": True}


@router.get("/tasks")
async def get_tasks(limit: int = 10, user_id: str = Depends(require_demo_user_id)):
    return {"success": True, "tasks": db.get_generation_tasks(user_id, limit)}
