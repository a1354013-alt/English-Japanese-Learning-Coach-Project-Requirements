from __future__ import annotations

import gc
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import pytest
from database import Database
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_lifecycle_app(test_db: Database) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            test_db.close_all_connections()

    app = FastAPI(lifespan=lifespan)

    @app.get("/sync-health")
    def sync_health():
        with test_db.get_connection() as conn:
            row = conn.execute("SELECT 1 AS ok").fetchone()
        return {"ok": int(row["ok"])}

    return app


def test_database_close_all_connections_closes_tracked_worker_connections(tmp_path):
    test_db = Database(str(tmp_path / "close-all.db"))

    def _open_worker_connection() -> int:
        with test_db.get_connection() as conn:
            row = conn.execute("SELECT 1 AS ok").fetchone()
        return int(row["ok"])

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _index: _open_worker_connection(), range(4)))

    assert results == [1, 1, 1, 1]
    assert len(test_db._thread_connections) >= 1

    test_db.close_all_connections()

    assert test_db._thread_connections == {}
    assert getattr(test_db._local, "conn", None) is None


def test_sqlite_lifecycle_emits_no_unclosed_connection_warnings(tmp_path, recwarn):
    test_db = Database(str(tmp_path / "lifecycle.db"))
    app = _build_lifecycle_app(test_db)

    with TestClient(app) as client:
        response = client.get("/sync-health")
        assert response.status_code == 200

        def _open_worker_connection() -> int:
            with test_db.get_connection() as conn:
                row = conn.execute("SELECT 1 AS ok").fetchone()
            try:
                return int(row["ok"])
            finally:
                test_db.close()

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _index: _open_worker_connection(), range(4)))
        assert results == [1, 1, 1, 1]

    test_db.close_all_connections()
    Database.close_all_instances()
    del client
    del app
    gc.collect()

    warnings = list(recwarn)
    assert not any(issubclass(w.category, ResourceWarning) for w in warnings)
    assert not any(issubclass(w.category, pytest.PytestUnraisableExceptionWarning) for w in warnings)
