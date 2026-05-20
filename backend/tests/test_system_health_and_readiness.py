"""Health and readiness routes should separate liveness from optional dependencies."""

import database as database_module
from database import Database
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import system as system_router


class _StubRagManager:
    def __init__(self, *, enabled: bool, init_error: str | None) -> None:
        self.enabled = enabled
        self.init_error = init_error


def _make_client(tmp_path, monkeypatch) -> TestClient:
    test_db = Database(str(tmp_path / "health.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)

    app = FastAPI()
    app.include_router(system_router.api_router)
    return TestClient(app)


def test_health_succeeds_without_ollama_or_rag_dependencies(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)
    called_models: list[str] = []

    async def _unexpected_check(model_name: str) -> bool:
        called_models.append(model_name)
        return False

    monkeypatch.setattr(system_router.ollama_client, "check_model_availability", _unexpected_check)
    monkeypatch.setattr(
        system_router,
        "rag_manager",
        _StubRagManager(enabled=False, init_error="chromadb missing"),
        raising=False,
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "healthy"
    assert body["database"]["ready"] is True
    assert "ollama" not in body
    assert "rag" not in body
    assert called_models == []


def test_ready_reports_optional_dependency_status_without_crashing(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)

    async def _model_ready(model_name: str) -> bool:
        return model_name == system_router.settings.small_model_name

    monkeypatch.setattr(system_router.ollama_client, "check_model_availability", _model_ready)
    monkeypatch.setattr(
        system_router,
        "rag_manager",
        _StubRagManager(enabled=False, init_error="chromadb missing"),
        raising=False,
    )

    response = client.get("/api/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "healthy"
    assert body["database"]["ready"] is True
    assert body["ollama"]["small_model_ready"] is True
    assert body["ollama"]["large_model_ready"] is False
    assert body["ollama"]["ready"] is True
    assert body["rag"]["ready"] is False
    assert body["rag"]["error"] == "chromadb missing"
