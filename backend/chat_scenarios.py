"""Canonical persisted-chat scenario catalog."""

from __future__ import annotations

from typing import Final

from models import LanguageCode

DEFAULT_SCENARIO_ID: Final[str] = "daily-conversation"

SCENARIO_DEFINITIONS: Final[tuple[dict[str, object], ...]] = (
    {
        "scenario_id": "daily-conversation",
        "language": "EN",
        "label": "Daily Conversation",
        "system_prompt": "Practice a natural everyday conversation in English.",
    },
    {
        "scenario_id": "travel",
        "language": "EN",
        "label": "Travel",
        "system_prompt": "Practice useful English for travel situations like transit, hotels, and sightseeing.",
    },
    {
        "scenario_id": "restaurant",
        "language": "EN",
        "label": "Restaurant",
        "system_prompt": "Practice ordering food, asking questions, and handling restaurant situations in English.",
    },
    {
        "scenario_id": "workplace",
        "language": "EN",
        "label": "Workplace",
        "system_prompt": "Practice practical English for meetings, updates, collaboration, and workplace conversations.",
    },
    {
        "scenario_id": "daily-conversation",
        "language": "JP",
        "label": "Daily Conversation",
        "system_prompt": "Practice a natural everyday conversation in Japanese.",
    },
    {
        "scenario_id": "travel",
        "language": "JP",
        "label": "Travel",
        "system_prompt": "Practice useful Japanese for travel situations like transit, hotels, and sightseeing.",
    },
    {
        "scenario_id": "restaurant",
        "language": "JP",
        "label": "Restaurant",
        "system_prompt": "Practice ordering food, asking questions, and handling restaurant situations in Japanese.",
    },
    {
        "scenario_id": "workplace",
        "language": "JP",
        "label": "Workplace",
        "system_prompt": "Practice practical Japanese for meetings, updates, collaboration, and workplace conversations.",
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
