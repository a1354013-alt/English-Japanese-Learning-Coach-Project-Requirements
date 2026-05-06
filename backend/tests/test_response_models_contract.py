"""Response-model contract coverage for key API endpoints and OpenAPI output."""

from fastapi.testclient import TestClient

import database as database_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.lesson_ops as lesson_ops_module
from database import Database
from main import app
from routers import imports as imports_router
from routers import lessons as lessons_router
from routers import review as review_router
from routers import system as system_router


class _FailingModel:
    async def _generate_with_model(self, **kwargs):  # pragma: no cover
        raise RuntimeError("no model in tests")


def _patch_test_state(monkeypatch, tmp_path):
    test_db = Database(str(tmp_path / "response-contract.db"))
    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(imports_router, "db", test_db, raising=False)

    gen = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(gen, "_generate_with_model", _FailingModel()._generate_with_model, raising=True)
    monkeypatch.setattr(lessons_router, "lesson_generator", gen, raising=False)
    return test_db


def test_openapi_exposes_typed_response_schemas():
    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    paths = openapi["paths"]
    schemas = openapi["components"]["schemas"]

    assert paths["/api/generate/lesson"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/GeneratedLessonResponse")
    assert paths["/api/progress"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/ProgressResponse")
    assert paths["/api/analytics"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/AnalyticsResponse")
    assert paths["/api/review"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/ReviewSubmitResponse")
    assert "ApiErrorPayload" in schemas


def test_response_models_keep_key_fields_for_lesson_review_progress_and_analytics(monkeypatch, tmp_path):
    _patch_test_state(monkeypatch, tmp_path)
    client = TestClient(app)

    r_gen = client.post("/api/generate/lesson", json={"language": "EN", "difficulty": "A1", "topic": "Schema Contract"})
    assert r_gen.status_code == 200
    lesson = r_gen.json()["lesson"]
    assert lesson["metadata"]["lesson_id"]
    assert "gamification" in lesson
    assert "xp_added" in lesson["gamification"]
    assert "new_cards" in lesson["gamification"]

    lesson_id = lesson["metadata"]["lesson_id"]
    answers = [
        {
            "lesson_id": lesson_id,
            "exercise_type": "grammar",
            "question_index": 0,
            "user_answer": lesson["grammar"]["exercises"][0]["correct_answer"],
            "correct_answer": lesson["grammar"]["exercises"][0]["correct_answer"],
        },
        {
            "lesson_id": lesson_id,
            "exercise_type": "reading",
            "question_index": 0,
            "user_answer": lesson["reading"]["questions"][0]["correct_answer"],
            "correct_answer": lesson["reading"]["questions"][0]["correct_answer"],
        },
    ]

    r_review = client.post("/api/review", json=answers)
    assert r_review.status_code == 200
    review = r_review.json()
    assert "gamification" in review
    assert "xp_added" in review["gamification"]
    assert "incorrect_items" in review

    progress = client.get("/api/progress").json()["progress"]
    assert "rpg_stats" in progress
    assert "is_onboarded" in progress["rpg_stats"]
    assert "word_cards" in progress["rpg_stats"]

    analytics = client.get("/api/analytics").json()["analytics"]
    assert "hardest_words" in analytics
    assert "accuracy_trend" in analytics
    assert "today_completed" in analytics


def test_response_models_keep_import_and_rag_outer_contract(monkeypatch):
    class _StubRag:
        enabled = True
        init_error = None
        disabled_by_config = False

        def list_materials(self, *, user_id: str, language=None):
            return [
                {
                    "doc_id": "doc-1",
                    "source": "notes.txt",
                    "language": language or "EN",
                    "uploaded_at": "2026-05-06T08:00:00",
                    "total_chunks": 1,
                }
            ]

    monkeypatch.setattr(imports_router, "rag_manager", _StubRag(), raising=False)
    client = TestClient(app)

    rag = client.get("/api/rag/materials?language=EN")
    assert rag.status_code == 200
    rag_body = rag.json()
    assert rag_body["success"] is True
    assert rag_body["items"][0]["doc_id"] == "doc-1"

    imported = client.get("/api/imported-vocabulary")
    assert imported.status_code == 200
    imported_body = imported.json()
    assert imported_body["success"] is True
    assert "count" in imported_body
    assert "items" in imported_body
