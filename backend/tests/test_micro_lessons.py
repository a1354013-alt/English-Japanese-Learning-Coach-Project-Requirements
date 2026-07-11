import database as database_module
import gamification_engine as gamification_module
import routers.micro_lessons as micro_lessons_router
import services.streak_service as streak_service_module
from api_errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from database import Database
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from routers import micro_lessons
from routers.micro_lessons import DIAGNOSTIC_QUESTIONS
from services.micro_lesson_service import build_micro_lesson


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(micro_lessons.router)
    return app


def _client(tmp_path, monkeypatch) -> TestClient:
    test_db = Database(str(tmp_path / "micro.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(micro_lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(streak_service_module.database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    return TestClient(_make_app())


def _submit_diagnostic(client: TestClient) -> dict:
    questions = client.get("/api/diagnostic/questions").json()["questions"]
    correct_answers = {
        question.question_id: question.correct_answer for question in DIAGNOSTIC_QUESTIONS
    }
    answers = [{"question_id": item["question_id"], "answer": correct_answers[item["question_id"]]} for item in questions]
    response = client.post("/api/diagnostic/submit", json={"answers": answers})
    assert response.status_code == 200
    return response.json()["learning_plan"]


def test_diagnostic_questions_contract(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/diagnostic/questions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert 3 <= len(body["questions"]) <= 5
    for question in body["questions"]:
        assert {"question_id", "prompt", "choices", "skill"} <= set(question)
        assert "correct_answer" not in question
        assert question["skill"] in {"subject", "verb", "present_simple"}


def test_diagnostic_submit_rejects_partial_submissions(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/diagnostic/submit",
        json={"answers": [{"question_id": "subject-1", "answer": "The manager"}]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "diagnostic_answers_incomplete"


def test_diagnostic_submit_rejects_duplicate_and_unknown_question_ids(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    duplicate = client.post(
        "/api/diagnostic/submit",
        json={
            "answers": [
                {"question_id": "subject-1", "answer": "The manager"},
                {"question_id": "subject-1", "answer": "The manager"},
                {"question_id": "verb-1", "answer": "raise"},
                {"question_id": "present-1", "answer": "She works today."},
                {"question_id": "subject-2", "answer": "Customers"},
            ]
        },
    )
    assert duplicate.status_code == 422
    assert duplicate.json()["code"] == "diagnostic_question_id_duplicate"

    unknown = client.post(
        "/api/diagnostic/submit",
        json={
            "answers": [
                {"question_id": "subject-1", "answer": "The manager"},
                {"question_id": "verb-1", "answer": "raise"},
                {"question_id": "present-1", "answer": "She works today."},
                {"question_id": "subject-2", "answer": "Customers"},
                {"question_id": "unknown-1", "answer": "??"},
            ]
        },
    )
    assert unknown.status_code == 422
    assert unknown.json()["code"] == "diagnostic_question_id_unknown"


def test_diagnostic_submit_returns_learning_plan(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    plan = _submit_diagnostic(client)

    assert plan == {
        "estimated_total_days": 90,
        "current_day": 1,
        "summary_zh": "Placement complete: start a 90-day TOEIC 600 micro lesson plan.",
    }


def test_micro_lesson_schema_contains_required_fields(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)

    response = client.get("/api/micro-lessons/today")

    assert response.status_code == 200
    lesson = response.json()["lesson"]
    assert {
        "day_index",
        "total_days",
        "target_exam",
        "sentence",
        "translation_zh",
        "subject_text",
        "verb_text",
        "object_text",
        "reading_order_steps",
        "grammar_note",
        "toeic_usage_note",
        "vocabulary_items",
        "dialogue_lines",
        "reading_passage",
        "comic_panels",
        "fill_blank_question",
        "completed",
    } <= set(lesson)


def test_micro_lesson_template_bank_changes_by_current_day(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)

    day_one = client.get("/api/micro-lessons/today").json()["lesson"]
    micro_lessons_router.db.save_diagnostic_state(
        user_id="default_user",
        estimated_total_days=90,
        current_day=2,
        summary_zh="day two",
        correct_count=4,
    )
    day_two = client.get("/api/micro-lessons/today").json()["lesson"]

    assert day_one["sentence"] != day_two["sentence"]
    assert day_two["day_index"] == 2
    assert {"lesson_id", "sentence", "fill_blank_question", "vocabulary_items"} <= set(day_two)


def test_micro_lesson_template_bank_has_at_least_seven_stable_day_templates():
    lessons = [build_micro_lesson(day_index=day, total_days=90) for day in range(1, 8)]

    assert len({lesson.sentence for lesson in lessons}) == 7
    assert lessons[0].sentence == "We raise prices today."
    assert lessons[-1].sentence == "We review one sentence again."


def test_micro_lesson_generation_is_deterministic_without_live_llm():
    first = build_micro_lesson(day_index=3, total_days=90)
    second = build_micro_lesson(day_index=3, total_days=90)

    assert first.sentence == second.sentence
    assert first.fill_blank_question.correct_answer == second.fill_blank_question.correct_answer


def test_micro_lesson_sentence_and_vocabulary_bounds(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)

    lesson = client.get("/api/micro-lessons/today").json()["lesson"]

    assert len(lesson["sentence"].replace(".", " ").split()) <= 10
    assert 5 <= len(lesson["vocabulary_items"]) <= 10


def test_answer_correct_marks_completed(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.get("/api/micro-lessons/today").json()["lesson"]

    response = client.post(
        f"/api/micro-lessons/{lesson['lesson_id']}/answer",
        json={"answer": lesson["fill_blank_question"]["correct_answer"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["completed"] is True
    assert body["lesson"]["completed"] is True
    assert body["streak"]["today_completed"] is True


def test_answer_wrong_does_not_mark_completed(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.get("/api/micro-lessons/today").json()["lesson"]

    response = client.post(
        f"/api/micro-lessons/{lesson['lesson_id']}/answer",
        json={"answer": "raises"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["completed"] is False
    assert body["lesson"]["completed"] is False
    assert body["streak"]["today_completed"] is False
