"""Lesson generation prompt and fallback contract tests."""

import asyncio

import database as database_module
import lesson_generator as lesson_generator_module
from database import Database


class _InvalidStructuredOllama:
    async def generate(self, **kwargs):
        return {"success": True, "response": '{"grammar":{"exercises":[]}}'}

    @staticmethod
    def parse_json_response(_response_text):
        return {
            "vocabulary": [],
            "grammar": {
                "title": "Broken",
                "explanation": "Broken",
                "examples": [],
                "exercises": [],
            },
            "reading": {
                "title": "Broken",
                "content": "Broken",
                "word_count": 1,
                "questions": [],
            },
            "dialogue": {
                "scenario": "Broken",
                "context": "Broken",
                "dialogue": [],
                "alternatives": [],
            },
        }


def test_build_prompt_requires_json_only_and_fixed_counts():
    generator = lesson_generator_module.LessonGenerator()

    system_prompt = generator._get_system_prompt("EN")
    prompt = generator._build_prompt("EN", "A1", "Travel")

    assert "Output JSON only" in system_prompt
    assert "Do not output markdown" in system_prompt
    assert "exactly 1 grammar exercise" in prompt
    assert "exactly 1 reading question" in prompt
    assert "exactly 3 choices" in prompt
    assert "correct_answer must be one of the choices" in prompt
    normalized_prompt = prompt.lower()
    assert "requested language enum is en" in normalized_prompt
    assert "requested difficulty value is a1" in normalized_prompt


def test_generate_lesson_falls_back_when_model_json_violates_contract(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)

    generator = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(generator, "ollama", _InvalidStructuredOllama(), raising=True)

    lesson = asyncio.run(
        generator.generate_lesson(
            language="EN",
            topic="Travel",
            level="A1",
            interest_context=None,
            user_id="default_user",
        )
    )

    assert lesson.metadata.topic.endswith("(Fallback)")
    tasks = test_db.get_generation_tasks("default_user", limit=5)
    assert tasks
    assert tasks[0]["status"] == "fallback_success"
    assert "exactly one grammar exercise" in str(tasks[0]["error_message"])
