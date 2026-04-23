"""Imported vocabulary delete must clean derived data (SRS + word cards)."""

from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database as database_module
import gamification_engine as gamification_module
import services.lesson_ops as lesson_ops_module
from database import Database
from models import UserRPGStats, WordCard
from routers import imports as imports_router
from srs import srs_engine


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(imports_router.router)
    return app


def test_delete_imported_vocabulary_cleans_srs_and_word_cards(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))

    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(imports_router, "db", test_db, raising=False)

    # Ensure default progress exists so rpg_stats cleanup path is deterministic.
    uid = "default_user"
    test_db.get_progress(uid)

    vocab = {
        "word": "resilience",
        "reading": None,
        "definition_zh": "韌性",
        "example_sentence": "Consistency builds resilience.",
        "example_translation": "持續的練習建立韌性。",
    }

    test_db.save_imported_vocabulary(uid, "EN", vocab)
    srs_data = srs_engine.calculate(quality=3, prev_interval=0, prev_ease_factor=2.5, repetition=0)
    test_db.update_srs_item(uid, vocab["word"], "EN", srs_data, vocab)

    stats = UserRPGStats(**test_db.get_rpg_stats(uid))
    stats.word_cards.append(
        WordCard(word=vocab["word"], rarity="C", collected_at=datetime.now(), language="EN")
    )
    test_db.save_rpg_stats(uid, stats.model_dump(mode="json"))

    items, total = test_db.list_imported_vocabulary(user_id=uid, language="EN", q=None, limit=10, offset=0)
    assert total == 1
    item_id = int(items[0]["id"])

    assert test_db.get_srs_item(uid, vocab["word"], "EN") is not None
    assert any(c.word == vocab["word"] and c.language == "EN" for c in UserRPGStats(**test_db.get_rpg_stats(uid)).word_cards)

    client = TestClient(_make_app())
    r = client.delete(f"/api/imported-vocabulary/{item_id}")
    assert r.status_code == 200

    # Source record removed.
    items2, total2 = test_db.list_imported_vocabulary(user_id=uid, language="EN", q=None, limit=10, offset=0)
    assert total2 == 0
    assert items2 == []

    # Derived data removed.
    assert test_db.get_srs_item(uid, vocab["word"], "EN") is None
    stats2 = UserRPGStats(**test_db.get_rpg_stats(uid))
    assert not any(c.word == vocab["word"] and c.language == "EN" for c in stats2.word_cards)

    # Repeat delete is a clear 404.
    r2 = client.delete(f"/api/imported-vocabulary/{item_id}")
    assert r2.status_code == 404
