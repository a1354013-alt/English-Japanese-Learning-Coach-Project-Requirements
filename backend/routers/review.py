"""Exercise review, SRS due items, and generation task history."""

import hashlib
import json
from typing import Any, List, Optional

from api_errors import COMMON_ERROR_RESPONSES, api_error
from database import db
from fastapi import APIRouter, Depends, Query
from gamification_engine import gamification_engine
from models import (
    ErrorType,
    LanguageCode,
    LearningItemDueResponse,
    LearningItemGroupResponse,
    LearningItemReviewRequest,
    LearningItemReviewState,
    LearningSessionEventMetadata,
    ReviewAnswer,
    ReviewSubmitResponse,
    SrsDueResponse,
    SrsReviewRequest,
    SuccessResponse,
    TasksResponse,
    UserRPGStats,
)
from services.learning_intelligence import apply_item_reviews_from_lesson
from services.learning_session_recorder import build_learning_session_recorder
from services.lesson_ops import (
    is_answer_correct,
    load_lesson_payload,
    score_answers,
    update_progress_after_review,
    update_srs_after_review,
)
from srs import srs_engine

from routers.deps import require_demo_user_id

router = APIRouter(prefix="/api", tags=["review"], responses=COMMON_ERROR_RESPONSES)

def _validate_review_submission(lesson_data: dict, answers: List[ReviewAnswer]) -> None:
    lesson_id = answers[0].lesson_id
    if any(a.lesson_id != lesson_id for a in answers):
        raise api_error(422, "Invalid review payload: mixed lesson_id", "review_mixed_lesson_id")
    client_submission_ids = {a.client_submission_id for a in answers if a.client_submission_id is not None}
    if len(client_submission_ids) > 1:
        raise api_error(
            422,
            "Invalid review payload: mixed client_submission_id",
            "review_mixed_client_submission_id",
        )

    grammar_exercises = lesson_data.get("grammar", {}).get("exercises", []) or []
    reading_questions = lesson_data.get("reading", {}).get("questions", []) or []
    expected_keys = {
        ("grammar", idx) for idx in range(len(grammar_exercises))
    } | {
        ("reading", idx) for idx in range(len(reading_questions))
    }

    seen: set[tuple[str, int]] = set()
    for a in answers:
        # Disallow blank answers (avoid polluted wrong-answer notebook/analytics).
        if str(a.user_answer).strip() == "":
            raise api_error(422, "Invalid review payload: user_answer must be non-empty", "review_blank_user_answer")

        key = (a.exercise_type, a.question_index)
        if key in seen:
            raise api_error(422, f"Invalid review payload: duplicate answer for {a.exercise_type}[{a.question_index}]", "review_duplicate_answer")
        seen.add(key)

        if a.question_index < 0:
            raise api_error(422, "Invalid review payload: question_index must be >= 0", "review_negative_question_index")

        if a.exercise_type == "grammar":
            if a.question_index >= len(grammar_exercises):
                raise api_error(422, "Invalid review payload: grammar question_index out of range", "review_grammar_index_out_of_range")
            expected = str((grammar_exercises[a.question_index] or {}).get("correct_answer", ""))
        else:
            if a.question_index >= len(reading_questions):
                raise api_error(422, "Invalid review payload: reading question_index out of range", "review_reading_index_out_of_range")
            expected = str((reading_questions[a.question_index] or {}).get("correct_answer", ""))

        if str(a.correct_answer).strip() != expected.strip():
            raise api_error(422, "Invalid review payload: correct_answer mismatch", "review_correct_answer_mismatch")

    missing = sorted(expected_keys - seen)
    if missing:
        missing_labels = ", ".join(f"{exercise_type}[{question_index}]" for exercise_type, question_index in missing)
        raise api_error(
            422,
            f"Invalid review payload: missing answers for {missing_labels}",
            "review_answers_incomplete",
        )


def _review_request_hash(answers: List[ReviewAnswer]) -> str:
    payload = [
        {
            "lesson_id": answer.lesson_id,
            "exercise_type": answer.exercise_type,
            "question_index": answer.question_index,
            "user_answer": answer.user_answer,
            "correct_answer": answer.correct_answer,
        }
        for answer in sorted(answers, key=lambda item: (item.exercise_type, item.question_index))
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _srs_request_hash(*, word: str, language: str, quality: int) -> str:
    encoded = json.dumps(
        {"word": word, "language": language, "quality": quality},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@router.post("/review", response_model=ReviewSubmitResponse)
async def submit_review(
    answers: List[ReviewAnswer],
    user_id: str = Depends(require_demo_user_id),
    error_type: ErrorType | None = Query(default=None),
):
    if not answers:
        raise api_error(422, "No answers provided", "review_answers_required")

    lesson_id = answers[0].lesson_id
    lesson_data = load_lesson_payload(lesson_id, user_id=user_id)
    _validate_review_submission(lesson_data, answers)
    review_data = score_answers(lesson_data, answers)
    client_submission_id = next((a.client_submission_id for a in answers if a.client_submission_id is not None), None)
    try:
        submission = db.get_or_create_review_submission(
            user_id=user_id,
            lesson_id=lesson_id,
            client_submission_id=client_submission_id,
            request_hash=_review_request_hash(answers),
            total_questions=review_data["total_questions"],
            correct_count=review_data["correct_count"],
            accuracy_rate=review_data["accuracy_rate"],
        )
    except ValueError:
        raise api_error(
            409,
            "Review submission idempotency conflict",
            "review_submission_idempotency_conflict",
        ) from None
    review_submission_id = str(submission["submission_id"])
    previous_result = db.get_exercise_result(user_id=user_id, lesson_id=lesson_id, exercise_type="mixed")
    was_completed = previous_result is not None

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

    # Demo rule: XP and completed lesson count are awarded only once per lesson.
    # Re-submitting updates the latest exercise_result, improves progress when it
    # beats the prior best score, and refreshes SRS from the latest attempt.
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
        previous_best_correct=int(previous_result["correct_count"]) if previous_result else None,
    )
    item_review_updates = apply_item_reviews_from_lesson(
        user_id=user_id,
        lesson_data=lesson_data,
        answer_checks=[
            (a.exercise_type, a.question_index, is_answer_correct(a.user_answer, (
                lesson_data.get("grammar", {}).get("exercises", [])[a.question_index]
                if a.exercise_type == "grammar"
                else lesson_data.get("reading", {}).get("questions", [])[a.question_index]
            )))
            for a in answers
        ],
    )
    if item_review_updates == 0:
        update_srs_after_review(user_id, language, lesson_data, review_data["accuracy_rate"])

    # Wrong Answer Notebook: persist each incorrect answer with dedupe/upsert.
    answer_map = {(a.exercise_type, a.question_index): a for a in answers}
    grammar_exercises = lesson_data.get("grammar", {}).get("exercises", [])
    for idx, exercise in enumerate(grammar_exercises):
        submitted = answer_map.get(("grammar", idx))
        user_answer = str(submitted.user_answer) if submitted is not None else "(no answer)"
        correct_answer = str(exercise.get("correct_answer", ""))
        if is_answer_correct(user_answer, exercise):
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
        correct_answer = str(question.get("correct_answer", ""))
        if is_answer_correct(user_answer, question):
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

    recorder = build_learning_session_recorder(db)
    for answer in answers:
        event_id = f"{review_submission_id}:{answer.exercise_type}:{answer.question_index}"
        recorder.record_event(
            user_id=user_id,
            language=language,
            event_type="review_answered",
            entity_type="review",
            entity_id=event_id,
            idempotency_key=f"review-answered:{event_id}",
            metadata=LearningSessionEventMetadata(
                correct=is_answer_correct(
                    answer.user_answer,
                    (
                        lesson_data.get("grammar", {}).get("exercises", [])[answer.question_index]
                        if answer.exercise_type == "grammar"
                        else lesson_data.get("reading", {}).get("questions", [])[answer.question_index]
                    ),
                ),
                result_category=answer.exercise_type,
            ),
        )

    if not was_completed:
        recorder.record_event(
            user_id=user_id,
            language=language,
            event_type="lesson_completed",
            entity_type="lesson",
            entity_id=lesson_id,
            idempotency_key=f"lesson-completed:{lesson_id}",
            metadata=LearningSessionEventMetadata(
                completion_outcome="review_submitted",
            ),
        )

    return {
        "success": True,
        **review_data,
        "gamification": {"xp_added": xp_amount, "leveled_up": xp_result.get("leveled_up")},
    }


@router.get("/srs/due", response_model=SrsDueResponse)
async def get_due_items(
    language: Optional[LanguageCode] = None,
    user_id: str = Depends(require_demo_user_id),
):
    raw = db.get_due_srs_items(user_id, language=language)
    items = []
    for r in raw:
        data_value = r.get("data")
        data: dict[str, object] = data_value if isinstance(data_value, dict) else {}
        items.append(
            {
                "word": r.get("word"),
                "language": r.get("language"),
                "definition_zh": data.get("definition_zh"),
                "category": data.get("category"),
                "tags": data.get("tags") if isinstance(data.get("tags"), list) else [],
                "memory_tip": data.get("memory_tip"),
                "root": data.get("root"),
                "next_review": r.get("next_review"),
                "interval": r.get("interval"),
                "ease_factor": r.get("ease_factor"),
                "srs_level": r.get("srs_level"),
            }
        )
    return {"success": True, "items": items}


@router.post("/srs/review", response_model=SuccessResponse)
async def submit_srs_review(
    request: SrsReviewRequest,
    user_id: str = Depends(require_demo_user_id),
):
    word = str(request.word).strip()
    if not word:
        raise api_error(400, "Missing word", "srs_word_required")
    prev = db.get_srs_item(user_id, word, request.language)
    if not prev:
        raise api_error(404, "SRS item not found", "srs_item_not_found")
    try:
        operation = db.get_or_create_legacy_srs_review_operation(
            user_id=user_id,
            word=word,
            language=request.language,
            quality=request.quality,
            client_operation_id=request.client_operation_id,
            request_hash=_srs_request_hash(word=word, language=request.language, quality=request.quality),
        )
    except ValueError:
        raise api_error(
            409,
            "SRS review idempotency conflict",
            "srs_review_idempotency_conflict",
        ) from None
    if operation["is_retry"]:
        db.record_learning_activity(user_id=user_id, activity_type="srs_review")
        return {"success": True}

    srs_data = srs_engine.calculate(
        quality=request.quality,
        prev_interval=int(prev["interval"]) if prev else 0,
        prev_ease_factor=float(prev["ease_factor"]) if prev else 2.5,
        repetition=int(prev["srs_level"]) if prev else 0,
    )
    vocab_info = prev["data"] if isinstance(prev.get("data"), dict) else {}
    if not operation["is_retry"]:
        db.update_srs_item(user_id, word, request.language, srs_data, vocab_info)
    db.record_learning_activity(user_id=user_id, activity_type="srs_review")
    build_learning_session_recorder(db).record_event(
        user_id=user_id,
        language=request.language,
        event_type="srs_reviewed",
        entity_type="srs_item",
        entity_id=f"legacy:{word}",
        idempotency_key=f"srs-reviewed:{operation['operation_id']}",
        metadata=LearningSessionEventMetadata(
            correct=request.quality >= 3,
            rating=request.quality,
            interval_days=int(srs_data["interval"]),
            result_category="legacy_vocabulary",
        ),
    )
    return {"success": True}


@router.get("/srs/items/due", response_model=LearningItemDueResponse)
async def get_due_learning_items(
    language: Optional[LanguageCode] = None,
    item_type: Optional[str] = Query(default=None),
    user_id: str = Depends(require_demo_user_id),
):
    raw_items = db.list_due_learning_items(
        user_id=user_id,
        language=language,
        item_type=item_type,
    )
    items: List[dict[str, Any]] = []
    for item in raw_items:
        raw_content = item.get("content")
        content: dict[str, Any] = raw_content if isinstance(raw_content, dict) else {}
        items.append(
            {
                "item_id": item.get("id"),
                "item_type": item.get("item_type"),
                "item_key": item.get("item_key"),
                "language": item.get("language"),
                "level": item.get("level"),
                "content": content,
                "category": item.get("category") or content.get("category"),
                "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
                "root": content.get("root"),
                "memory_tip": content.get("memory_tip"),
                "mastery_state": item.get("mastery_state"),
                "due_at": item.get("due_at"),
            }
        )
    return {"success": True, "items": items}


@router.post("/srs/items/review", response_model=LearningItemReviewState)
async def submit_learning_item_review(
    request: LearningItemReviewRequest,
    user_id: str = Depends(require_demo_user_id),
):
    try:
        updated = db.record_learning_item_review(
            user_id=user_id,
            item_id=request.item_id,
            rating=request.rating,
            response_time_ms=request.response_time_ms,
            source=request.source,
        )
    except ValueError:
        raise api_error(404, "Learning item not found", "learning_item_not_found") from None
    build_learning_session_recorder(db).record_event(
        user_id=user_id,
        language=str(updated.get("language") or ""),
        event_type="srs_reviewed",
        entity_type="srs_item",
        entity_id=str(updated.get("item_id") or request.item_id),
        idempotency_key=f"srs-reviewed:{updated.get('review_event_id')}",
        metadata=LearningSessionEventMetadata(
            correct=bool(updated.get("review_correct")),
            rating=request.rating,
            interval_days=int(updated.get("interval_days") or 0),
            result_category=str(updated.get("mastery_state") or ""),
            response_time_ms=request.response_time_ms,
        ),
    )
    return {
        "success": True,
        "item_id": updated.get("id"),
        "interval_days": updated.get("interval_days"),
        "ease_factor": updated.get("ease_factor"),
        "repetitions": updated.get("repetitions"),
        "lapses": updated.get("lapses"),
        "due_at": updated.get("due_at"),
        "last_reviewed_at": updated.get("last_reviewed_at"),
        "mastery_state": updated.get("mastery_state"),
    }


@router.get("/srs/items/weak", response_model=LearningItemGroupResponse)
async def get_weak_learning_items(
    language: Optional[LanguageCode] = None,
    user_id: str = Depends(require_demo_user_id),
):
    grouped: dict[str, List[dict[str, Any]]] = {
        "vocabulary": [],
        "grammar": [],
        "sentence_pattern": [],
    }
    for item in db.get_weak_learning_items(user_id=user_id, language=language, limit=60):
        raw_content = item.get("content")
        content: dict[str, Any] = raw_content if isinstance(raw_content, dict) else {}
        payload: dict[str, Any] = {
            "item_id": item.get("id"),
            "item_type": item.get("item_type"),
            "item_key": item.get("item_key"),
            "language": item.get("language"),
            "level": item.get("level"),
            "content": content,
            "category": item.get("category") or content.get("category"),
            "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
            "root": content.get("root"),
            "memory_tip": content.get("memory_tip"),
            "mastery_state": item.get("mastery_state"),
            "due_at": item.get("due_at"),
        }
        grouped[str(item.get("item_type"))].append(payload)
    return {"success": True, **grouped}


@router.get("/tasks", response_model=TasksResponse)
async def get_tasks(limit: int = 10, user_id: str = Depends(require_demo_user_id)):
    return {"success": True, "tasks": db.get_generation_tasks(user_id, limit)}
