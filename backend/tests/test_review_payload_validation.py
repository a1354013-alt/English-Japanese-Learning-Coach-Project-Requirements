"""Review API must validate payload boundaries and return clear 4xx errors."""

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
    async def _generate_with_model(self, **kwargs):  # pragma: no cover
        raise RuntimeError("no model in tests")


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(lessons_router.router)
    app.include_router(review_router.router)
    return app


def _setup_isolated_app(tmp_path, monkeypatch) -> TestClient:
    test_db = Database(str(tmp_path / "t.db"))

    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)

    gen = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(gen, "_generate_with_model", _FailingModel()._generate_with_model, raising=True)
    monkeypatch.setattr(lessons_router, "lesson_generator", gen, raising=False)

    return TestClient(_make_app())


def _full_valid_answers(lesson: dict, *, lesson_id: str | None = None) -> list[dict]:
    current_lesson_id = lesson_id or lesson["metadata"]["lesson_id"]
    return [
        {
            "lesson_id": current_lesson_id,
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": lesson["grammar"]["exercises"][0]["correct_answer"],
            "correct_answer": lesson["grammar"]["exercises"][0]["correct_answer"],
        },
        {
            "lesson_id": current_lesson_id,
            "exercise_type": "reading",
            "question_index": 0,
            "user_answer": lesson["reading"]["questions"][0]["correct_answer"],
            "correct_answer": lesson["reading"]["questions"][0]["correct_answer"],
        },
    ]


def test_review_rejects_mixed_lesson_id(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    r_gen = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Validation"})
    lesson = r_gen.json()["lesson"]
    answers = _full_valid_answers(lesson)
    answers[1]["lesson_id"] = "different"

    r = client.post("/api/review", json=answers)
    assert r.status_code == 422
    assert "mixed lesson_id" in r.json()["detail"]


def test_review_rejects_duplicate_answers(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Dup"}).json()["lesson"]
    answers = _full_valid_answers(lesson)
    answers[1] = dict(answers[0])

    r = client.post("/api/review", json=answers)
    assert r.status_code == 422
    assert "duplicate answer" in r.json()["detail"]


def test_review_rejects_out_of_range_indexes(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Range"}).json()["lesson"]
    answers = _full_valid_answers(lesson)
    answers[0]["question_index"] = 999
    answers[0]["user_answer"] = "A"
    answers[0]["correct_answer"] = "B"

    r = client.post("/api/review", json=answers)
    assert r.status_code == 422
    assert "out of range" in r.json()["detail"]


def test_review_rejects_correct_answer_mismatch(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Mismatch"}).json()["lesson"]
    answers = _full_valid_answers(lesson)
    answers[0]["correct_answer"] = "tampered"

    r = client.post("/api/review", json=answers)
    assert r.status_code == 422
    assert "correct_answer mismatch" in r.json()["detail"]


def test_review_rejects_blank_user_answer(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Blank"}).json()["lesson"]
    answers = _full_valid_answers(lesson)
    answers[0]["user_answer"] = "   "

    r = client.post("/api/review", json=answers)
    assert r.status_code == 422
    assert "user_answer must be non-empty" in r.json()["detail"]


def test_review_rejects_incomplete_payload_when_reading_answer_is_missing(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    lesson = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Incomplete"}).json()["lesson"]
    answers = _full_valid_answers(lesson)[:1]

    r = client.post("/api/review", json=answers)
    assert r.status_code == 422
    assert "missing answers for reading[0]" in r.json()["detail"]


def test_review_rejects_empty_answer_list(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)
    r = client.post("/api/review", json=[])
    assert r.status_code == 422
    assert "No answers provided" in r.json()["detail"]


def test_srs_endpoints_reject_invalid_language(tmp_path, monkeypatch):
    client = _setup_isolated_app(tmp_path, monkeypatch)

    due_response = client.get("/api/srs/due", params={"language": "FR"})
    assert due_response.status_code == 422

    review_response = client.post(
        "/api/srs/review",
        json={"word": "hello", "language": "FR", "quality": 3},
    )
    assert review_response.status_code == 422
