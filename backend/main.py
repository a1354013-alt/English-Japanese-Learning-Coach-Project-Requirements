"""FastAPI application entrypoint: lifespan, middleware, and router mounting."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api_errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from config import settings
from fastapi import HTTPException
from logging_config import configure_logging
from ollama_client import ollama_client
from routers import ai_tools, imports, lessons, review, system, streak, wrong_answers
from scheduler import lesson_scheduler

APP_VERSION = "1.2.0"

configure_logging()
logger = logging.getLogger(__name__)


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

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

_cors_list = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if not _cors_list:
    _cors_list = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "request_failed",
            extra={"method": request.method, "path": request.url.path, "duration_ms": duration_ms},
        )
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request_complete",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


app.include_router(system.root_router)
app.include_router(system.api_router)
app.include_router(lessons.router)
app.include_router(review.router)
app.include_router(wrong_answers.router)
app.include_router(streak.router)
app.include_router(imports.router)
app.include_router(ai_tools.router)
app.include_router(ai_tools.chat_ws_router)
