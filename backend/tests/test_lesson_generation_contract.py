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
    assert "at least 3 grammar exercises" in prompt
    assert "at least 3 reading comprehension questions" in prompt
    assert "objectives, vocabulary, word_roots, sentence_patterns" in prompt
    assert "immersion, feynman_prompt, review_plan" in prompt
    assert "at least 8 items" in prompt
    assert "at least 3 roots" in prompt
    assert "exactly 3 choices" in prompt
    assert "correct_answer must be one of the choices" in prompt
    assert "Every grammar exercise must include related_vocabulary" in prompt
    assert "Every reading question must include related_vocabulary" in prompt
    normalized_prompt = prompt.lower()
    assert "requested language enum is en" in normalized_prompt
    assert "requested difficulty value is a1" in normalized_prompt


def test_normalized_lesson_items_get_related_refs_when_possible():
    generator = lesson_generator_module.LessonGenerator()
    content = {
        "objectives": ["One", "Two", "Three"],
        "vocabulary": [
            {"word": "invoice", "definition_zh": "發票", "example_sentence": "The invoice is ready.", "example_translation": "發票好了。"}
        ]
        * 8,
        "word_roots": [
            {"root": "in-", "meaning_zh": "in", "examples": ["invoice"], "memory_tip": "inside"},
            {"root": "voice", "meaning_zh": "voice", "examples": ["invoice"], "memory_tip": "sound"},
            {"root": "-tion", "meaning_zh": "noun", "examples": ["action"], "memory_tip": "noun"},
        ],
        "sentence_patterns": [
            {"pattern": "The invoice is ...", "meaning_zh": "發票...", "usage_note": "status", "examples": []},
            {"pattern": "Please confirm ...", "meaning_zh": "請確認", "usage_note": "email", "examples": []},
            {"pattern": "I need ...", "meaning_zh": "我需要", "usage_note": "request", "examples": []},
        ],
        "grammar": {
            "title": "Be Verb",
            "explanation": "Use be for status.",
            "examples": [],
            "exercises": [
                {
                    "question": "The invoice ___ ready.",
                    "options": ["is", "are", "be"],
                    "correct_answer": "is",
                    "explanation": "Use is.",
                    "related_vocabulary": [],
                    "related_grammar": [],
                    "related_sentence_patterns": [],
                }
            ]
            * 3,
        },
        "reading": {
            "title": "Invoice",
            "content": "The invoice is ready. Please confirm it today.",
            "word_count": 8,
            "questions": [
                {
                    "question": "What is ready?",
                    "options": ["invoice", "room", "phone"],
                    "correct_answer": "invoice",
                    "explanation": "The invoice is ready.",
                }
            ]
            * 3,
        },
        "dialogue": {
            "scenario": "Office",
            "context": "Email",
            "dialogue": [{"speaker": "A", "text": "The invoice is ready.", "translation": "發票好了。"}] * 6,
            "alternatives": [],
        },
    }

    generator._normalize(content)
    generator._attach_related_item_refs(content)
    generator._validate_generated_content(content)

    for item in content["grammar"]["exercises"] + content["reading"]["questions"]:
        assert item["related_vocabulary"]
        assert item["related_grammar"]
        assert item["related_sentence_patterns"]


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
    assert "at least three objectives" in str(tasks[0]["error_message"])
