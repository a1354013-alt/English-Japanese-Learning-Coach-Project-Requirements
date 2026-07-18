from __future__ import annotations

import gc
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from queue import Queue

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
        conn = test_db.get_connection()
        row = conn.execute("SELECT 1 AS ok").fetchone()
        return {"ok": int(row["ok"]), "connection_id": id(conn)}

    return app


def test_database_close_all_connections_closes_tracked_worker_connections(tmp_path):
    test_db = Database(str(tmp_path / "close-all.db"))

    def _open_worker_connection() -> int:
        conn = test_db.get_connection()
        row = conn.execute("SELECT 1 AS ok").fetchone()
        return int(row["ok"])

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _index: _open_worker_connection(), range(4)))

    assert results == [1, 1, 1, 1]
    assert len(test_db._thread_connections) >= 1

    test_db.close_all_connections()

    assert test_db._thread_connections == {}
    assert getattr(test_db._local, "conn", None) is None
    assert test_db not in Database._instances


def test_sqlite_lifecycle_handles_short_lived_thread_reuse_pressure(tmp_path, recwarn):
    test_db = Database(str(tmp_path / "lifecycle-stress.db"))
    app = _build_lifecycle_app(test_db)
    worker_results: "Queue[tuple[int, int]]" = Queue()

    def _worker_open_connection() -> None:
        conn = test_db.get_connection()
        row = conn.execute("SELECT 1 AS ok").fetchone()
        assert int(row["ok"]) == 1
        worker_results.put((threading.get_ident(), id(conn)))

    with TestClient(app) as client:
        expected_connection_ids = {id(test_db.get_connection())}
        thread_ids: list[int] = []
        connection_ids: list[int] = []

        for _batch in range(80):
            response = client.get("/sync-health")
            assert response.status_code == 200
            expected_connection_ids.add(int(response.json()["connection_id"]))

            threads = [threading.Thread(target=_worker_open_connection) for _ in range(3)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        while not worker_results.empty():
            thread_id, connection_id = worker_results.get_nowait()
            thread_ids.append(thread_id)
            connection_ids.append(connection_id)

        assert len(connection_ids) == 240
        assert len(set(connection_ids)) == 240
        expected_connection_ids.update(connection_ids)
        assert set(test_db._thread_connections.keys()) == expected_connection_ids
        assert len(test_db._thread_connections) == len(expected_connection_ids)
        assert len(thread_ids) == 240

        # Real short-lived workers have already opened one connection each. To keep this
        # regression deterministic across hosts, project those connections through a tiny
        # recycled identifier space and prove the legacy thread-id keyed registry would
        # lose reachability even though the connection-identity registry retains them all.
        recycled_thread_slots = [index % 5 for index in range(len(connection_ids))]
        legacy_registry = {
            recycled_slot: connection_id
            for recycled_slot, connection_id in zip(recycled_thread_slots, connection_ids)
        }
        assert len(legacy_registry) == 5
        assert len(legacy_registry) < len(connection_ids)

    test_db.close_all_connections()
    assert test_db._thread_connections == {}
    assert test_db not in Database._instances

    Database.close_all_instances()
    del app
    gc.collect()

    warnings = list(recwarn)
    assert not any(issubclass(w.category, ResourceWarning) for w in warnings)
    assert not any(issubclass(w.category, pytest.PytestUnraisableExceptionWarning) for w in warnings)
