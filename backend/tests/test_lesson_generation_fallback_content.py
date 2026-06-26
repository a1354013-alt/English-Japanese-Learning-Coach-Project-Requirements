"""Fallback lesson content should stay readable for demo-safe degraded mode."""

import asyncio

import database as database_module
import lesson_generator as lesson_generator_module
from database import Database


class _FailingGenerator:
    async def _generate_with_model(self, **kwargs):  # pragma: no cover - called via generate_lesson
        raise RuntimeError("boom")


def test_fallback_lesson_english_and_japanese_content_is_readable(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)

    generator = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(
        generator,
        "_generate_with_model",
        _FailingGenerator()._generate_with_model,
        raising=True,
    )

    english = asyncio.run(
        generator.generate_lesson(
            language="EN",
            topic="Daily Habits",
            level="A1",
            interest_context=None,
            user_id="default_user",
        )
    )
    japanese = asyncio.run(
        generator.generate_lesson(
            language="JP",
            topic="Daily Habits",
            level="N5",
            interest_context=None,
            user_id="default_user",
        )
    )

    assert english.metadata.topic.endswith("(Fallback)")
    assert english.vocabulary[0].word == "resilience"
    assert english.vocabulary[0].definition_zh
    assert english.reading.content == "Study a little every day to build confidence."

    assert japanese.metadata.topic.endswith("(Fallback)")
    assert japanese.vocabulary[0].word
    assert japanese.vocabulary[0].reading
    assert japanese.vocabulary[0].definition_zh
    assert japanese.reading.content
