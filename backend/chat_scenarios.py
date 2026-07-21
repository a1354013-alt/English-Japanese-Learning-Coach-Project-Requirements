"""Canonical persisted-chat scenario catalog."""

from __future__ import annotations

from typing import Final

from models import LanguageCode

DEFAULT_SCENARIO_ID: Final[str] = "daily_conversation"

SCENARIO_DEFINITIONS: Final[tuple[dict[str, object], ...]] = (
    {
        "scenario_id": "daily_conversation",
        "language": "EN",
        "label": "Daily Conversation",
        "system_prompt": "Practice a natural everyday conversation with practical follow-up questions.",
    },
    {
        "scenario_id": "travel",
        "language": "EN",
        "label": "Travel",
        "system_prompt": "Practice travel situations such as transit, hotels, directions, and polite requests.",
    },
    {
        "scenario_id": "restaurant",
        "language": "EN",
        "label": "Restaurant",
        "system_prompt": "Practice ordering food, asking about dishes, and handling restaurant conversations.",
    },
    {
        "scenario_id": "workplace",
        "language": "EN",
        "label": "Workplace",
        "system_prompt": "Practice professional workplace conversation with clear, respectful phrasing.",
    },
    {
        "scenario_id": "daily_conversation",
        "language": "JP",
        "label": "Daily Conversation",
        "system_prompt": "Practice a natural everyday conversation with practical follow-up questions.",
    },
    {
        "scenario_id": "travel",
        "language": "JP",
        "label": "Travel",
        "system_prompt": "Practice travel situations such as transit, hotels, directions, and polite requests.",
    },
    {
        "scenario_id": "restaurant",
        "language": "JP",
        "label": "Restaurant",
        "system_prompt": "Practice ordering food, asking about dishes, and handling restaurant conversations.",
    },
    {
        "scenario_id": "workplace",
        "language": "JP",
        "label": "Workplace",
        "system_prompt": "Practice professional workplace conversation with clear, respectful phrasing.",
    },
)


def list_scenarios(language: LanguageCode) -> list[dict[str, str]]:
    return [
        {
            "scenario_id": str(item["scenario_id"]),
            "language": str(item["language"]),
            "label": str(item["label"]),
        }
        for item in SCENARIO_DEFINITIONS
        if item["language"] == language
    ]


def get_scenario(language: LanguageCode, scenario_id: str) -> dict[str, str] | None:
    normalized = scenario_id.strip()
    for item in SCENARIO_DEFINITIONS:
        if item["language"] == language and item["scenario_id"] == normalized:
            return {
                "scenario_id": str(item["scenario_id"]),
                "language": str(item["language"]),
                "label": str(item["label"]),
                "system_prompt": str(item["system_prompt"]),
            }
    return None
