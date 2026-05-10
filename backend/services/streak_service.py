"""Shared streak helpers so progress, analytics, and the streak API stay aligned."""

from __future__ import annotations

from typing import Any, Dict

import database as database_module
from models import UserRPGStats


def get_streak_snapshot(user_id: str) -> Dict[str, Any]:
    """Return the canonical streak payload and mirror the current streak into RPG stats."""
    streak = database_module.db.get_streak_info(user_id)
    stats = UserRPGStats(**database_module.db.get_rpg_stats(user_id))
    if stats.streak_days != streak["current_streak"]:
        stats.streak_days = streak["current_streak"]
        database_module.db.save_rpg_stats(user_id, stats.model_dump(mode="json"))
    return streak
