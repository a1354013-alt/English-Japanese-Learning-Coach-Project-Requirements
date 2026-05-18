"""Daily learning streak API (derived from user_learning_activity)."""

from api_errors import COMMON_ERROR_RESPONSES
from fastapi import APIRouter, Depends
from models import StreakResponse
from services.streak_service import get_streak_snapshot

from routers.deps import require_demo_user_id

router = APIRouter(prefix="/api", tags=["streak"], responses=COMMON_ERROR_RESPONSES)


@router.get("/streak", response_model=StreakResponse)
async def get_streak(user_id: str = Depends(require_demo_user_id)):
    info = get_streak_snapshot(user_id)
    # Check achievements after getting streak
    from gamification_engine import gamification_engine
    gamification_engine.check_and_unlock_achievements(user_id)
    return {"success": True, **info}
