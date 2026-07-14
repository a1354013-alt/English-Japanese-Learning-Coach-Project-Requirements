import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

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


def _client(tmp_path, monkeypatch, *, raise_server_exceptions: bool = True) -> TestClient:
    test_db = Database(str(tmp_path / "micro.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(micro_lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(streak_service_module.database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    return TestClient(_make_app(), raise_server_exceptions=raise_server_exceptions)


def _submit_diagnostic(client: TestClient) -> dict:
    questions = client.get("/api/diagnostic/questions").json()["questions"]
    correct_answers = {
        question.question_id: question.correct_answer for question in DIAGNOSTIC_QUESTIONS
    }
    answers = [{"question_id": item["question_id"], "answer": correct_answers[item["question_id"]]} for item in questions]
    response = client.post("/api/diagnostic/submit", json={"answers": answers})
    assert response.status_code == 200
    return response.json()["learning_plan"]


def _run_concurrently(callable_factory, count: int = 10) -> list:
    barrier = Barrier(count)

    def worker():
        barrier.wait(timeout=10)
        return callable_factory()

    with ThreadPoolExecutor(max_workers=count) as executor:
        return list(executor.map(lambda _index: worker(), range(count)))


def _activity_count(user_id: str, activity_type: str = "micro_lesson") -> int:
    with micro_lessons_router.db.get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(1) AS count
            FROM user_learning_activity
            WHERE user_id = ? AND activity_type = ?
            """,
            (user_id, activity_type),
        ).fetchone()
    return int(row["count"]) if row else 0


def _snapshot_reward_state(user_id: str, lesson_id: str) -> dict:
    progress = micro_lessons_router.db.get_progress(user_id)
    english = progress["english_progress"]
    rpg_stats = progress["rpg_stats"]
    return {
        "completed_lessons": english["completed_lessons"],
        "total_exercises": english["total_exercises"],
        "correct_exercises": english["correct_exercises"],
        "accuracy_rate": english["accuracy_rate"],
        "total_xp": rpg_stats["total_xp"],
        "current_xp": rpg_stats["current_xp"],
        "activity_count": _activity_count(user_id),
        "reward_event_count": micro_lessons_router.db.count_micro_lesson_reward_events(user_id, lesson_id),
    }


def _answer_current_lesson(client: TestClient, lesson: dict):
    return client.post(
        f"/api/micro-lessons/{lesson['lesson_id']}/answer",
        json={"answer": lesson["fill_blank_question"]["correct_answer"]},
    )


def _micro_lesson_row_count(user_id: str, day_index: int) -> int:
    with micro_lessons_router.db.get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(1) AS count
            FROM micro_lessons
            WHERE user_id = ? AND day_index = ?
            """,
            (user_id, day_index),
        ).fetchone()
    return int(row["count"]) if row else 0


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


def test_micro_lesson_templates_are_localized_for_beginner_zh_tw():
    lessons = [build_micro_lesson(day_index=day, total_days=90) for day in range(1, 8)]

    for lesson in lessons:
        realistic_phonetic_count = 0
        assert lesson.translation_zh != lesson.sentence
        assert any("\u4e00" <= char <= "\u9fff" for char in lesson.translation_zh)
        assert any("\u4e00" <= char <= "\u9fff" for char in lesson.grammar_note)
        assert any("\u4e00" <= char <= "\u9fff" for char in lesson.toeic_usage_note)
        assert "中文提示" in lesson.reading_passage
        for step in lesson.reading_order_steps:
            assert any("\u4e00" <= char <= "\u9fff" for char in step)
        for item in lesson.vocabulary_items:
            assert item.definition_zh != item.word
            assert item.example_translation != item.example_sentence
            assert item.phonetic.startswith("/") and item.phonetic.endswith("/")
            if item.phonetic != f"/{item.word}/":
                realistic_phonetic_count += 1
            assert any("\u4e00" <= char <= "\u9fff" for char in item.pronunciation_zh)
            assert not any("\u3040" <= char <= "\u30ff" for char in item.pronunciation_zh)
        for line in lesson.dialogue_lines:
            assert line.translation_zh != line.english
        for panel in lesson.comic_panels:
            assert panel.translation_zh != panel.english
        assert realistic_phonetic_count >= 4


def test_polite_request_template_treats_please_as_marker_not_subject():
    lesson = build_micro_lesson(day_index=5, total_days=90)

    assert lesson.sentence == "Please confirm the meeting time."
    assert lesson.subject_text == "(you)"
    assert lesson.verb_text == "confirm"
    assert lesson.object_text == "the meeting time"
    assert "Please" in lesson.grammar_note
    assert "不是主詞" in lesson.grammar_note


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


def test_correct_answer_keeps_completed_day_available_on_same_date(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.get("/api/micro-lessons/today").json()["lesson"]

    response = client.post(
        f"/api/micro-lessons/{lesson['lesson_id']}/answer",
        json={"answer": lesson["fill_blank_question"]["correct_answer"]},
    )
    assert response.status_code == 200

    today = client.get("/api/micro-lessons/today").json()["lesson"]

    assert today["day_index"] == 1
    assert today["lesson_id"] == lesson["lesson_id"]
    assert today["completed"] is True


def test_generate_preserves_completed_lesson_and_reward_state(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.get("/api/micro-lessons/today").json()["lesson"]
    answer = client.post(
        f"/api/micro-lessons/{lesson['lesson_id']}/answer",
        json={"answer": lesson["fill_blank_question"]["correct_answer"]},
    )
    assert answer.status_code == 200
    completed_lesson = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])
    assert completed_lesson is not None
    completed_at = completed_lesson["completed_at"]
    completed_local_date = completed_lesson["completed_local_date"]
    progress_after_complete = micro_lessons_router.db.get_progress("default_user")
    xp_after_complete = micro_lessons_router.db.get_rpg_stats("default_user")["total_xp"]
    streak_after_complete = micro_lessons_router.db.get_streak_info("default_user")

    first_generate = client.post("/api/micro-lessons/generate")
    second_generate = client.post("/api/micro-lessons/generate")
    persisted = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])

    assert first_generate.status_code == 200
    assert second_generate.status_code == 200
    assert first_generate.json()["lesson"] == second_generate.json()["lesson"]
    assert first_generate.json()["lesson"]["lesson_id"] == lesson["lesson_id"]
    assert first_generate.json()["lesson"]["completed"] is True
    assert persisted is not None
    assert persisted["lesson_id"] == lesson["lesson_id"]
    assert persisted["completed"] is True
    assert persisted["completed_at"] == completed_at
    assert persisted["completed_local_date"] == completed_local_date
    assert micro_lessons_router.db.get_progress("default_user")["english_progress"] == progress_after_complete["english_progress"]
    assert micro_lessons_router.db.get_rpg_stats("default_user")["total_xp"] == xp_after_complete
    assert micro_lessons_router.db.get_streak_info("default_user") == streak_after_complete


def test_save_micro_lesson_cannot_downgrade_completed_lesson(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.get("/api/micro-lessons/today").json()["lesson"]
    client.post(
        f"/api/micro-lessons/{lesson['lesson_id']}/answer",
        json={"answer": lesson["fill_blank_question"]["correct_answer"]},
    )
    completed = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])
    assert completed is not None

    replacement = build_micro_lesson(day_index=1, total_days=90).model_dump()
    replacement["lesson_id"] = "replacement-lesson"
    saved = micro_lessons_router.db.save_micro_lesson("default_user", replacement)
    persisted = micro_lessons_router.db.get_micro_lesson_by_day("default_user", 1)

    assert saved["lesson_id"] == lesson["lesson_id"]
    assert saved["completed"] is True
    assert persisted is not None
    assert persisted["lesson_id"] == lesson["lesson_id"]
    assert persisted["completed"] is True
    assert persisted["completed_at"] == completed["completed_at"]
    assert persisted["completed_local_date"] == completed["completed_local_date"]


def test_repeated_correct_answer_does_not_duplicate_progress_streak_or_xp(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.get("/api/micro-lessons/today").json()["lesson"]
    payload = {"answer": lesson["fill_blank_question"]["correct_answer"]}

    first = client.post(f"/api/micro-lessons/{lesson['lesson_id']}/answer", json=payload)
    progress_after_first = micro_lessons_router.db.get_progress("default_user")
    xp_after_first = micro_lessons_router.db.get_rpg_stats("default_user")["total_xp"]
    streak_after_first = first.json()["streak"]

    second = client.post(f"/api/micro-lessons/{lesson['lesson_id']}/answer", json=payload)
    progress_after_second = micro_lessons_router.db.get_progress("default_user")
    xp_after_second = micro_lessons_router.db.get_rpg_stats("default_user")["total_xp"]
    streak_after_second = second.json()["streak"]

    assert first.status_code == 200
    assert second.status_code == 200
    assert progress_after_first["english_progress"] == progress_after_second["english_progress"]
    assert xp_after_second == xp_after_first
    assert streak_after_second == streak_after_first


def test_next_micro_lesson_advancement_is_date_gated_and_deterministic(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.get("/api/micro-lessons/today").json()["lesson"]
    client.post(
        f"/api/micro-lessons/{lesson['lesson_id']}/answer",
        json={"answer": lesson["fill_blank_question"]["correct_answer"]},
    )
    completed_lesson = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])
    assert completed_lesson is not None

    same_day_state = micro_lessons_router.db.advance_micro_lesson_day_if_due(
        "default_user",
        today=completed_lesson["completed_local_date"],
    )
    assert same_day_state["current_day"] == 1

    next_day_state = micro_lessons_router.db.advance_micro_lesson_day_if_due("default_user", today="9999-01-01")
    day_two = client.get("/api/micro-lessons/today").json()["lesson"]

    assert next_day_state["current_day"] == 2
    assert day_two["day_index"] == 2
    assert day_two["completed"] is False


def test_generate_after_local_date_change_advances_once_and_returns_next_lesson(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.get("/api/micro-lessons/today").json()["lesson"]
    client.post(
        f"/api/micro-lessons/{lesson['lesson_id']}/answer",
        json={"answer": lesson["fill_blank_question"]["correct_answer"]},
    )
    completed = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])
    assert completed is not None
    next_date = "9999-01-01"
    monkeypatch.setattr(micro_lessons_router.db, "_local_date_str", lambda dt=None: next_date)

    first = client.post("/api/micro-lessons/generate").json()["lesson"]
    second = client.post("/api/micro-lessons/generate").json()["lesson"]
    third = client.post("/api/micro-lessons/generate").json()["lesson"]
    state = micro_lessons_router.db.get_diagnostic_state("default_user")

    assert first["day_index"] == 2
    assert second == first
    assert third == first
    assert state is not None
    assert state["current_day"] == 2
    assert micro_lessons_router.db.get_micro_lesson_by_day("default_user", 3) is None


def test_concurrent_generate_returns_one_canonical_persisted_lesson(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)

    for _attempt in range(3):
        responses = _run_concurrently(
            lambda: TestClient(_make_app()).post("/api/micro-lessons/generate"),
            count=10,
        )
        assert all(response.status_code == 200 for response in responses)
        lesson_ids = {response.json()["lesson"]["lesson_id"] for response in responses}
        assert len(lesson_ids) == 1
        canonical_id = next(iter(lesson_ids))
        persisted = micro_lessons_router.db.get_micro_lesson_by_day("default_user", 1)
        assert persisted is not None
        assert persisted["lesson_id"] == canonical_id
        assert _micro_lesson_row_count("default_user", 1) == 1

    answer_response = client.post(
        f"/api/micro-lessons/{canonical_id}/answer",
        json={"answer": persisted["fill_blank_question"]["correct_answer"]},
    )
    assert answer_response.status_code == 200
    assert answer_response.json()["completed"] is True

    monkeypatch.setattr(micro_lessons_router.db, "_local_date_str", lambda dt=None: "9999-01-01")
    next_day_responses = _run_concurrently(
        lambda: TestClient(_make_app()).post("/api/micro-lessons/generate"),
        count=10,
    )
    assert all(response.status_code == 200 for response in next_day_responses)
    next_day_ids = {response.json()["lesson"]["lesson_id"] for response in next_day_responses}
    assert len(next_day_ids) == 1
    next_day = micro_lessons_router.db.get_micro_lesson_by_day("default_user", 2)
    state = micro_lessons_router.db.get_diagnostic_state("default_user")
    assert next_day is not None
    assert next_day["lesson_id"] == next(iter(next_day_ids))
    assert state is not None
    assert state["current_day"] == 2
    assert _micro_lesson_row_count("default_user", 2) == 1
    assert micro_lessons_router.db.get_micro_lesson_by_day("default_user", 3) is None


def test_concurrent_correct_answers_complete_and_reward_once(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.post("/api/micro-lessons/generate").json()["lesson"]
    payload = {"answer": lesson["fill_blank_question"]["correct_answer"]}
    baseline_progress = micro_lessons_router.db.get_progress("default_user")["english_progress"]
    baseline_xp = micro_lessons_router.db.get_rpg_stats("default_user")["total_xp"]
    baseline_activity_count = _activity_count("default_user")

    for expected_delta in (1, 0):
        responses = _run_concurrently(
            lambda: TestClient(_make_app()).post(
                f"/api/micro-lessons/{lesson['lesson_id']}/answer",
                json=payload,
            ),
            count=10,
        )
        assert all(response.status_code == 200 for response in responses)
        assert all(response.json()["completed"] is True for response in responses)
        persisted = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])
        assert persisted is not None
        assert persisted["completed"] is True
        completed_at = persisted["completed_at"]
        completed_local_date = persisted["completed_local_date"]
        assert completed_at
        assert completed_local_date

        progress = micro_lessons_router.db.get_progress("default_user")["english_progress"]
        xp = micro_lessons_router.db.get_rpg_stats("default_user")["total_xp"]
        assert progress["completed_lessons"] == baseline_progress["completed_lessons"] + 1
        assert progress["total_exercises"] == baseline_progress["total_exercises"] + 1
        assert progress["correct_exercises"] == baseline_progress["correct_exercises"] + 1
        assert xp == baseline_xp + 10
        assert _activity_count("default_user") == baseline_activity_count + 1
        assert micro_lessons_router.db.count_micro_lesson_reward_events("default_user", lesson["lesson_id"]) == 1

        again = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])
        assert again is not None
        assert again["completed_at"] == completed_at
        assert again["completed_local_date"] == completed_local_date
        if expected_delta == 0:
            assert progress["completed_lessons"] == baseline_progress["completed_lessons"] + 1


def test_micro_lesson_reward_event_failure_rolls_back_completion_and_rewards(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, raise_server_exceptions=False)
    _submit_diagnostic(client)
    lesson = client.post("/api/micro-lessons/generate").json()["lesson"]
    baseline = _snapshot_reward_state("default_user", lesson["lesson_id"])

    with micro_lessons_router.db.get_connection() as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_micro_lesson_reward_event
            BEFORE INSERT ON micro_lesson_reward_events
            BEGIN
                SELECT RAISE(FAIL, 'forced reward event failure');
            END
            """
        )

    failed = _answer_current_lesson(client, lesson)
    persisted = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])

    assert failed.status_code == 500
    assert persisted is not None
    assert persisted["completed"] is False
    assert "completed_at" not in persisted
    assert "completed_local_date" not in persisted
    assert _snapshot_reward_state("default_user", lesson["lesson_id"]) == baseline

    with micro_lessons_router.db.get_connection() as conn:
        conn.execute("DROP TRIGGER fail_micro_lesson_reward_event")

    retry = _answer_current_lesson(client, lesson)
    final = _snapshot_reward_state("default_user", lesson["lesson_id"])
    persisted_after_retry = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])

    assert retry.status_code == 200
    assert persisted_after_retry is not None
    assert persisted_after_retry["completed"] is True
    assert persisted_after_retry["completed_at"]
    assert persisted_after_retry["completed_local_date"]
    assert final["reward_event_count"] == baseline["reward_event_count"] + 1
    assert final["completed_lessons"] == baseline["completed_lessons"] + 1
    assert final["total_exercises"] == baseline["total_exercises"] + 1
    assert final["correct_exercises"] == baseline["correct_exercises"] + 1
    assert final["total_xp"] == baseline["total_xp"] + 10
    assert final["activity_count"] == baseline["activity_count"] + 1


def test_micro_lesson_progress_failure_rolls_back_completion_event_xp_and_activity(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, raise_server_exceptions=False)
    _submit_diagnostic(client)
    lesson = client.post("/api/micro-lessons/generate").json()["lesson"]
    baseline = _snapshot_reward_state("default_user", lesson["lesson_id"])

    with micro_lessons_router.db.get_connection() as conn:
        conn.execute(
            """
            CREATE TRIGGER fail_micro_lesson_progress_update
            BEFORE UPDATE ON progress
            BEGIN
                SELECT RAISE(FAIL, 'forced progress failure');
            END
            """
        )

    failed = _answer_current_lesson(client, lesson)
    persisted = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])

    assert failed.status_code == 500
    assert persisted is not None
    assert persisted["completed"] is False
    assert "completed_at" not in persisted
    assert "completed_local_date" not in persisted
    assert _snapshot_reward_state("default_user", lesson["lesson_id"]) == baseline

    with micro_lessons_router.db.get_connection() as conn:
        conn.execute("DROP TRIGGER fail_micro_lesson_progress_update")

    retry = _answer_current_lesson(client, lesson)
    final = _snapshot_reward_state("default_user", lesson["lesson_id"])

    assert retry.status_code == 200
    assert final["reward_event_count"] == baseline["reward_event_count"] + 1
    assert final["completed_lessons"] == baseline["completed_lessons"] + 1
    assert final["total_exercises"] == baseline["total_exercises"] + 1
    assert final["correct_exercises"] == baseline["correct_exercises"] + 1
    assert final["total_xp"] == baseline["total_xp"] + 10
    assert final["activity_count"] == baseline["activity_count"] + 1


def test_post_commit_retry_does_not_change_reward_state(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = client.post("/api/micro-lessons/generate").json()["lesson"]

    first = _answer_current_lesson(client, lesson)
    after_first = _snapshot_reward_state("default_user", lesson["lesson_id"])
    completed = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])
    assert completed is not None
    completed_at = completed["completed_at"]
    completed_local_date = completed["completed_local_date"]

    repeated = [_answer_current_lesson(client, lesson) for _ in range(3)]
    responses = _run_concurrently(
        lambda: TestClient(_make_app()).post(
            f"/api/micro-lessons/{lesson['lesson_id']}/answer",
            json={"answer": lesson["fill_blank_question"]["correct_answer"]},
        ),
        count=10,
    )
    after_retries = _snapshot_reward_state("default_user", lesson["lesson_id"])
    persisted = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])

    assert first.status_code == 200
    assert all(response.status_code == 200 for response in repeated)
    assert all(response.status_code == 200 for response in responses)
    assert after_retries == after_first
    assert persisted is not None
    assert persisted["completed_at"] == completed_at
    assert persisted["completed_local_date"] == completed_local_date


def test_legacy_completed_lesson_without_reward_event_cannot_receive_duplicate_xp(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = build_micro_lesson(day_index=1, total_days=90).model_dump()
    lesson["lesson_id"] = "legacy-completed-without-event"
    lesson["completed"] = True
    with micro_lessons_router.db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO micro_lessons (
                lesson_id, user_id, day_index, lesson_json, completed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson["lesson_id"],
                "default_user",
                1,
                json.dumps(lesson, ensure_ascii=False, default=str),
                1,
                "2026-07-10T08:00:00+08:00",
                "2026-07-10T08:00:00+08:00",
            ),
        )
    baseline = _snapshot_reward_state("default_user", lesson["lesson_id"])

    response = _answer_current_lesson(client, lesson)
    after = _snapshot_reward_state("default_user", lesson["lesson_id"])
    persisted = micro_lessons_router.db.get_micro_lesson_by_id("default_user", lesson["lesson_id"])

    assert response.status_code == 200
    assert response.json()["completed"] is True
    assert persisted is not None
    assert persisted["completed"] is True
    assert after == baseline


def test_legacy_completed_lesson_without_completion_dates_uses_persisted_updated_at(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    lesson = build_micro_lesson(day_index=1, total_days=90).model_dump()
    lesson["lesson_id"] = "legacy-day-1"
    lesson["completed"] = True
    with micro_lessons_router.db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO micro_lessons (
                lesson_id, user_id, day_index, lesson_json, completed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson["lesson_id"],
                "default_user",
                1,
                json.dumps(lesson, ensure_ascii=False, default=str),
                1,
                "2026-07-10T08:00:00+08:00",
                "2026-07-10T08:00:00+08:00",
            ),
        )

    same_day = micro_lessons_router.db.advance_micro_lesson_day_if_due("default_user", today="2026-07-10")
    next_day = micro_lessons_router.db.advance_micro_lesson_day_if_due("default_user", today="2026-07-11")

    assert same_day is not None
    assert same_day["current_day"] == 1
    assert next_day is not None
    assert next_day["current_day"] == 2


def test_final_micro_lesson_day_does_not_advance_past_plan_total(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _submit_diagnostic(client)
    micro_lessons_router.db.save_diagnostic_state(
        user_id="default_user",
        estimated_total_days=2,
        current_day=2,
        summary_zh="final day",
        correct_count=4,
    )
    lesson = client.get("/api/micro-lessons/today").json()["lesson"]
    client.post(
        f"/api/micro-lessons/{lesson['lesson_id']}/answer",
        json={"answer": lesson["fill_blank_question"]["correct_answer"]},
    )
    monkeypatch.setattr(micro_lessons_router.db, "_local_date_str", lambda dt=None: "9999-01-01")

    generated = client.post("/api/micro-lessons/generate").json()["lesson"]
    state = micro_lessons_router.db.get_diagnostic_state("default_user")

    assert generated["day_index"] == 2
    assert generated["total_days"] == 2
    assert generated["completed"] is True
    assert state is not None
    assert state["current_day"] == 2


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
