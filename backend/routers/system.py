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
    
    # Get wrong answers for analysis
    try:
        wrong_answers = db.get_wrong_answers(user_id, status="active", limit=100)
        
        # Analyze word difficulties
        word_counts: Dict[str, int] = {}
        category_counts: Dict[str, int] = {}
        
        for item in wrong_answers:
            question = item.get("question", "Unknown")
            category = item.get("question_type", "general")
            
            word_counts[question] = word_counts.get(question, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Top 5 hardest words
        hardest_words = sorted(
            [{"word": k, "mistakes": v} for k, v in word_counts.items()],
            key=lambda x: x["mistakes"],
            reverse=True
        )[:5]
        
        # Weakest category (most errors)
        weakest_category = None
        if category_counts:
            max_cat = max(category_counts.items(), key=lambda x: x[1])
            weakest_category = {
                "category": max_cat[0],
                "error_count": max_cat[1],
                "accuracy": round(100 * (1 - max_cat[1] / len(wrong_answers))) if wrong_answers else 100
            }
    except Exception:
        hardest_words = []
        weakest_category = None
    
    # Accuracy trend - would need exercise_results history
    # For now, return empty array rather than fake data
    accuracy_trend: List[float] = []
    
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
            "accuracy_trend": accuracy_trend,  # Empty until exercise history is tracked properly
            "today_completed": streak_info["today_completed"],
        }
    }
