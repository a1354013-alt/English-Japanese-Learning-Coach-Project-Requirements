"""Lesson generation, listing, detail, today's lesson, and onboarding."""
from typing import Optional

from api_errors import COMMON_ERROR_RESPONSES
from database import db
from fastapi import APIRouter, Depends, Query
from gamification_engine import gamification_engine
from lesson_generator import lesson_generator
from models import (
    FeynmanFeedbackRequest,
    FeynmanFeedbackResponse,
    GeneratedLessonResponse,
    GenerateLessonRequest,
    LanguageCode,
    LessonDetailResponse,
    LessonListResponse,
    LessonStartRequest,
    OnboardRequest,
    SuccessResponse,
    TodayLessonResponse,
    UserRPGStats,
)
from services.learning_intelligence import generate_feynman_feedback
from services.learning_session_recorder import build_learning_session_recorder
from services.lesson_ops import load_lesson_payload

from routers.deps import require_demo_user_id

router = APIRouter(prefix="/api", tags=["lessons"], responses=COMMON_ERROR_RESPONSES)


@router.post("/generate/lesson", response_model=GeneratedLessonResponse)
async def generate_lesson(request: GenerateLessonRequest, user_id: str = Depends(require_demo_user_id)):
    # Pass user_id to lesson generator for proper user scoping
    lesson = await lesson_generator.generate_lesson(
        language=request.language,
        topic=request.topic,
        level=request.difficulty,
        interest_context=request.interest_context,
        user_id=user_id,  # Properly pass user_id through
    )

    xp_result = gamification_engine.add_xp(user_id, 50)
    db.record_learning_activity(user_id=user_id, activity_type="generate_lesson")

    words = [item.word for item in lesson.vocabulary]
    new_cards = gamification_engine.collect_word_cards(user_id, words, request.language)

    lesson_dict = lesson.model_dump(mode="json")
    lesson_dict["gamification"] = {
        "xp_added": 50,
        "leveled_up": xp_result.get("leveled_up"),
        "new_cards": [card.model_dump(mode="json") for card in new_cards],
    }

    return {"success": True, "lesson": lesson_dict}


@router.get("/lessons", response_model=LessonListResponse)
async def list_lessons(
    language: Optional[LanguageCode] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    level: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(require_demo_user_id),
):
    lessons, total = db.query_lessons(user_id, language, start_date, end_date, level, topic, limit, offset)
    return {"success": True, "count": total, "lessons": lessons}


@router.get("/lessons/today/{language}", response_model=TodayLessonResponse)
async def get_today_lesson(language: LanguageCode, user_id: str = Depends(require_demo_user_id)):
    lesson_meta = db.get_today_lesson(user_id, language)
    if not lesson_meta:
        return {"success": True, "lesson": None}
    return {"success": True, "lesson": load_lesson_payload(lesson_meta["lesson_id"], user_id=user_id)}


@router.get("/lessons/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(lesson_id: str, user_id: str = Depends(require_demo_user_id)):
    return {"success": True, "lesson": load_lesson_payload(lesson_id, user_id=user_id)}


@router.post("/lessons/{lesson_id}/start", response_model=SuccessResponse)
async def start_lesson(
    lesson_id: str,
    request: LessonStartRequest | None = None,
    user_id: str = Depends(require_demo_user_id),
):
    lesson_data = load_lesson_payload(lesson_id, user_id=user_id)
    language = str(lesson_data.get("metadata", {}).get("language", "")).strip()
    idempotency_key = (
        request.idempotency_key.strip()
        if request is not None and request.idempotency_key is not None
        else f"lesson-started:{lesson_id}"
    )
    build_learning_session_recorder(db).record_event(
        user_id=user_id,
        language=language,
        event_type="lesson_started",
        entity_type="lesson",
        entity_id=lesson_id,
        idempotency_key=idempotency_key,
    )
    return {"success": True}


@router.post("/lessons/{lesson_id}/feynman-feedback", response_model=FeynmanFeedbackResponse)
async def create_feynman_feedback(
    lesson_id: str,
    request: FeynmanFeedbackRequest,
    user_id: str = Depends(require_demo_user_id),
):
    lesson_data = load_lesson_payload(lesson_id, user_id=user_id)
    lesson_language = str(lesson_data.get("metadata", {}).get("language", "")).strip()
    if lesson_language != request.language:
        from api_errors import api_error

        raise api_error(422, "Lesson language does not match request language", "lesson_language_mismatch")
    feedback, feedback_id = await generate_feynman_feedback(
        user_id=user_id,
        lesson_id=lesson_id,
        language=request.language,
        explanation=request.explanation,
        lesson_data=lesson_data,
    )
    build_learning_session_recorder(db).record_event(
        user_id=user_id,
        language=request.language,
        event_type="feynman_completed",
        entity_type="feynman_response",
        entity_id=feedback_id,
        idempotency_key=f"feynman-completed:{feedback_id}",
    )
    return {"success": True, "feedback": feedback.model_dump(mode="json")}


@router.post("/onboard", response_model=SuccessResponse)
async def onboard_user(
    request: OnboardRequest,
    user_id: str = Depends(require_demo_user_id),
):
    progress = db.get_progress(user_id)
    key = "english_progress" if request.language == "EN" else "japanese_progress"
    progress[key]["current_level"] = request.level

    stats = UserRPGStats(**db.get_rpg_stats(user_id))
    stats.is_onboarded = True
    stats.difficulty_mode = request.difficulty

    progress["rpg_stats"] = stats.model_dump(mode="json")
    db.save_progress(progress)
    return {"success": True}
