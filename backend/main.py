"""
FastAPI main application for Language Coach
"""
from fastapi import FastAPI, HTTPException, Query, WebSocket, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Literal, Dict, Any
import json
import os
import pandas as pd
import io
from datetime import datetime
from contextlib import asynccontextmanager

from models import (
    Lesson, GenerateLessonRequest, LessonQueryParams,
    UserProgress, LanguageProgress, ReviewAnswer, ReviewResult, UserRPGStats,
    WritingSubmission, WritingAnalysis
)
from database import db
from lesson_generator import lesson_generator
from scheduler import lesson_scheduler
from gamification_engine import gamification_engine
from config import settings
from chat_handler import chat_manager
from srs import srs_engine
from tts_service import tts_service
from export_service import pdf_exporter
from writing_assistant import writing_assistant
from study_planner import study_planner
from fastapi.responses import FileResponse


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    print("Starting Language Coach API...")
    lesson_scheduler.start()
    yield
    # Shutdown
    print("Shutting down Language Coach API...")
    lesson_scheduler.stop()


# Initialize FastAPI app
app = FastAPI(
    title="Language Coach API",
    description="API for English and Japanese learning with AI-generated lessons",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS (P1 Fix: Explicit origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Health Check ============
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Language Coach API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/health")
async def health_check():
    from ollama_client import ollama_client
    ollama_status = ollama_client.check_model_availability()
    return {
        "api": "healthy",
        "database": "connected",
        "ollama": "connected" if ollama_status else "disconnected",
        "model": settings.model_name,
        "timestamp": datetime.now().isoformat()
    }


# ============ Lesson Generation ============
@app.post("/api/generate/lesson", response_model=dict)
async def generate_lesson(request: GenerateLessonRequest):
    try:
        lesson = await lesson_generator.generate_lesson(
            language=request.language,
            topic=request.topic,
            level=request.difficulty,
            interest_context=request.interest_context
        )
        
        if not lesson:
            raise HTTPException(status_code=500, detail="Failed to generate lesson.")
        
        # Gamification
        xp_result = gamification_engine.add_xp("default_user", 50)
        words = [item.word for item in lesson.vocabulary]
        new_cards = gamification_engine.collect_word_cards("default_user", words, request.language)
        
        lesson_dict = lesson.model_dump(mode='json')
        lesson_dict['gamification'] = {
            "xp_added": 50,
            "leveled_up": xp_result.get("leveled_up"),
            "new_cards": [card.model_dump(mode='json') for card in new_cards]
        }
        
        return {"success": True, "lesson": lesson_dict}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks")
async def get_tasks(limit: int = 10):
    """Get generation task history"""
    return {"success": True, "tasks": db.get_generation_tasks("default_user", limit)}


# ============ Lesson Retrieval ============
@app.get("/api/lessons", response_model=dict)
async def list_lessons(
    language: Optional[Literal["EN", "JP"]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    level: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    lessons = db.query_lessons(language, start_date, end_date, level, topic, limit, offset)
    return {"success": True, "count": len(lessons), "lessons": lessons}


@app.get("/api/lessons/{lesson_id}", response_model=dict)
async def get_lesson(lesson_id: str):
    lesson_meta = db.get_lesson(lesson_id)
    if not lesson_meta: raise HTTPException(status_code=404, detail="Lesson not found")
    with open(lesson_meta['file_path'], 'r', encoding='utf-8') as f:
        lesson_data = json.load(f)
    return {"success": True, "lesson": lesson_data}


@app.get("/api/lessons/today/{language}", response_model=dict)
async def get_today_lesson(language: Literal["EN", "JP"]):
    lesson_meta = db.get_today_lesson(language)
    if not lesson_meta: return {"success": True, "lesson": None}
    with open(lesson_meta['file_path'], 'r', encoding='utf-8') as f:
        lesson_data = json.load(f)
    return {"success": True, "lesson": lesson_data}


# ============ Progress & Onboarding ============
@app.get("/api/progress", response_model=dict)
async def get_progress(user_id: str = "default_user"):
    progress = db.get_progress(user_id)
    if not progress:
        progress = {
            "user_id": user_id,
            "english_progress": {"language": "EN", "current_level": "A1", "target_level": "B2", "completed_lessons": 0, "total_exercises": 0, "correct_exercises": 0, "accuracy_rate": 0.0, "last_study_date": None},
            "japanese_progress": {"language": "JP", "current_level": "N5", "target_level": "N2", "completed_lessons": 0, "total_exercises": 0, "correct_exercises": 0, "accuracy_rate": 0.0, "last_study_date": None},
            "rpg_stats": UserRPGStats().model_dump(),
            "updated_at": datetime.now().isoformat()
        }
        db.save_progress(progress)
    return {"success": True, "progress": progress}


@app.post("/api/onboard")
async def onboard_user(language: str, level: str, difficulty: str):
    """Initial onboarding for new users"""
    stats_dict = db.get_rpg_stats("default_user")
    if stats_dict:
        stats = UserRPGStats(**stats_dict)
    else:
        stats = UserRPGStats()
        
    stats.is_onboarded = True
    stats.difficulty_mode = difficulty
    
    progress = db.get_progress("default_user") or {
        "user_id": "default_user",
        "english_progress": {"language": "EN", "current_level": "A1", "target_level": "B2", "completed_lessons": 0, "total_exercises": 0, "correct_exercises": 0, "accuracy_rate": 0.0, "last_study_date": None},
        "japanese_progress": {"language": "JP", "current_level": "N5", "target_level": "N2", "completed_lessons": 0, "total_exercises": 0, "correct_exercises": 0, "accuracy_rate": 0.0, "last_study_date": None}
    }
    
    if language == "EN": progress["english_progress"]["current_level"] = level
    else: progress["japanese_progress"]["current_level"] = level
        
    db.save_progress(progress)
    db.save_rpg_stats("default_user", stats.model_dump())
    return {"success": True}


# ============ Exercise Review ============
@app.post("/api/review", response_model=dict)
async def submit_review(answers: List[ReviewAnswer], user_id: str = "default_user", error_type: Optional[str] = None):
    if not answers: raise HTTPException(status_code=400, detail="No answers provided")
    
    lesson_id = answers[0].lesson_id
    lesson_meta = db.get_lesson(lesson_id)
    if not lesson_meta: raise HTTPException(status_code=404, detail="Lesson not found")
    
    with open(lesson_meta['file_path'], 'r', encoding='utf-8') as f:
        lesson_data = json.load(f)
    
    total_questions = len(answers)
    correct_count = 0
    incorrect_items = []
    
    for answer in answers:
        exercises = lesson_data['grammar']['exercises'] if answer.exercise_type == "grammar" else lesson_data['reading']['questions']
        if answer.question_index < len(exercises):
            exercise = exercises[answer.question_index]
            
            # P0 Fix: Force numeric comparison if possible
            ua = str(answer.user_answer).strip().lower()
            ca = str(exercise['correct_answer']).strip().lower()
            is_correct = ua == ca
            
            if is_correct: correct_count += 1
            else:
                incorrect_items.append({"question": exercise['question'], "user_answer": answer.user_answer, "correct_answer": exercise['correct_answer'], "explanation": exercise['explanation']})
    
    accuracy_rate = (correct_count / total_questions * 100) if total_questions > 0 else 0
    
    # Update Stats & Error Distribution
    stats_dict = db.get_rpg_stats(user_id)
    if stats_dict:
        stats = UserRPGStats(**stats_dict)
    else:
        stats = UserRPGStats()
        
    if accuracy_rate < 100 and error_type:
        stats.error_distribution[error_type] = stats.error_distribution.get(error_type, 0) + (total_questions - correct_count)
    
    xp_amount = (correct_count * 10) + ((total_questions - correct_count) * 2)
    xp_result = gamification_engine.add_xp(user_id, xp_amount)
    db.save_rpg_stats(user_id, stats.model_dump())
    
    # Update Progress
    progress = db.get_progress(user_id)
    if progress:
        lang = lesson_data['metadata']['language']
        key = 'english_progress' if lang == 'EN' else 'japanese_progress'
        progress[key]['total_exercises'] += total_questions
        progress[key]['correct_exercises'] += correct_count
        progress[key]['accuracy_rate'] = (progress[key]['correct_exercises'] / progress[key]['total_exercises'] * 100)
        db.save_progress(progress)
    
    return {
        "total_questions": total_questions,
        "correct_count": correct_count,
        "accuracy_rate": accuracy_rate,
        "incorrect_items": incorrect_items,
        "gamification": {"xp_added": xp_amount, "leveled_up": xp_result.get("leveled_up")}
    }


# ============ SRS & TTS & Chat & Export ============
@app.get("/api/srs/due")
async def get_due_items(language: str = None, user_id: str = "default_user"):
    return {"success": True, "items": db.get_due_srs_items(user_id, language=language)}

@app.post("/api/tts")
async def generate_tts(text: str, language: str):
    audio_path = await tts_service.generate_audio(text, language)
    return {"success": True, "audio_url": f"/api/audio/{os.path.basename(audio_path)}" if audio_path else None}

# P1 Fix: Add audio file endpoint
@app.get("/api/audio/{filename}")
async def get_audio_file(filename: str):
    file_path = os.path.join(settings.data_dir, "audio", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path)

@app.websocket("/ws/chat/{language}")
async def websocket_endpoint(websocket: WebSocket, language: str, scenario: str = "Daily Conversation"):
    await chat_manager.connect(websocket)
    await chat_manager.handle_chat(websocket, language, scenario)

@app.post("/api/rag/upload")
async def upload_rag_material(language: str, file: UploadFile = File(...)):
    from rag_manager import rag_manager
    content = await file.read()
    rag_manager.add_material(content.decode('utf-8'), metadata={"language": language, "source": file.filename})
    return {"success": True}

@app.get("/api/export/pdf/{lesson_id}")
async def export_lesson_pdf(lesson_id: str):
    lesson_meta = db.get_lesson(lesson_id)
    if not lesson_meta: raise HTTPException(status_code=404, detail="Lesson not found")
    with open(lesson_meta['file_path'], 'r', encoding='utf-8') as f:
        lesson_data = json.load(f)
    pdf_path = pdf_exporter.export_lesson(lesson_data)
    return FileResponse(pdf_path, filename=f"lesson_{lesson_id}.pdf")

@app.post("/api/study-plan/generate", response_model=dict)
async def generate_study_plan(target_goal: str, language: str):
    plan = await study_planner.generate_plan("default_user", target_goal, language)
    return {"success": True, "plan": plan}

@app.post("/api/writing/analyze", response_model=dict)
async def analyze_writing(submission: WritingSubmission):
    analysis = await writing_assistant.analyze_writing(submission.text, submission.language)
    return {"success": True, "analysis": analysis}

# P1 Fix: Correct Excel import logic
@app.post("/api/import/excel")
async def import_excel(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Check columns instead of values
        if 'word' not in df.columns or 'definition' not in df.columns:
            raise HTTPException(status_code=400, detail="Excel must contain columns: word, definition")
            
        imported_count = 0
        for _, row in df.iterrows():
            w = str(row['word']).strip()
            d = str(row['definition']).strip()
            if not w or not d:
                continue
                
            # Add to cards and SRS
            gamification_engine.collect_word_cards("default_user", [w], "EN") # Default to EN
            imported_count += 1
            
        return {"success": True, "count": imported_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
