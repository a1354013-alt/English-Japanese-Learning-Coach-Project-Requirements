"""Lesson generation task status semantics."""

import database as database_module
import lesson_generator as lesson_generator_module
from database import Database


class _FailingGenerator:
    async def _generate_with_model(self, **kwargs):  # pragma: no cover - called via generate_lesson
        raise RuntimeError("boom")


def test_generation_task_marks_fallback_success(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)

    gen = lesson_generator_module.LessonGenerator()
    # Force model call to fail.
    monkeypatch.setattr(gen, "_generate_with_model", _FailingGenerator()._generate_with_model, raising=True)

    # Call async method directly (no API needed).
    import asyncio

    out = asyncio.run(gen.generate_lesson(language="EN", topic="T", level="A1", interest_context=None, user_id="default_user"))
    assert out.metadata.topic.endswith("(Fallback)")

    tasks = test_db.get_generation_tasks("default_user", limit=5)
    assert tasks
    assert tasks[0]["status"] == "fallback_success"
    assert tasks[0].get("error_message")
