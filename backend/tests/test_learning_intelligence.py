"""Coverage for additive v1.3 learning-intelligence flows."""

from __future__ import annotations

import json
from pathlib import Path

import database as database_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.learning_intelligence as learning_intelligence_module
import services.lesson_ops as lesson_ops_module
from api_errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from database import Database
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from routers import lessons as lessons_router
from routers import review as review_router
from services.learning_intelligence import build_snowball_context, sync_lesson_items


class _UnavailableOllama:
    async def generate(self, **kwargs):
        return {"success": False, "error": "offline"}


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(lessons_router.router)
    app.include_router(review_router.router)
    return app


def _seed_textbook_lesson(db: Database, tmp_path: Path, *, user_id: str) -> dict:
    lesson_id = "lesson-intelligence-1"
    payload = {
        "metadata": {
            "lesson_id": lesson_id,
            "language": "EN",
            "level": "A1",
            "topic": "Study Habits",
            "generated_at": "2026-07-05T00:00:00",
            "estimated_duration_minutes": 15,
            "key_points": ["review"],
        },
        "objectives": ["Use review words.", "Explain the pattern.", "Teach it simply."],
        "vocabulary": [
            {
                "word": "review",
                "definition_zh": "複習",
                "example_sentence": "I review words.",
                "example_translation": "我複習單字。",
                "root": "view",
                "memory_tip": "re- means again.",
                "category": "study",
                "tags": ["habit"],
            }
        ],
        "word_roots": [
            {"root": "re-", "meaning_zh": "again", "examples": ["review"], "memory_tip": "repeat"},
            {"root": "pre-", "meaning_zh": "before", "examples": ["preview"], "memory_tip": "before"},
            {"root": "-tion", "meaning_zh": "noun", "examples": ["explanation"], "memory_tip": "noun"},
        ],
        "sentence_patterns": [
            {
                "pattern": "I review ... every day",
                "meaning_zh": "我每天複習……",
                "usage_note": "habit pattern",
                "examples": [{"sentence": "I review one phrase every day.", "translation": "我每天複習一句話。"}],
            }
        ],
        "grammar": {
            "title": "Simple Present",
            "explanation": "Use it for habits.",
            "examples": [],
            "exercises": [
                {
                    "question": "I ___ words every day.",
                    "options": ["review", "reviews", "reviewed"],
                    "correct_answer": "review",
                    "explanation": "Use the base form with I.",
                    "related_vocabulary": ["review"],
                    "related_grammar": ["Simple Present"],
                    "related_sentence_patterns": ["I review ... every day"],
                }
            ],
        },
        "reading": {
            "title": "Daily Review",
            "content": "I review one pattern every day.",
            "word_count": 6,
            "questions": [
                {
                    "question": "What does the learner review?",
                    "options": ["one pattern", "a movie", "nothing"],
                    "correct_answer": "one pattern",
                    "explanation": "The passage says one pattern.",
                    "related_vocabulary": ["review"],
                    "related_sentence_patterns": ["I review ... every day"],
                }
            ],
        },
        "dialogue": {
            "scenario": "Study",
            "context": "Routine",
            "dialogue": [],
            "alternatives": [],
        },
        "immersion": {"shadowing_text": [], "repeat_chunks": ["review every day"], "listening_tips": []},
        "feynman_prompt": {
            "prompt": "Explain how you review this lesson.",
            "checklist": ["Use one vocabulary word.", "Mention the grammar.", "Give one example."],
        },
        "review_plan": {
            "today": ["Review the word review."],
            "next_1_day": [],
            "next_3_days": [],
            "next_7_days": [],
        },
    }
    lesson_file = tmp_path / "lesson-intelligence.json"
    lesson_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    db.save_lesson(payload, str(lesson_file), user_id=user_id)
    return payload


def _patch_modules(monkeypatch, test_db: Database) -> None:
    for module in (
        database_module,
        gamification_module,
        lesson_ops_module,
        learning_intelligence_module,
        lesson_generator_module,
        lessons_router,
        review_router,
    ):
        monkeypatch.setattr(module, "db", test_db, raising=False)


def test_review_creates_item_level_srs_and_new_endpoints_work(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "learning-items.db"))
    _patch_modules(monkeypatch, test_db)
    user_id = "default_user"
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id=user_id)
    sync_lesson_items(user_id=user_id, lesson_data=lesson)

    app = _make_app()
    client = TestClient(app)

    due = client.get("/api/srs/items/due?language=EN")
    assert due.status_code == 200
    due_items = due.json()["items"]
    assert {item["item_type"] for item in due_items} == {
        "vocabulary",
        "grammar",
        "sentence_pattern",
    }

    answers = [
        {
            "lesson_id": lesson["metadata"]["lesson_id"],
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": "reviews",
            "correct_answer": "review",
        },
        {
            "lesson_id": lesson["metadata"]["lesson_id"],
            "exercise_type": "reading",
            "question_index": 0,
            "user_answer": "one pattern",
            "correct_answer": "one pattern",
        },
    ]
    review = client.post("/api/review", json=answers)
    assert review.status_code == 200

    with test_db.get_connection() as conn:
        reviewed_types = {
            row["item_type"]
            for row in conn.execute(
                """
                SELECT DISTINCT li.item_type
                FROM learning_item_reviews AS lir
                JOIN learning_items AS li ON li.id = lir.item_id
                WHERE li.user_id = ?
                """,
                (user_id,),
            ).fetchall()
        }
        legacy_srs_count = conn.execute(
            "SELECT COUNT(1) AS c FROM srs_vocabulary WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    assert reviewed_types == {"vocabulary", "grammar", "sentence_pattern"}
    assert int(legacy_srs_count["c"]) == 0

    weak = client.get("/api/srs/items/weak?language=EN")
    assert weak.status_code == 200
    weak_body = weak.json()
    assert weak_body["vocabulary"][0]["item_key"] == "review"
    assert weak_body["grammar"][0]["item_key"] == "Simple Present"

    vocab_item = next(item for item in due_items if item["item_type"] == "vocabulary")
    submit = client.post(
        "/api/srs/items/review",
        json={
            "item_id": vocab_item["item_id"],
            "rating": 5,
            "source": "srs_review",
        },
    )
    assert submit.status_code == 200
    assert submit.json()["mastery_state"] in {"learning", "review", "mastered"}


def test_learning_item_review_missing_item_returns_structured_404(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "learning-item-missing.db"))
    _patch_modules(monkeypatch, test_db)
    client = TestClient(_make_app())

    response = client.post(
        "/api/srs/items/review",
        json={
            "item_id": "missing-item",
            "rating": 3,
            "source": "srs_review",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": True,
        "message": "Learning item not found",
        "code": "learning_item_not_found",
        "detail": "Learning item not found",
    }


def test_learning_item_review_derives_correctness_from_rating(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "learning-item-ratings.db"))
    _patch_modules(monkeypatch, test_db)
    client = TestClient(_make_app())
    user_id = "default_user"

    outcomes: dict[int, dict[str, int | bool]] = {}
    for rating in (0, 3, 4, 5):
        saved = test_db.upsert_learning_item(
            user_id=user_id,
            item_type="vocabulary",
            item_key=f"word-{rating}",
            language="EN",
            level="A1",
            lesson_id="lesson-1",
            content={"word": f"word-{rating}"},
            category="study",
            tags=[],
        )
        with test_db.get_connection() as conn:
            conn.execute(
                """
                UPDATE learning_item_srs
                SET interval_days = 6, ease_factor = 2.5, repetitions = 2, lapses = 0, due_at = '2000-01-01T00:00:00'
                WHERE item_id = ?
                """,
                (str(saved["id"]),),
            )

        response = client.post(
            "/api/srs/items/review",
            json={
                "item_id": str(saved["id"]),
                "rating": rating,
                "correct": False,
                "source": "srs_review",
            },
        )
        assert response.status_code == 200

        body = response.json()
        with test_db.get_connection() as conn:
            review_row = conn.execute(
                "SELECT rating, correct FROM learning_item_reviews WHERE item_id = ? ORDER BY created_at DESC LIMIT 1",
                (str(saved["id"]),),
            ).fetchone()
        outcomes[rating] = {
            "interval_days": int(body["interval_days"]),
            "lapses": int(body["lapses"]),
            "correct": bool(review_row["correct"]),
        }

    assert outcomes[0] == {"interval_days": 1, "lapses": 1, "correct": False}
    assert outcomes[3]["lapses"] == 0
    assert outcomes[4]["lapses"] == 0
    assert outcomes[5]["lapses"] == 0
    assert outcomes[3]["correct"] is True
    assert outcomes[4]["correct"] is True
    assert outcomes[5]["correct"] is True
    assert outcomes[3]["interval_days"] < outcomes[4]["interval_days"] < outcomes[5]["interval_days"]


def test_snowball_context_and_prompt_include_recent_and_weak_items(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "snowball.db"))
    _patch_modules(monkeypatch, test_db)
    user_id = "default_user"

    test_db.upsert_learning_item(
        user_id=user_id,
        item_type="vocabulary",
        item_key="review",
        language="EN",
        level="A1",
        lesson_id="l1",
        content={"word": "review", "definition_zh": "複習"},
        category="study",
        tags=["habit"],
    )
    item = test_db.get_learning_item_by_key(
        user_id=user_id,
        item_type="vocabulary",
        item_key="review",
        language="EN",
    )
    assert item is not None
    test_db.record_learning_item_review(
        user_id=user_id,
        item_id=str(item["id"]),
        rating=1,
        correct=False,
        source="manual",
    )

    test_db.upsert_learning_item(
        user_id=user_id,
        item_type="sentence_pattern",
        item_key="I review ... every day",
        language="EN",
        level="A1",
        lesson_id="l1",
        content={"pattern": "I review ... every day", "meaning_zh": "habit"},
        category="sentence_pattern",
        tags=[],
    )

    context = build_snowball_context(user_id, "EN", "A1")
    assert context["weak_vocabulary"][0]["item_key"] == "review"
    assert context["recent_sentence_patterns"][0]["item_key"] == "I review ... every day"

    generator = lesson_generator_module.LessonGenerator()
    prompt = generator._build_prompt("EN", "A1", "Study Habits", snowball_context=context)
    assert "70% new content, 20% recent learned items, 10% weak items" in prompt
    assert "review" in prompt

    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id=user_id)
    sync_lesson_items(user_id=user_id, lesson_data=lesson)
    sync_lesson_items(user_id=user_id, lesson_data=lesson)
    with test_db.get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(1) AS c FROM learning_items WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    assert int(count["c"]) == 3


def test_feynman_feedback_fallback_stores_history_and_marks_missing_items_weak(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "feynman.db"))
    _patch_modules(monkeypatch, test_db)
    monkeypatch.setattr(learning_intelligence_module, "ollama_client", _UnavailableOllama(), raising=False)
    user_id = "default_user"
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id=user_id)
    sync_lesson_items(user_id=user_id, lesson_data=lesson)

    app = _make_app()
    client = TestClient(app)
    response = client.post(
        f"/api/lessons/{lesson['metadata']['lesson_id']}/feynman-feedback",
        json={
            "explanation": "I studied today.",
            "language": "EN",
        },
    )
    assert response.status_code == 200
    body = response.json()["feedback"]
    assert body["summary"]
    assert body["suggested_simple_explanation"]
    assert isinstance(body["missing_points"], list)

    vocab_item = test_db.get_learning_item_by_key(
        user_id=user_id,
        item_type="vocabulary",
        item_key="review",
        language="EN",
    )
    assert vocab_item is not None
    assert vocab_item["mastery_state"] in {"weak", "learning"}

    with test_db.get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(1) AS c FROM feynman_feedback_history WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    assert int(row["c"]) == 1


def test_feynman_feedback_ignores_client_lesson_snapshot_and_uses_persisted_lesson(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "feynman-snapshot.db"))
    _patch_modules(monkeypatch, test_db)
    monkeypatch.setattr(learning_intelligence_module, "ollama_client", _UnavailableOllama(), raising=False)
    user_id = "default_user"
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id=user_id)
    sync_lesson_items(user_id=user_id, lesson_data=lesson)

    client = TestClient(_make_app())
    response = client.post(
        f"/api/lessons/{lesson['metadata']['lesson_id']}/feynman-feedback",
        json={
            "explanation": "I studied today.",
            "language": "EN",
            "lesson_snapshot": {
                "metadata": {"language": "EN", "lesson_id": lesson["metadata"]["lesson_id"]},
                "vocabulary": [{"word": "tampered-word"}],
            },
        },
    )

    assert response.status_code == 200
    assert test_db.get_learning_item_by_key(
        user_id=user_id,
        item_type="vocabulary",
        item_key="tampered-word",
        language="EN",
    ) is None
    assert test_db.get_learning_item_by_key(
        user_id=user_id,
        item_type="vocabulary",
        item_key="review",
        language="EN",
    ) is not None


def test_feynman_feedback_rejects_language_mismatch(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "feynman-language.db"))
    _patch_modules(monkeypatch, test_db)
    user_id = "default_user"
    lesson = _seed_textbook_lesson(test_db, tmp_path, user_id=user_id)

    client = TestClient(_make_app())
    response = client.post(
        f"/api/lessons/{lesson['metadata']['lesson_id']}/feynman-feedback",
        json={"explanation": "I studied today.", "language": "JP"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "lesson_language_mismatch"
