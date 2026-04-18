"""FastAPI application entrypoint: lifespan, middleware, and router mounting."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from ollama_client import ollama_client
from scheduler import lesson_scheduler

from routers import ai_tools, imports, lessons, review, system, streak, wrong_answers

APP_VERSION = "1.2.0"


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
        await ollama_client.aclose()


app = FastAPI(
    title="Language Coach API",
    description="API for English and Japanese learning with AI-generated lessons",
    version=APP_VERSION,
    lifespan=lifespan,
)

_cors_list = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if not _cors_list:
    _cors_list = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.root_router)
app.include_router(system.api_router)
app.include_router(lessons.router)
app.include_router(review.router)
app.include_router(wrong_answers.router)
app.include_router(streak.router)
app.include_router(imports.router)
app.include_router(ai_tools.router)
app.include_router(ai_tools.chat_ws_router)
