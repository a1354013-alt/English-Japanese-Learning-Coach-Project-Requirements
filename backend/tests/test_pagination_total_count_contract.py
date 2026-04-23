"""List APIs with limit/offset must return total count, not page length."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database as database_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.lesson_ops as lesson_ops_module
from database import Database
from routers import lessons as lessons_router
from routers import system as system_router
from routers import wrong_answers as wrong_answers_router


class _FailingModel:
    async def _generate_with_model(self, **kwargs):  # pragma: no cover
        raise RuntimeError("no model in tests")


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(lessons_router.router)
    app.include_router(wrong_answers_router.router)
    return app


def test_lessons_list_count_is_total(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))

    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(wrong_answers_router, "db", test_db, raising=False)

    gen = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(gen, "_generate_with_model", _FailingModel()._generate_with_model, raising=True)
    monkeypatch.setattr(lessons_router, "lesson_generator", gen, raising=False)

    client = TestClient(_make_app())

    for i in range(3):
        r = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": f"Topic {i}"})
        assert r.status_code == 200

    r_page = client.get("/api/lessons", params={"limit": 2, "offset": 0})
    assert r_page.status_code == 200
    body = r_page.json()
    assert body["success"] is True
    assert body["count"] == 3
    assert len(body["lessons"]) == 2


def test_wrong_answers_list_count_is_total(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))

    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(wrong_answers_router, "db", test_db, raising=False)

    uid = "default_user"
    for i in range(3):
        test_db.upsert_wrong_answer(
            user_id=uid,
            language="EN",
            question_type="grammar",
            question=f"Q{i}",
            user_answer="A",
            correct_answer="B",
            source_lesson_id=None,
        )

    client = TestClient(_make_app())
    r_page = client.get("/api/wrong-answers", params={"limit": 1, "offset": 0})
    assert r_page.status_code == 200
    body = r_page.json()
    assert body["success"] is True
    assert body["count"] == 3
    assert len(body["items"]) == 1

