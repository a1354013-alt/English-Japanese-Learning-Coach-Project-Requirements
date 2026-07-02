"""Core product loop integration test: lesson -> review -> progress (single-tenant demo)."""

import database as database_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.lesson_ops as lesson_ops_module
from database import Database
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import lessons as lessons_router
from routers import review as review_router
from routers import system as system_router


class _FailingModel:
    async def _generate_with_model(self, **kwargs):  # pragma: no cover - invoked via generate_lesson
        raise RuntimeError("no model in tests")


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(lessons_router.router)
    app.include_router(review_router.router)
    return app


def test_core_flow_generate_review_progress_dedup(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))

    # Patch module globals to isolate state.
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)

    # Use a generator instance that always falls back quickly (no external AI required).
    gen = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(gen, "_generate_with_model", _FailingModel()._generate_with_model, raising=True)
    monkeypatch.setattr(lessons_router, "lesson_generator", gen, raising=False)

    app = _make_app()
    client = TestClient(app)

    r_gen = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Flow Test"})
    assert r_gen.status_code == 200
    lesson = r_gen.json()["lesson"]
    lesson_id = lesson["metadata"]["lesson_id"]

    answers = []
    for idx, exercise in enumerate(lesson["grammar"]["exercises"]):
        answers.append(
            {
                "lesson_id": lesson_id,
                "exercise_type": "grammar",
                "question_index": idx,
                "user_answer": exercise["correct_answer"],
                "correct_answer": exercise["correct_answer"],
            }
        )
    for idx, question in enumerate(lesson["reading"]["questions"]):
        answers.append(
            {
                "lesson_id": lesson_id,
                "exercise_type": "reading",
                "question_index": idx,
                "user_answer": question["correct_answer"],
                "correct_answer": question["correct_answer"],
            }
        )

    r1 = client.post("/api/review", json=answers)
    assert r1.status_code == 200
    assert r1.json()["success"] is True
    assert r1.json()["gamification"]["xp_added"] > 0

    p1 = client.get("/api/progress")
    assert p1.status_code == 200
    progress1 = p1.json()["progress"]
    assert progress1["english_progress"]["completed_lessons"] == 1
    assert progress1["english_progress"]["total_exercises"] == len(answers)
    assert progress1["english_progress"]["correct_exercises"] == len(answers)

    # Re-submitting must not farm XP or progress.
    r2 = client.post("/api/review", json=answers)
    assert r2.status_code == 200
    assert r2.json()["success"] is True
    assert r2.json()["gamification"]["xp_added"] == 0

    p2 = client.get("/api/progress")
    assert p2.status_code == 200
    progress2 = p2.json()["progress"]
    assert progress2["english_progress"]["completed_lessons"] == 1
    assert progress2["english_progress"]["total_exercises"] == len(answers)
    assert progress2["english_progress"]["correct_exercises"] == len(answers)
