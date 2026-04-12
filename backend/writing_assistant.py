"""Writing assistant service."""
from typing import Any, Dict, List

from config import settings
from models import WritingAnalysis, WritingSubmission
from ollama_client import ollama_client


class WritingAssistant:
    def __init__(self) -> None:
        self.client = ollama_client

    async def analyze_writing(self, submission: WritingSubmission) -> WritingAnalysis:
        result = await self.client.generate(
            prompt=self._get_analysis_prompt(submission),
            system_prompt=self._get_system_prompt(submission.language),
            model=settings.model_name,
            format="json",
            timeout_profile="structured_json",
        )
        if not result.get("success"):
            return self._fallback(submission, reason=result.get("error", "generation_failed"))

        parsed = self.client.parse_json_response(result.get("response", ""))
        if not isinstance(parsed, dict):
            return self._fallback(submission, reason="invalid_json")

        normalized = self._normalize_payload(parsed, submission)
        try:
            return WritingAnalysis(**normalized)
        except Exception:
            return self._fallback(submission, reason="schema_validation_failed")

    def _normalize_payload(self, data: Dict[str, Any], submission: WritingSubmission) -> Dict[str, Any]:
        corrections = data.get("corrections")
        if not isinstance(corrections, list):
            corrections = []

        safe_corrections: List[Dict[str, str]] = []
        for item in corrections:
            if not isinstance(item, dict):
                continue
            safe_corrections.append(
                {
                    "original": str(item.get("original", "")),
                    "corrected": str(item.get("corrected", "")),
                    "explanation": str(item.get("explanation", "")),
                    "type": str(item.get("type", "general")),
                }
            )

        suggestions = data.get("suggestions") if isinstance(data.get("suggestions"), list) else []

        def clamp_score(key: str) -> int:
            raw = data.get(key, 0)
            try:
                value = int(raw)
            except Exception:
                value = 0
            return max(0, min(100, value))

        return {
            "original_text": submission.text,
            "corrected_text": str(data.get("corrected_text", submission.text)),
            "grammar_score": clamp_score("grammar_score"),
            "vocabulary_score": clamp_score("vocabulary_score"),
            "style_score": clamp_score("style_score"),
            "overall_score": clamp_score("overall_score"),
            "estimated_level": str(data.get("estimated_level", submission.target_level or "Unknown")),
            "corrections": safe_corrections,
            "suggestions": [str(s) for s in suggestions],
            "feedback": str(data.get("feedback", "Analysis generated with limited confidence.")),
        }

    def _fallback(self, submission: WritingSubmission, reason: str) -> WritingAnalysis:
        return WritingAnalysis(
            original_text=submission.text,
            corrected_text=submission.text,
            grammar_score=0,
            vocabulary_score=0,
            style_score=0,
            overall_score=0,
            estimated_level=submission.target_level or "Unknown",
            corrections=[],
            suggestions=["Try shorter sentences and review common patterns.", "Submit again after revision."],
            feedback=f"AI analysis fallback used: {reason}.",
        )

    def _get_system_prompt(self, language: str) -> str:
        lang_name = "English" if language == "EN" else "Japanese"
        return f"You are an expert {lang_name} writing tutor. Return strict JSON only."

    def _get_analysis_prompt(self, submission: WritingSubmission) -> str:
        return f"""
Analyze this writing and return JSON fields exactly:
corrected_text, grammar_score, vocabulary_score, style_score, overall_score,
estimated_level, corrections, suggestions, feedback.

Language: {submission.language}
Topic: {submission.topic or "General"}
Target Level: {submission.target_level or "Not specified"}
Text:
{submission.text}
"""


writing_assistant = WritingAssistant()
