"""Daily adaptive study mission API."""

from __future__ import annotations

from typing import Any, cast

from api_errors import COMMON_ERROR_RESPONSES
from database import db
from fastapi import APIRouter, Depends, Query
from models import (
    DailyStudyMissionResponse,
    DueLearningItemCounts,
    LanguageCode,
    LearningPlan,
    SuggestedNextLesson,
    WeakLearningItemCounts,
)
from services.micro_lesson_service import build_micro_lesson, learning_plan_from_state
from services.streak_service import get_streak_snapshot

from routers.deps import require_demo_user_id

router = APIRouter(prefix="/api", tags=["study"], responses=COMMON_ERROR_RESPONSES)


@router.get("/study/today", response_model=DailyStudyMissionResponse)
async def get_today_study_mission(
    language: LanguageCode = Query(default="EN"),
    user_id: str = Depends(require_demo_user_id),
):
    diagnostic_state = db.get_diagnostic_state(user_id) if language == "EN" else None
    if diagnostic_state:
        diagnostic_state = db.advance_micro_lesson_day_if_due(user_id) or diagnostic_state
    learning_plan: LearningPlan | None = None
    micro_lesson: dict[str, Any] | None = None
    micro_status = "diagnostic_required" if language == "EN" else "unavailable"

    if diagnostic_state:
        learning_plan = learning_plan_from_state(diagnostic_state)
        micro_lesson = db.get_micro_lesson_by_day(user_id, learning_plan.current_day)
        if not micro_lesson:
            micro_lesson = build_micro_lesson(
                day_index=learning_plan.current_day,
                total_days=learning_plan.estimated_total_days,
            ).model_dump()
            db.save_micro_lesson(user_id, micro_lesson)
        micro_status = "completed" if micro_lesson.get("completed") else "available"

    due_by_type = db.count_due_learning_items_by_type(user_id=user_id, language=language)
    legacy_due = db.count_due_srs_items(user_id, language=language)
    due_counts = DueLearningItemCounts(
        vocabulary=due_by_type.get("vocabulary", 0),
        grammar=due_by_type.get("grammar", 0),
        sentence_pattern=due_by_type.get("sentence_pattern", 0),
        legacy_vocabulary=legacy_due,
    )
    due_counts.total = (
        due_counts.vocabulary
        + due_counts.grammar
        + due_counts.sentence_pattern
        + due_counts.legacy_vocabulary
    )

    grouped: dict[str, list[dict[str, Any]]] = {"vocabulary": [], "grammar": [], "sentence_pattern": []}
    for item in db.get_weak_learning_items(user_id=user_id, language=language, limit=60):
        payload = _learning_item_payload(item)
        grouped[str(item.get("item_type"))].append(payload)
    weak_counts = WeakLearningItemCounts(
        vocabulary=len(grouped["vocabulary"]),
        grammar=len(grouped["grammar"]),
        sentence_pattern=len(grouped["sentence_pattern"]),
    )

    progress = db.get_progress(user_id)
    suggested = _suggest_next_lesson(
        progress,
        grouped,
        language=language,
        diagnostic_completed=diagnostic_state is not None,
    )
    streak = get_streak_snapshot(user_id)
    today_goal = _today_goal_text(
        language=language,
        diagnostic_completed=diagnostic_state is not None,
        due_total=due_counts.total,
        weak_counts=weak_counts,
        suggested=suggested,
    )

    return {
        "success": True,
        "mission": {
            "diagnostic_completed": diagnostic_state is not None,
            "micro_lesson_status": micro_status,
            "learning_plan": learning_plan,
            "micro_lesson": micro_lesson,
            "due_counts": due_counts,
            "weak_counts": weak_counts,
            "weak_items": {"success": True, **grouped},
            "suggested_next_lesson": suggested,
            "today_goal_text": today_goal,
            "completion_summary": {
                "current_streak": streak["current_streak"],
                "longest_streak": streak["longest_streak"],
                "last_active_date": streak["last_active_date"],
                "today_completed": streak["today_completed"],
                "text": _completion_text(streak),
            },
        },
    }


def _learning_item_payload(item: dict[str, Any]) -> dict[str, Any]:
    content = cast(dict[str, Any], item.get("content")) if isinstance(item.get("content"), dict) else {}
    return {
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


def _suggest_next_lesson(
    progress: dict[str, Any],
    grouped: dict[str, list[dict[str, Any]]],
    *,
    language: LanguageCode,
    diagnostic_completed: bool,
) -> SuggestedNextLesson:
    key = "english_progress" if language == "EN" else "japanese_progress"
    selected_progress = progress.get(key, {})
    default_level = "A1" if language == "EN" else "N5"
    if language == "EN" and not diagnostic_completed:
        return SuggestedNextLesson(
            language="EN",
            level=str(selected_progress.get("current_level") or default_level),
            topic="Placement diagnostic",
        )
    if grouped["grammar"]:
        topic = f"Repair grammar: {grouped['grammar'][0]['item_key']}"
    elif grouped["sentence_pattern"]:
        topic = f"Practice pattern: {grouped['sentence_pattern'][0]['item_key']}"
    elif grouped["vocabulary"]:
        topic = f"Review vocabulary: {grouped['vocabulary'][0]['item_key']}"
    else:
        topic = (
            "Daily business English practice"
            if language == "EN"
            else "Daily Japanese practice"
        )
    return SuggestedNextLesson(
        language=language,
        level=str(selected_progress.get("current_level") or default_level),
        topic=topic,
    )


def _today_goal_text(
    *,
    language: LanguageCode,
    diagnostic_completed: bool,
    due_total: int,
    weak_counts: WeakLearningItemCounts,
    suggested: SuggestedNextLesson,
) -> str:
    if language == "EN" and not diagnostic_completed:
        return "Complete the diagnostic, then start your first micro lesson."
    weak_total = weak_counts.vocabulary + weak_counts.grammar + weak_counts.sentence_pattern
    if due_total:
        return f"Clear {due_total} due review items, then study: {suggested.topic}."
    if weak_total:
        return f"Repair {weak_total} weak learning items, then study: {suggested.topic}."
    if language == "EN":
        return f"Complete today's micro lesson and continue with: {suggested.topic}."
    return f"Continue with today's Japanese study: {suggested.topic}."


def _completion_text(streak: dict[str, Any]) -> str:
    if streak["today_completed"]:
        return f"Today is complete. Current streak: {streak['current_streak']} days."
    if streak["current_streak"]:
        return f"Keep your {streak['current_streak']}-day streak alive with one review."
    return "Start today's learning activity to begin a streak."
