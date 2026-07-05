"""Demo reset API should rebuild a fully presentable dataset."""

import database as database_module
from config import settings
from database import Database
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import system as system_router


def test_demo_reset_disabled_by_default_returns_403(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "allow_demo_reset", False, raising=False)
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"), raising=False)
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)

    app = FastAPI()
    app.include_router(system_router.api_router)
    client = TestClient(app)

    response = client.post("/api/demo/reset")
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


def test_demo_reset_rebuilds_seed_data(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "allow_demo_reset", True, raising=False)
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"), raising=False)
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)

    app = FastAPI()
    app.include_router(system_router.api_router)
    client = TestClient(app)

    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["summary"]["lessons"] >= 2

    diagnostic_state = test_db.get_diagnostic_state("default_user")
    assert diagnostic_state is not None
    assert diagnostic_state["current_day"] == 1
    assert diagnostic_state["estimated_total_days"] == 90
    assert diagnostic_state["correct_count"] == 4

    lessons, total = test_db.query_lessons("default_user", limit=10, offset=0)
    assert total >= 2
    vocab, vocab_total = test_db.list_imported_vocabulary(user_id="default_user", limit=10, offset=0)
    assert vocab_total >= 2
    assert test_db.list_wrong_answers(user_id="default_user", limit=10, offset=0)


def test_demo_reset_clears_stale_micro_lesson_state(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "allow_demo_reset", True, raising=False)
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"), raising=False)
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)

    test_db.save_diagnostic_state(
        user_id="default_user",
        estimated_total_days=150,
        current_day=7,
        summary_zh="stale state",
        correct_count=1,
    )
    test_db.save_micro_lesson(
        "default_user",
        {
            "lesson_id": "stale-micro-lesson",
            "day_index": 7,
            "total_days": 150,
            "target_exam": "TOEIC 600",
            "sentence": "We study today.",
            "translation_zh": "stale",
            "subject_text": "We",
            "verb_text": "study",
            "object_text": "today",
            "reading_order_steps": ["We", "study", "today"],
            "grammar_note": "stale",
            "toeic_usage_note": "stale",
            "vocabulary_items": [
                {
                    "word": "study",
                    "phonetic": "/s/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "We study today.",
                    "example_translation": "stale",
                },
                {
                    "word": "team",
                    "phonetic": "/t/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "Our team studies.",
                    "example_translation": "stale",
                },
                {
                    "word": "daily",
                    "phonetic": "/d/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "Daily practice helps.",
                    "example_translation": "stale",
                },
                {
                    "word": "review",
                    "phonetic": "/r/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "We review often.",
                    "example_translation": "stale",
                },
                {
                    "word": "plan",
                    "phonetic": "/p/",
                    "pronunciation_zh": "stale",
                    "definition_zh": "stale",
                    "example_sentence": "A plan helps.",
                    "example_translation": "stale",
                },
            ],
            "dialogue_lines": [
                {
                    "speaker": "A",
                    "english": "We study today.",
                    "translation_zh": "stale",
                }
            ],
            "reading_passage": "stale passage",
            "comic_panels": [
                {
                    "panel": 1,
                    "english": "We study today.",
                    "translation_zh": "stale",
                    "scene_prompt": "stale",
                }
            ],
            "fill_blank_question": {
                "prompt": "We ___ today.",
                "choices": ["study", "studies", "studied"],
                "correct_answer": "study",
                "explanation": "stale",
            },
            "completed": True,
        },
    )

    app = FastAPI()
    app.include_router(system_router.api_router)
    client = TestClient(app)

    response = client.post("/api/demo/reset")
    assert response.status_code == 200

    diagnostic_state = test_db.get_diagnostic_state("default_user")
    assert diagnostic_state is not None
    assert diagnostic_state["current_day"] == 1
    assert diagnostic_state["estimated_total_days"] == 90
    assert diagnostic_state["correct_count"] == 4
    assert test_db.get_micro_lesson_by_day("default_user", 7) is None
