"""Shared API dependencies (single-tenant demo user scoping)."""

from fastapi import HTTPException, Query

from config import settings


def require_demo_user_id(user_id: str = Query(default=settings.default_user_id)) -> str:
    """Enforce single-tenant demo scoping.

    The project currently runs as a single-user demo (no auth). We still keep user_id in the DB
    so the data model can evolve later, but API callers must not be able to select arbitrary user_id.
    """
    if user_id != settings.default_user_id:
        raise HTTPException(status_code=400, detail="Invalid user_id for demo mode")
    return user_id

