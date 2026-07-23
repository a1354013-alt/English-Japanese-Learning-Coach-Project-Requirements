"""Learning Goal and deterministic weekly insight APIs."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from api_errors import COMMON_ERROR_RESPONSES
from config import settings
from database import db
from fastapi import APIRouter, Depends, Query
from models import (
    LanguageCode,
    LearningGoalResponse,
    UpdateLearningGoalRequest,
    WeeklyLearningInsightResponse,
)

from routers.deps import require_demo_user_id

router = APIRouter(prefix="/api", tags=["learning-goals"], responses=COMMON_ERROR_RESPONSES)


def _monday_week_start(value: str | None) -> datetime:
    tz = ZoneInfo(settings.timezone)
    if value:
        parsed = datetime.fromisoformat(value)
        local_date = parsed.date()
    else:
        local_date = datetime.now(tz).date()
    monday = local_date - timedelta(days=local_date.weekday())
    return datetime.combine(monday, time.min, tzinfo=tz)


@router.get("/learning-goals", response_model=LearningGoalResponse)
async def get_learning_goal(
    language: LanguageCode = Query(...),
    user_id: str = Depends(require_demo_user_id),
):
    goal = db.get_learning_goal(user_id=user_id, language=language)
    return {"success": True, "goal": goal}


@router.put("/learning-goals", response_model=LearningGoalResponse)
async def update_learning_goal(
    request: UpdateLearningGoalRequest,
    language: LanguageCode = Query(...),
    user_id: str = Depends(require_demo_user_id),
):
    goal = db.upsert_learning_goal(
        user_id=user_id,
        language=language,
        daily_minutes=request.daily_minutes,
        weekly_sessions=request.weekly_sessions,
        weekly_minutes=request.weekly_minutes,
    )
    return {"success": True, "goal": goal}


@router.get("/learning-insights/weekly", response_model=WeeklyLearningInsightResponse)
async def get_weekly_learning_insight(
    language: LanguageCode = Query(...),
    week_start: str | None = Query(None),
    user_id: str = Depends(require_demo_user_id),
):
    start = _monday_week_start(week_start)
    end = start + timedelta(days=7)
    insight = db.get_weekly_learning_insight(
        user_id=user_id,
        language=language,
        week_start=start,
        week_end=end,
    )
    return {"success": True, "insight": insight}
