"""Root metadata, health checks, and user progress."""
from datetime import datetime

from fastapi import APIRouter

from config import settings
from database import db
from ollama_client import ollama_client
from rag_manager import rag_manager

root_router = APIRouter(tags=["system"])

api_router = APIRouter(prefix="/api", tags=["system"])


@root_router.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Language Coach API",
        "version": "1.1.0",
        "timestamp": datetime.now().isoformat(),
    }


@api_router.get("/health")
async def health_check():
    db_reachable = db.check_connection()
    ollama_model_ready = await ollama_client.check_model_availability()

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


@api_router.get("/progress", response_model=dict)
async def get_progress(user_id: str = "default_user"):
    return {"success": True, "progress": db.get_progress(user_id)}
