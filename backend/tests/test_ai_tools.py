"""Tests for AI tools router (study plan, writing analysis, TTS).

These are intentionally light: they validate API contract wiring (router -> service -> response shape)
without relying on a real Ollama server.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_generate_study_plan_success():
    with patch("routers.ai_tools.study_planner") as mock_planner, patch("routers.ai_tools.db") as mock_db:
        mock_plan = MagicMock()
        mock_plan.model_dump.return_value = {"plan_id": "test-plan"}
        mock_planner.generate_plan = AsyncMock(return_value=mock_plan)

        mock_db.get_progress.return_value = {"english_progress": {"current_level": "A2"}, "japanese_progress": {}}
        mock_db.record_learning_activity = MagicMock()

        response = client.post("/api/study-plan/generate", params={"target_goal": "TOEIC 800", "language": "EN"})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["plan"]["plan_id"] == "test-plan"

        mock_planner.generate_plan.assert_called_once()
        mock_db.record_learning_activity.assert_called_once()


def test_analyze_writing_success():
    with patch("routers.ai_tools.writing_assistant") as mock_assistant, patch("routers.ai_tools.db") as mock_db:
        mock_analysis = MagicMock()
        mock_analysis.model_dump.return_value = {"original_text": "x", "corrected_text": "x"}
        mock_assistant.analyze_writing = AsyncMock(return_value=mock_analysis)
        mock_db.record_learning_activity = MagicMock()

        response = client.post("/api/writing/analyze", json={"language": "EN", "text": "hello"})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["analysis"]["original_text"] == "x"

        mock_assistant.analyze_writing.assert_called_once()
        mock_db.record_learning_activity.assert_called_once()


def test_generate_tts_returns_audio_url():
    with patch("routers.ai_tools.tts_service") as mock_tts:
        mock_audio_path = MagicMock()
        mock_audio_path.name = "audio_123.wav"
        mock_tts.generate_audio = AsyncMock(return_value=mock_audio_path)

        response = client.post("/api/tts", params={"text": "Hello world", "language": "en-US"})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["audio_url"] == "/api/audio/audio_123.wav"

