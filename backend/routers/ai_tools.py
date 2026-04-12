"""Study plan, writing analysis, TTS, audio files, and chat WebSocket."""
from typing import Literal

from fastapi import APIRouter, HTTPException, WebSocket
from fastapi.responses import FileResponse

from chat_handler import chat_manager
from config import settings
from database import db
from models import WritingSubmission
from study_planner import study_planner
from tts_service import tts_service
from writing_assistant import writing_assistant

router = APIRouter(prefix="/api", tags=["ai-tools"])

# WebSocket path is /ws/... (not under /api); separate router with no prefix.
chat_ws_router = APIRouter(tags=["ai-tools"])


@router.post("/study-plan/generate", response_model=dict)
async def generate_study_plan(target_goal: str, language: Literal["EN", "JP"]):
    progress = db.get_progress("default_user")
    current_progress = progress["english_progress"] if language == "EN" else progress["japanese_progress"]
    plan = await study_planner.generate_plan("default_user", target_goal, language, current_progress)
    return {"success": True, "plan": plan.model_dump(mode="json")}


@router.post("/writing/analyze", response_model=dict)
async def analyze_writing(submission: WritingSubmission):
    analysis = await writing_assistant.analyze_writing(submission)
    return {"success": True, "analysis": analysis.model_dump(mode="json")}


@router.post("/tts")
async def generate_tts(text: str, language: str):
    audio_path = await tts_service.generate_audio(text, language)
    return {"success": True, "audio_url": f"/api/audio/{audio_path.name}" if audio_path else None}


@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    file_path = settings.audio_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path)


@chat_ws_router.websocket("/ws/chat/{language}")
async def websocket_endpoint(websocket: WebSocket, language: str, scenario: str = "Daily Conversation"):
    await chat_manager.connect(websocket)
    await chat_manager.handle_chat(websocket, language, scenario)
