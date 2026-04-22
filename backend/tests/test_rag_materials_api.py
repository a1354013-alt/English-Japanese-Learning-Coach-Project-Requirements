"""RAG upload/list/delete API contract tests (with a stub manager)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import imports as imports_router


class _StubRag:
    def __init__(self) -> None:
        self.enabled = True
        self.init_error = None
        self._items = {}

    def add_material(self, text: str, metadata: dict, *, user_id: str, doc_id=None) -> str:
        doc_id = doc_id or f"d{len(self._items)+1}"
        self._items[doc_id] = {
            "doc_id": doc_id,
            "source": metadata.get("source", "unknown"),
            "language": metadata.get("language", "unknown"),
            "uploaded_at": "2026-04-21T00:00:00",
            "total_chunks": 1,
            "user_id": user_id,
        }
        return doc_id

    def list_materials(self, *, user_id: str, language=None):
        items = [v for v in self._items.values() if v["user_id"] == user_id]
        if language:
            items = [v for v in items if v["language"] == language]
        return [{k: v for k, v in item.items() if k != "user_id"} for item in items]

    def delete_material(self, *, user_id: str, doc_id: str) -> bool:
        item = self._items.get(doc_id)
        if not item or item["user_id"] != user_id:
            return False
        del self._items[doc_id]
        return True


def test_rag_list_delete_smoke(monkeypatch):
    stub = _StubRag()
    monkeypatch.setattr(imports_router, "rag_manager", stub, raising=False)

    app = FastAPI()
    app.include_router(imports_router.router)
    client = TestClient(app)

    # upload (multipart)
    files = {"file": ("a.txt", b"hello world", "text/plain")}
    r_up = client.post("/api/rag/upload?language=EN", files=files)
    assert r_up.status_code == 200
    doc_id = r_up.json()["doc_id"]

    r_list = client.get("/api/rag/materials?language=EN")
    assert r_list.status_code == 200
    body = r_list.json()
    assert body["success"] is True
    assert any(i["doc_id"] == doc_id for i in body["items"])

    r_del = client.delete(f"/api/rag/materials/{doc_id}")
    assert r_del.status_code == 200
    assert r_del.json()["success"] is True

    # deleting again should be a 404 (not "fake success")
    r_del_missing = client.delete(f"/api/rag/materials/{doc_id}")
    assert r_del_missing.status_code == 404
    assert r_del_missing.json()["detail"] == "Material not found"


def test_rag_delete_surface_underlying_failure(monkeypatch):
    class _FailingDeleteStub(_StubRag):
        def delete_material(self, *, user_id: str, doc_id: str) -> bool:  # type: ignore[override]
            item = self._items.get(doc_id)
            if not item or item["user_id"] != user_id:
                return False
            raise RuntimeError("storage down")

    stub = _FailingDeleteStub()
    monkeypatch.setattr(imports_router, "rag_manager", stub, raising=False)

    app = FastAPI()
    app.include_router(imports_router.router)
    client = TestClient(app)

    files = {"file": ("a.txt", b"hello world", "text/plain")}
    r_up = client.post("/api/rag/upload?language=EN", files=files)
    assert r_up.status_code == 200
    doc_id = r_up.json()["doc_id"]

    r_del = client.delete(f"/api/rag/materials/{doc_id}")
    assert r_del.status_code == 500
    assert "Failed to delete material" in r_del.json()["detail"]


def test_rag_delete_returns_503_when_rag_disabled(monkeypatch):
    stub = _StubRag()
    stub.enabled = False
    stub.init_error = "RAG init failed"
    monkeypatch.setattr(imports_router, "rag_manager", stub, raising=False)

    app = FastAPI()
    app.include_router(imports_router.router)
    client = TestClient(app)

    r_del = client.delete("/api/rag/materials/does-not-matter")
    assert r_del.status_code == 503
    assert r_del.json()["detail"] == "RAG init failed"

