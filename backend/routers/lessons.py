"""Lesson generation, listing, detail, today's lesson, and onboarding."""
from typing import Literal, Optional

from fastapi import APIRouter, Query

from config import settings
from database import db
from gamification_engine import gamification_engine
from lesson_generator import lesson_generator
from models import GenerateLessonRequest, UserRPGStats
from services.lesson_ops import load_lesson_payload

router = APIRouter(prefix="/api", tags=["lessons"])


@router.post("/generate/lesson", response_model=dict)
async def generate_lesson(request: GenerateLessonRequest, user_id: str = Query(default=settings.default_user_id)):
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


@router.get("/lessons", response_model=dict)
async def list_lessons(
    language: Optional[Literal["EN", "JP"]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    level: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    lessons = db.query_lessons(language, start_date, end_date, level, topic, limit, offset)
    return {"success": True, "count": len(lessons), "lessons": lessons}


@router.get("/lessons/today/{language}", response_model=dict)
async def get_today_lesson(language: Literal["EN", "JP"]):
    lesson_meta = db.get_today_lesson(language)
    if not lesson_meta:
        return {"success": True, "lesson": None}
    return {"success": True, "lesson": load_lesson_payload(lesson_meta["lesson_id"])}


@router.get("/lessons/{lesson_id}", response_model=dict)
async def get_lesson(lesson_id: str):
    return {"success": True, "lesson": load_lesson_payload(lesson_id)}


@router.post("/onboard")
async def onboard_user(language: Literal["EN", "JP"], level: str, difficulty: str, user_id: str = Query(default=settings.default_user_id)):
    progress = db.get_progress(user_id)
    key = "english_progress" if language == "EN" else "japanese_progress"
    progress[key]["current_level"] = level

    stats = UserRPGStats(**db.get_rpg_stats(user_id))
    stats.is_onboarded = True
    stats.difficulty_mode = difficulty

    progress["rpg_stats"] = stats.model_dump(mode="json")
    db.save_progress(progress)
    return {"success": True}
