"""Daily learning streak API (derived from user_learning_activity)."""

from fastapi import APIRouter, Query

from config import settings
from database import db

router = APIRouter(prefix="/api", tags=["streak"])


@router.get("/streak", response_model=dict)
async def get_streak(user_id: str = Query(default=settings.default_user_id)):
    info = db.get_streak_info(user_id)
    # Check achievements after getting streak
    from gamification_engine import gamification_engine
    gamification_engine.check_and_unlock_achievements(user_id)
    return {"success": True, **info}

