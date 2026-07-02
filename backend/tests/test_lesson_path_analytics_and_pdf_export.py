"""Lesson file key portability, analytics semantics, and PDF export smoke tests."""

from pathlib import Path

import database as database_module
import export_service as export_service_module
import gamification_engine as gamification_module
import lesson_generator as lesson_generator_module
import services.lesson_ops as lesson_ops_module
from database import Database
from export_service import PDFExporter
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import imports as imports_router
from routers import lessons as lessons_router
from routers import review as review_router
from routers import system as system_router


class _FailingModel:
    async def _generate_with_model(self, **kwargs):  # pragma: no cover
        raise RuntimeError("no model in tests")


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(system_router.api_router)
    app.include_router(lessons_router.router)
    app.include_router(review_router.router)
    app.include_router(imports_router.router)
    return app


def _patch_isolated_state(tmp_path, monkeypatch) -> Database:
    test_db = Database(str(tmp_path / "t.db"))

    monkeypatch.setattr(database_module, "db", test_db, raising=False)
    monkeypatch.setattr(gamification_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_ops_module, "db", test_db, raising=False)
    monkeypatch.setattr(lesson_generator_module, "db", test_db, raising=False)
    monkeypatch.setattr(system_router, "db", test_db, raising=False)
    monkeypatch.setattr(lessons_router, "db", test_db, raising=False)
    monkeypatch.setattr(review_router, "db", test_db, raising=False)
    monkeypatch.setattr(imports_router, "db", test_db, raising=False)

    generator = lesson_generator_module.LessonGenerator()
    monkeypatch.setattr(
        generator,
        "_generate_with_model",
        _FailingModel()._generate_with_model,
        raising=True,
    )
    monkeypatch.setattr(lessons_router, "lesson_generator", generator, raising=False)
    return test_db


def _generated_lesson_client(tmp_path, monkeypatch) -> tuple[TestClient, Database]:
    test_db = _patch_isolated_state(tmp_path, monkeypatch)
    client = TestClient(_make_app())
    return client, test_db


def _answers_for_lesson(lesson: dict, *, first_grammar_answer: str | None = None) -> list[dict]:
    lesson_id = lesson["metadata"]["lesson_id"]
    answers = []
    for idx, exercise in enumerate(lesson["grammar"]["exercises"]):
        user_answer = first_grammar_answer if idx == 0 and first_grammar_answer is not None else exercise["correct_answer"]
        answers.append(
            {
                "lesson_id": lesson_id,
                "exercise_type": "grammar",
                "question_index": idx,
                "user_answer": user_answer,
                "correct_answer": exercise["correct_answer"],
            }
        )
    for idx, question in enumerate(lesson["reading"]["questions"]):
        answers.append(
            {
                "lesson_id": lesson_id,
                "exercise_type": "reading",
                "question_index": idx,
                "user_answer": question["correct_answer"],
                "correct_answer": question["correct_answer"],
            }
        )
    return answers


def test_lesson_file_path_is_portable_key_and_loadable(tmp_path, monkeypatch):
    client, test_db = _generated_lesson_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/generate/lesson",
        json={"language": "EN", "difficulty": "A1", "topic": "PathKey"},
    )
    assert response.status_code == 200
    lesson_id = response.json()["lesson"]["metadata"]["lesson_id"]

    meta = test_db.get_lesson(lesson_id, user_id="default_user")
    assert meta is not None
    stored = str(meta["file_path"])
    assert not Path(stored).is_absolute()
    assert stored.replace("\\", "/").startswith("lessons/")

    get_response = client.get(f"/api/lessons/{lesson_id}")
    assert get_response.status_code == 200
    assert get_response.json()["lesson"]["metadata"]["lesson_id"] == lesson_id


def test_analytics_exposes_latest_and_best_accuracy_semantics(tmp_path, monkeypatch):
    client, test_db = _generated_lesson_client(tmp_path, monkeypatch)

    lesson = client.post(
        "/api/generate/lesson",
        json={"language": "EN", "difficulty": "A1", "topic": "Analytics"},
    ).json()["lesson"]
    lesson_id = lesson["metadata"]["lesson_id"]
    perfect_answers = _answers_for_lesson(lesson)
    lower_answers = _answers_for_lesson(lesson, first_grammar_answer="wrong answer")

    assert client.post("/api/review", json=perfect_answers).status_code == 200
    assert client.post("/api/review", json=lower_answers).status_code == 200

    test_db.upsert_wrong_answer(
        user_id="default_user",
        language="EN",
        question_type="grammar",
        question="Hardest prompt",
        user_answer="A",
        correct_answer="B",
        source_lesson_id=lesson_id,
    )
    test_db.upsert_wrong_answer(
        user_id="default_user",
        language="EN",
        question_type="grammar",
        question="Hardest prompt",
        user_answer="C",
        correct_answer="B",
        source_lesson_id=lesson_id,
    )

    response = client.get("/api/analytics")
    assert response.status_code == 200
    payload = response.json()["analytics"]
    assert payload["lessons_completed"] >= 1
    assert payload["hardest_words"]
    assert payload["hardest_words"][0]["mistakes"] >= 1
    expected_latest = (len(lower_answers) - 1) / len(lower_answers) * 100
    assert payload["accuracy_trend"][0]["latest_accuracy_rate"] == expected_latest
    assert payload["accuracy_trend"][0]["best_accuracy_rate"] == 100.0


def test_pdf_export_endpoint_returns_pdf(tmp_path, monkeypatch):
    _patch_isolated_state(tmp_path, monkeypatch)
    exporter = PDFExporter(output_dir=str(tmp_path / "exports"))
    monkeypatch.setattr(export_service_module, "pdf_exporter", exporter, raising=False)
    monkeypatch.setattr(imports_router, "pdf_exporter", exporter, raising=False)

    client = TestClient(_make_app())
    lesson_id = client.post(
        "/api/generate/lesson",
        json={"language": "EN", "difficulty": "A1", "topic": "PDF"},
    ).json()["lesson"]["metadata"]["lesson_id"]

    response = client.get(f"/api/export/pdf/{lesson_id}")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert response.content[:4] == b"%PDF"


def test_pdf_export_handles_special_characters_and_cjk_text(tmp_path):
    exporter = PDFExporter(output_dir=str(tmp_path / "exports"))
    pdf_path = exporter.export_lesson(
        {
            "metadata": {
                "lesson_id": "special-pdf",
                "language": "JP",
                "level": "N4",
                "topic": '<tag> & "quotes" 日本語 中文',
            },
            "vocabulary": [
                {
                    "word": "<danger>",
                    "definition_zh": '中文解釋 & 日本語 "ok"',
                    "example_sentence": 'Use <tag> & keep "quotes".',
                    "example_translation": "保留特殊字元與日文內容。",
                }
            ],
            "grammar": {
                "title": "<grammar>",
                "explanation": 'A & B < C > D "quoted"',
                "exercises": [
                    {"question": "<q1>", "correct_answer": "&answer"}
                ],
            },
            "reading": {
                "content": '日本語の文章 <tag>\n中文段落 & "quotes"\nKeep all content.',
                "questions": [
                    {"question": "<what>", "correct_answer": "日本語と中文"}
                ],
            },
            "dialogue": {
                "scenario": "<scene>",
                "context": 'A & B "quoted"',
                "dialogue": [
                    {
                        "speaker": "<A>",
                        "text": "こんにちは & <tag>",
                        "translation": "你好",
                    }
                ],
            },
            "evidence": [{"source": "<pdf>", "text": '證據 & 日本語 "ok"'}],
        }
    )

    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:4] == b"%PDF"


def test_pdf_export_handles_empty_content_without_crashing(tmp_path):
    exporter = PDFExporter(output_dir=str(tmp_path / "exports"))
    pdf_path = exporter.export_lesson(
        {
            "metadata": {
                "lesson_id": "empty-pdf",
                "language": "EN",
                "level": "A1",
                "topic": "",
            },
            "vocabulary": [
                {
                    "word": "",
                    "definition_zh": "",
                    "example_sentence": "",
                    "example_translation": "",
                }
            ],
            "grammar": {"title": "", "explanation": "", "exercises": []},
            "reading": {"content": "", "questions": []},
            "dialogue": {"scenario": "", "context": "", "dialogue": []},
            "evidence": [],
        }
    )

    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:4] == b"%PDF"


def test_pdf_export_logs_warning_when_cjk_font_is_unavailable(tmp_path, caplog):
    caplog.set_level("WARNING")
    exporter = PDFExporter(
        output_dir=str(tmp_path / "exports"),
        font_paths=["/missing/font.ttf"],
    )

    pdf_path = exporter.export_lesson(
        {
            "metadata": {
                "lesson_id": "fallback-font",
                "language": "JP",
                "level": "N5",
                "topic": "Japanese PDF",
            },
            "vocabulary": [],
            "grammar": {"title": "", "explanation": "", "exercises": []},
            "reading": {"content": "日本語のPDF", "questions": []},
            "dialogue": {"scenario": "", "context": "", "dialogue": []},
            "evidence": [],
        }
    )

    assert exporter.font_name == "Helvetica"
    assert exporter.font_warning is not None
    assert "No CJK font was found" in caplog.text
    assert pdf_path.exists()
