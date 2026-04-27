"""Demo reset API should rebuild a fully presentable dataset."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database as database_module
from config import settings
from database import Database
from routers import system as system_router


def test_demo_reset_rebuilds_seed_data(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "t.db"))
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

    lessons, total = test_db.query_lessons("default_user", limit=10, offset=0)
    assert total >= 2
    vocab, vocab_total = test_db.list_imported_vocabulary(user_id="default_user", limit=10, offset=0)
    assert vocab_total >= 2
    assert test_db.list_wrong_answers(user_id="default_user", limit=10, offset=0)
