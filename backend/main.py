"""FastAPI main application for Language Coach."""
import io
import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from chat_handler import chat_manager
from config import settings
from database import db
from export_service import pdf_exporter
from gamification_engine import gamification_engine
from lesson_generator import lesson_generator
from models import GenerateLessonRequest, ReviewAnswer, UserRPGStats, WritingSubmission
from rag_manager import rag_manager
from scheduler import lesson_scheduler
from srs import srs_engine
from study_planner import study_planner
from tts_service import tts_service
from writing_assistant import writing_assistant


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.lessons_dir.mkdir(parents=True, exist_ok=True)
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    lesson_scheduler.start()
    try:
        yield
    finally:
        lesson_scheduler.stop()


app = FastAPI(
    title="Language Coach API",
    description="API for English and Japanese learning with AI-generated lessons",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_lesson_payload(lesson_id: str) -> Dict[str, Any]:
    lesson_meta = db.get_lesson(lesson_id)
    if not lesson_meta:
        raise HTTPException(status_code=404, detail="Lesson not found")

    file_path = Path(lesson_meta["file_path"]).resolve()
    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Lesson file is missing")

    return json.loads(file_path.read_text(encoding="utf-8"))


def _score_answers(lesson_data: Dict[str, Any], answers: List[ReviewAnswer]) -> Dict[str, Any]:
    incorrect_items: List[Dict[str, str]] = []
    correct_count = 0

    for answer in answers:
        exercises = lesson_data["grammar"]["exercises"] if answer.exercise_type == "grammar" else lesson_data["reading"]["questions"]
        if answer.question_index < 0 or answer.question_index >= len(exercises):
            continue

        exercise = exercises[answer.question_index]
        user_text = str(answer.user_answer).strip().lower()
        correct_text = str(exercise.get("correct_answer", "")).strip().lower()
        if user_text == correct_text:
            correct_count += 1
        else:
            incorrect_items.append(
                {
                    "question": str(exercise.get("question", "")),
                    "user_answer": str(answer.user_answer),
                    "correct_answer": str(exercise.get("correct_answer", "")),
                    "explanation": str(exercise.get("explanation", "")),
                }
            )

    total_questions = len(answers)
    accuracy_rate = (correct_count / total_questions * 100) if total_questions else 0.0
    return {
        "total_questions": total_questions,
        "correct_count": correct_count,
        "accuracy_rate": accuracy_rate,
        "incorrect_items": incorrect_items,
    }


def _update_progress_after_review(user_id: str, language: str, total: int, correct: int) -> Dict[str, Any]:
    progress = db.get_progress(user_id)
    key = "english_progress" if language == "EN" else "japanese_progress"

    target = progress[key]
    target["completed_lessons"] += 1
    target["total_exercises"] += total
    target["correct_exercises"] += correct
    target["last_study_date"] = datetime.now().isoformat()
    target["accuracy_rate"] = (target["correct_exercises"] / target["total_exercises"] * 100) if target["total_exercises"] else 0.0

    db.save_progress(progress)
    return progress


def _update_srs_after_review(user_id: str, language: str, lesson_data: Dict[str, Any], accuracy_rate: float) -> None:
    quality = 5 if accuracy_rate >= 80 else 3 if accuracy_rate >= 50 else 2
    for vocab in lesson_data.get("vocabulary", []):
        word = str(vocab.get("word", "")).strip()
        if not word:
            continue
        prev = db.get_srs_item(user_id, word, language)
        interval = int(prev["interval"]) if prev else 0
        ease_factor = float(prev["ease_factor"]) if prev else 2.5
        repetition = int(prev["srs_level"]) if prev else 0

        srs_data = srs_engine.calculate(
            quality=quality,
            prev_interval=interval,
            prev_ease_factor=ease_factor,
            repetition=repetition,
        )
        db.update_srs_item(user_id, word, language, srs_data, vocab)


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Language Coach API",
        "version": "1.1.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/health")
async def health_check():
    from ollama_client import ollama_client

    db_reachable = db.check_connection()
    ollama_model_ready = ollama_client.check_model_availability()

    return {
        "api": "healthy",
        "database": {
            "configured": bool(settings.db_path),
            "reachable": db_reachable,
            "ready": db_reachable,
        },
        "ollama": {
            "configured": bool(settings.ollama_url),
            "model": settings.model_name,
            "ready": ollama_model_ready,
        },
        "rag": {
            "configured": bool(settings.chroma_db_path),
            "ready": rag_manager.enabled,
            "error": rag_manager.init_error,
        },
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/generate/lesson", response_model=dict)
async def generate_lesson(request: GenerateLessonRequest):
    lesson = await lesson_generator.generate_lesson(
        language=request.language,
        topic=request.topic,
        level=request.difficulty,
        interest_context=request.interest_context,
    )

    xp_result = gamification_engine.add_xp("default_user", 50)
    words = [item.word for item in lesson.vocabulary]
    new_cards = gamification_engine.collect_word_cards("default_user", words, request.language)

    lesson_dict = lesson.model_dump(mode="json")
    lesson_dict["gamification"] = {
        "xp_added": 50,
        "leveled_up": xp_result.get("leveled_up"),
        "new_cards": [card.model_dump(mode="json") for card in new_cards],
    }

    return {"success": True, "lesson": lesson_dict}


@app.get("/api/tasks")
async def get_tasks(limit: int = 10):
    return {"success": True, "tasks": db.get_generation_tasks("default_user", limit)}


@app.get("/api/lessons", response_model=dict)
async def list_lessons(
    language: Optional[Literal["EN", "JP"]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    level: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    lessons = db.query_lessons(language, start_date, end_date, level, topic, limit, offset)
    return {"success": True, "count": len(lessons), "lessons": lessons}


@app.get("/api/lessons/{lesson_id}", response_model=dict)
async def get_lesson(lesson_id: str):
    return {"success": True, "lesson": _load_lesson_payload(lesson_id)}


@app.get("/api/lessons/today/{language}", response_model=dict)
async def get_today_lesson(language: Literal["EN", "JP"]):
    lesson_meta = db.get_today_lesson(language)
    if not lesson_meta:
        return {"success": True, "lesson": None}
    return {"success": True, "lesson": _load_lesson_payload(lesson_meta["lesson_id"])}


@app.get("/api/progress", response_model=dict)
async def get_progress(user_id: str = "default_user"):
    return {"success": True, "progress": db.get_progress(user_id)}


@app.post("/api/onboard")
async def onboard_user(language: Literal["EN", "JP"], level: str, difficulty: str):
    progress = db.get_progress("default_user")
    key = "english_progress" if language == "EN" else "japanese_progress"
    progress[key]["current_level"] = level

    stats = UserRPGStats(**db.get_rpg_stats("default_user"))
    stats.is_onboarded = True
    stats.difficulty_mode = difficulty

    progress["rpg_stats"] = stats.model_dump(mode="json")
    db.save_progress(progress)
    return {"success": True}


@app.post("/api/review", response_model=dict)
async def submit_review(answers: List[ReviewAnswer], user_id: str = "default_user", error_type: Optional[str] = None):
    if not answers:
        raise HTTPException(status_code=400, detail="No answers provided")

    lesson_id = answers[0].lesson_id
    lesson_data = _load_lesson_payload(lesson_id)
    review_data = _score_answers(lesson_data, answers)

    db.save_exercise_result(
        user_id=user_id,
        lesson_id=lesson_id,
        exercise_type="mixed",
        total_questions=review_data["total_questions"],
        correct_count=review_data["correct_count"],
        accuracy_rate=review_data["accuracy_rate"],
    )

    stats = UserRPGStats(**db.get_rpg_stats(user_id))
    if error_type and review_data["correct_count"] < review_data["total_questions"]:
        stats.error_distribution[error_type] = stats.error_distribution.get(error_type, 0) + (
            review_data["total_questions"] - review_data["correct_count"]
        )

    xp_amount = (review_data["correct_count"] * 10) + ((review_data["total_questions"] - review_data["correct_count"]) * 2)
    xp_result = gamification_engine.add_xp(user_id, xp_amount)
    db.save_rpg_stats(user_id, stats.model_dump(mode="json"))

    language = lesson_data["metadata"]["language"]
    _update_progress_after_review(user_id, language, review_data["total_questions"], review_data["correct_count"])
    _update_srs_after_review(user_id, language, lesson_data, review_data["accuracy_rate"])

    return {
        "success": True,
        **review_data,
        "gamification": {"xp_added": xp_amount, "leveled_up": xp_result.get("leveled_up")},
    }


@app.get("/api/srs/due")
async def get_due_items(language: Optional[str] = None, user_id: str = "default_user"):
    return {"success": True, "items": db.get_due_srs_items(user_id, language=language)}


@app.post("/api/tts")
async def generate_tts(text: str, language: str):
    audio_path = await tts_service.generate_audio(text, language)
    return {"success": True, "audio_url": f"/api/audio/{audio_path.name}" if audio_path else None}


@app.get("/api/audio/{filename}")
async def get_audio_file(filename: str):
    file_path = settings.audio_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path)


@app.websocket("/ws/chat/{language}")
async def websocket_endpoint(websocket: WebSocket, language: str, scenario: str = "Daily Conversation"):
    await chat_manager.connect(websocket)
    await chat_manager.handle_chat(websocket, language, scenario)


@app.post("/api/rag/upload")
async def upload_rag_material(language: Literal["EN", "JP"], file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith((".txt", ".md", ".csv")):
        raise HTTPException(status_code=400, detail="Only .txt, .md, and .csv files are supported")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    decoded_text = None
    for encoding in ("utf-8", "utf-8-sig", "cp932", "big5"):
        try:
            decoded_text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if decoded_text is None:
        decoded_text = raw.decode("utf-8", errors="replace")

    rag_manager.add_material(decoded_text, metadata={"language": language, "source": file.filename or "unknown"})
    return {"success": True}


@app.get("/api/export/pdf/{lesson_id}")
async def export_lesson_pdf(lesson_id: str):
    lesson_data = _load_lesson_payload(lesson_id)
    pdf_path = pdf_exporter.export_lesson(lesson_data)
    return FileResponse(pdf_path, filename=f"lesson_{lesson_id}.pdf")


@app.post("/api/study-plan/generate", response_model=dict)
async def generate_study_plan(target_goal: str, language: Literal["EN", "JP"]):
    progress = db.get_progress("default_user")
    current_progress = progress["english_progress"] if language == "EN" else progress["japanese_progress"]
    plan = await study_planner.generate_plan("default_user", target_goal, language, current_progress)
    return {"success": True, "plan": plan.model_dump(mode="json")}


@app.post("/api/writing/analyze", response_model=dict)
async def analyze_writing(submission: WritingSubmission):
    analysis = await writing_assistant.analyze_writing(submission)
    return {"success": True, "analysis": analysis.model_dump(mode="json")}


@app.post("/api/import/excel")
async def import_excel(language: Literal["EN", "JP"] = "EN", file: UploadFile = File(...), user_id: str = "default_user"):
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {err}")

    column_map = {str(c).strip().lower(): c for c in df.columns}
    if "word" not in column_map:
        raise HTTPException(status_code=400, detail="Excel must include a 'word' column")

    definition_col = column_map.get("definition_zh") or column_map.get("definition")
    if not definition_col:
        raise HTTPException(status_code=400, detail="Excel must include 'definition' or 'definition_zh' column")

    reading_col = column_map.get("reading")
    example_col = column_map.get("example_sentence") or column_map.get("example")
    translation_col = column_map.get("example_translation")

    imported_count = 0
    for _, row in df.iterrows():
        word = str(row[column_map["word"]]).strip()
        definition_zh = str(row[definition_col]).strip()
        if not word or not definition_zh or word.lower() == "nan":
            continue

        vocab_item = {
            "word": word,
            "reading": str(row[reading_col]).strip() if reading_col and not pd.isna(row[reading_col]) else None,
            "definition_zh": definition_zh,
            "example_sentence": str(row[example_col]).strip() if example_col and not pd.isna(row[example_col]) else "",
            "example_translation": str(row[translation_col]).strip() if translation_col and not pd.isna(row[translation_col]) else "",
        }

        db.save_imported_vocabulary(user_id, language, vocab_item)
        gamification_engine.collect_word_cards(user_id, [word], language)

        prev = db.get_srs_item(user_id, word, language)
        srs_data = srs_engine.calculate(
            quality=3,
            prev_interval=int(prev["interval"]) if prev else 0,
            prev_ease_factor=float(prev["ease_factor"]) if prev else 2.5,
            repetition=int(prev["srs_level"]) if prev else 0,
        )
        db.update_srs_item(user_id, word, language, srs_data, vocab_item)
        imported_count += 1

    return {"success": True, "count": imported_count}
