"""Tests for AI tools router (study plan, writing analysis, TTS)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestStudyPlan:
    """Test study plan generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_study_plan_success(self):
        """Test successful study plan generation."""
        with patch("routers.ai_tools.study_planner") as mock_planner, \
             patch("routers.ai_tools.db") as mock_db:
            # Mock study planner
            mock_plan = MagicMock()
            mock_plan.model_dump.return_value = {
                "plan_id": "test-plan-123",
                "target_goal": "TOEIC 800",
                "language": "EN",
                "milestones": [],
                "daily_commitment_minutes": 30,
                "focus_areas": ["Vocabulary", "Grammar"],
            }
            mock_planner.generate_plan = AsyncMock(return_value=mock_plan)
            
            # Mock database
            mock_db.get_progress.return_value = {
                "english_progress": {
                    "current_level": "B1",
                    "completed_lessons": 5,
                    "accuracy_rate": 75.0,
                },
                "japanese_progress": {},
            }
            mock_db.record_learning_activity = MagicMock()
            
            response = client.post(
                "/api/study-plan/generate",
                params={"target_goal": "TOEIC 800", "language": "EN"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "plan" in data
            mock_planner.generate_plan.assert_called_once()
            mock_db.record_learning_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_study_plan_with_user_id(self):
        """Test study plan generation with custom user_id."""
        with patch("routers.ai_tools.study_planner") as mock_planner, \
             patch("routers.ai_tools.db") as mock_db:
            mock_plan = MagicMock()
            mock_plan.model_dump.return_value = {"plan_id": "test-plan"}
            mock_planner.generate_plan = AsyncMock(return_value=mock_plan)
            mock_db.get_progress.return_value = {
                "english_progress": {"current_level": "A2"},
                "japanese_progress": {},
            }
            
            response = client.post(
                "/api/study-plan/generate",
                params={"target_goal": "IELTS 7.0", "language": "EN", "user_id": "custom-user"},
            )
            
            assert response.status_code == 200
            # Verify user_id was passed correctly
            call_args = mock_db.get_progress.call_args
            assert call_args[0][0] == "custom-user" or call_args[1].get("user_id") == "custom-user"


class TestWritingAnalysis:
    """Test writing analysis endpoint."""

    @pytest.mark.asyncio
    async def test_analyze_writing_success(self):
        """Test successful writing analysis."""
        with patch("routers.ai_tools.writing_assistant") as mock_assistant, \
             patch("routers.ai_tools.db") as mock_db:
            mock_analysis = MagicMock()
            mock_analysis.model_dump.return_value = {
                "original_text": "Test text",
                "corrected_text": "Corrected text",
                "grammar_score": 85,
                "vocabulary_score": 80,
                "style_score": 75,
                "overall_score": 80,
                "estimated_level": "B2",
                "corrections": [],
                "suggestions": ["Good job!"],
                "feedback": "Well written.",
            }
            mock_assistant.analyze_writing = AsyncMock(return_value=mock_analysis)
            mock_db.record_learning_activity = MagicMock()
            
            response = client.post(
                "/api/writing/analyze",
                json={
                    "language": "EN",
                    "text": "This is a test sentence.",
                    "topic": "General",
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "analysis" in data
            mock_assistant.analyze_writing.assert_called_once()
            mock_db.record_learning_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_writing_japanese(self):
        """Test writing analysis for Japanese."""
        with patch("routers.ai_tools.writing_assistant") as mock_assistant:
            mock_analysis = MagicMock()
            mock_analysis.model_dump.return_value = {
                "original_text": "テスト",
                "corrected_text": "テスト",
                "grammar_score": 70,
                "vocabulary_score": 65,
                "style_score": 60,
                "overall_score": 65,
                "estimated_level": "N3",
                "corrections": [],
                "suggestions": [],
                "feedback": "Feedback",
            }
            mock_assistant.analyze_writing = AsyncMock(return_value=mock_analysis)
            
            response = client.post(
                "/api/writing/analyze",
                json={
                    "language": "JP",
                    "text": "これはテストです。",
                },
            )
            
            assert response.status_code == 200


class TestTTS:
    """Test TTS generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_tts(self):
        """Test TTS audio generation."""
        with patch("routers.ai_tools.tts_service") as mock_tts:
            mock_audio_path = MagicMock()
            mock_audio_path.name = "audio_123.wav"
            mock_tts.generate_audio = AsyncMock(return_value=mock_audio_path)
            
            response = client.post(
                "/api/tts",
                params={"text": "Hello world", "language": "en-US"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "audio_url" in data
            assert data["audio_url"] == "/api/audio/audio_123.wav"
            mock_tts.generate_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_tts_no_audio(self):
        """Test TTS when audio generation fails."""
        with patch("routers.ai_tools.tts_service") as mock_tts:
            mock_tts.generate_audio = AsyncMock(return_value=None)
            
            response = client.post(
                "/api/tts",
                params={"text": "Hello", "language": "en-US"},
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["audio_url"] is None
