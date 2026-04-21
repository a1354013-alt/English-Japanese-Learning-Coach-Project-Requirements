"""Root metadata, health checks, user progress, and analytics."""
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Query

from config import settings
from database import db
from ollama_client import ollama_client
from rag_manager import rag_manager

APP_VERSION = "1.2.0"

root_router = APIRouter(tags=["system"])

api_router = APIRouter(prefix="/api", tags=["system"])


@root_router.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Language Coach API",
        "version": APP_VERSION,
        "timestamp": datetime.now().isoformat(),
    }


@api_router.get("/health")
async def health_check():
    db_reachable = db.check_connection()
    ollama_small_ready = await ollama_client.check_model_availability(settings.small_model_name)
    ollama_large_ready = await ollama_client.check_model_availability(settings.large_model_name)

    return {
        "api": "healthy",
        "database": {
            "configured": bool(settings.db_path),
            "reachable": db_reachable,
            "ready": db_reachable,
        },
        "ollama": {
            "configured": bool(settings.ollama_url),
            "small_model": settings.small_model_name,
            "large_model": settings.large_model_name,
            "small_model_ready": ollama_small_ready,
            "large_model_ready": ollama_large_ready,
            "ready": ollama_small_ready or ollama_large_ready,
        },
        "rag": {
            "configured": bool(settings.chroma_db_path),
            "ready": rag_manager.enabled,
            "error": rag_manager.init_error,
        },
        "timestamp": datetime.now().isoformat(),
    }


@api_router.get("/progress", response_model=dict)
async def get_progress(user_id: str = Query(default=settings.default_user_id)):
    return {"success": True, "progress": db.get_progress(user_id)}


@api_router.get("/analytics", response_model=dict)
async def get_analytics(user_id: str = Query(default=settings.default_user_id)):
    """Get real analytics data based on actual user activity.
    
    Returns actual computed metrics, not placeholder data.
    If certain metrics cannot be reliably computed, they are omitted or marked unavailable.
    """
    # Get streak from authoritative source
    streak_info = db.get_streak_info(user_id)
    
    # Get progress data
    progress = db.get_progress(user_id)
    rpg_stats = progress.get("rpg_stats", {})
    
    # Calculate lessons completed
    english_completed = progress.get("english_progress", {}).get("completed_lessons", 0)
    japanese_completed = progress.get("japanese_progress", {}).get("completed_lessons", 0)
    total_lessons = english_completed + japanese_completed
    
    wrong_answers = db.list_wrong_answers(user_id=user_id, status="active", limit=500, offset=0)

    # Hardest prompts (by wrong_count; stable, DB-authoritative)
    hardest_words = sorted(
        [{"word": item.get("question", "Unknown"), "mistakes": int(item.get("wrong_count", 1))} for item in wrong_answers],
        key=lambda x: x["mistakes"],
        reverse=True,
    )[:5]

    # Weakest category: most active wrong answers (by count of items, not guesses)
    category_counts: Dict[str, int] = {}
    for item in wrong_answers:
        cat = str(item.get("question_type") or "general")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    weakest_category = None
    if category_counts:
        cat, count = max(category_counts.items(), key=lambda x: x[1])
        weakest_category = {"category": cat, "active_items": count}

    recent = db.list_recent_exercise_results(user_id=user_id, limit=5)
    accuracy_trend: List[Dict[str, Any]] = [
        {
            "lesson_id": r.get("lesson_id"),
            "accuracy_rate": r.get("accuracy_rate"),
            "submitted_at": r.get("submitted_at"),
        }
        for r in reversed(recent)
    ]
    
    return {
        "success": True,
        "analytics": {
            "total_xp": rpg_stats.get("total_xp", 0),
            "level": rpg_stats.get("level", 1),
            "streak": streak_info["current_streak"],
            "longest_streak": streak_info["longest_streak"],
            "lessons_completed": total_lessons,
            "hardest_words": hardest_words,
            "weakest_category": weakest_category,
            "accuracy_trend": accuracy_trend,
            "today_completed": streak_info["today_completed"],
        }
    }
