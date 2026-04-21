"""Study planner service."""
from datetime import datetime, timedelta
from typing import Any, Dict, List

from models import StudyMilestone, StudyPlan
from ollama_client import ollama_client


class StudyPlanner:
    def __init__(self) -> None:
        self.client = ollama_client

    async def generate_plan(
        self,
        user_id: str,
        target_goal: str,
        language: str,
        current_progress: Dict[str, Any],
    ) -> StudyPlan:
        result = await self.client.generate(
            prompt=self._get_plan_prompt(target_goal, language, current_progress),
            system_prompt=f"You are a study planning coach for {language}. Return strict JSON only.",
            format="json",
            timeout_profile="structured_json",
        )

        if not result.get("success"):
            return self._fallback(user_id, target_goal, language)

        parsed = self.client.parse_json_response(result.get("response", ""))
        if not isinstance(parsed, dict):
            return self._fallback(user_id, target_goal, language)

        try:
            return self._build_plan(user_id, target_goal, language, parsed)
        except Exception:
            return self._fallback(user_id, target_goal, language)

    def _build_plan(self, user_id: str, target_goal: str, language: str, data: Dict[str, Any]) -> StudyPlan:
        start = datetime.now()
        end = self._parse_datetime(data.get("end_date"), start + timedelta(days=90))

        milestones_raw = data.get("milestones") if isinstance(data.get("milestones"), list) else []
        milestones: List[StudyMilestone] = []
        for idx, item in enumerate(milestones_raw):
            if not isinstance(item, dict):
                continue
            milestones.append(
                StudyMilestone(
                    title=str(item.get("title", f"Milestone {idx + 1}")),
                    description=str(item.get("description", "")),
                    target_date=self._parse_datetime(item.get("target_date"), start + timedelta(days=30 * (idx + 1))),
                    required_skills=[str(s) for s in (item.get("required_skills") or [])],
                )
            )

        if not milestones:
            milestones = self._fallback_milestones(start)

        daily = data.get("daily_commitment_minutes", 30)
        try:
            daily_minutes = int(daily)
        except Exception:
            daily_minutes = 30

        focus = data.get("focus_areas") if isinstance(data.get("focus_areas"), list) else ["Vocabulary", "Grammar", "Review"]

        return StudyPlan(
            user_id=user_id,
            target_goal=target_goal,
            language=language,
            start_date=start,
            end_date=end,
            milestones=milestones,
            daily_commitment_minutes=max(10, min(180, daily_minutes)),
            focus_areas=[str(f) for f in focus],
        )

    def _parse_datetime(self, value: Any, fallback: datetime) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return fallback
        return fallback

    def _fallback_milestones(self, start: datetime) -> List[StudyMilestone]:
        return [
            StudyMilestone(
                title="Foundation",
                description="Build consistent daily study habits.",
                target_date=start + timedelta(days=30),
                required_skills=["Vocabulary", "Grammar"],
            ),
            StudyMilestone(
                title="Application",
                description="Practice reading and writing with feedback.",
                target_date=start + timedelta(days=60),
                required_skills=["Reading", "Writing"],
            ),
            StudyMilestone(
                title="Exam Readiness",
                description="Simulate exam tasks and close weak areas.",
                target_date=start + timedelta(days=90),
                required_skills=["Mock tests", "Error review"],
            ),
        ]

    def _fallback(self, user_id: str, target_goal: str, language: str) -> StudyPlan:
        start = datetime.now()
        return StudyPlan(
            user_id=user_id,
            target_goal=target_goal,
            language=language,
            start_date=start,
            end_date=start + timedelta(days=90),
            milestones=self._fallback_milestones(start),
            daily_commitment_minutes=30,
            focus_areas=["Vocabulary", "Grammar", "Review"],
        )

    def _get_plan_prompt(self, target_goal: str, language: str, progress: Dict[str, Any]) -> str:
        return f"""
Create a realistic study plan.
Language: {language}
Target goal: {target_goal}
Current level: {progress.get('current_level', 'Unknown')}
Completed lessons: {progress.get('completed_lessons', 0)}
Accuracy: {progress.get('accuracy_rate', 0)}

Return JSON with fields:
end_date, daily_commitment_minutes, focus_areas, milestones.
Milestones must contain: title, description, target_date, required_skills.
"""


study_planner = StudyPlanner()
