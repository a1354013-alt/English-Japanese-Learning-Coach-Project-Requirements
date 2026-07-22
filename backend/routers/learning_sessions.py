"""Typed REST APIs for structured learning-session lifecycle management."""

from __future__ import annotations

from api_errors import COMMON_ERROR_RESPONSES, api_error
from database import db
from fastapi import APIRouter, Depends, Query, Request, status
from models import (
    MAX_LEARNING_SESSION_PAGE_SIZE,
    AbandonLearningSessionRequest,
    AppendLearningSessionEventRequest,
    CompleteLearningSessionRequest,
    CreateLearningSessionRequest,
    LanguageCode,
    LearningSessionActiveResponse,
    LearningSessionDetailResponse,
    LearningSessionEventDetailResponse,
    LearningSessionEventListResponse,
    LearningSessionListResponse,
    LearningSessionSummaryResponse,
)
from repositories.errors import (
    InvalidLearningSessionEventError,
    InvalidLearningSessionPaginationError,
    InvalidLearningSessionTransitionError,
    LearningSessionAlreadyActiveError,
    LearningSessionIdempotencyConflictError,
    LearningSessionNotActiveError,
    LearningSessionNotFoundError,
)

from routers.deps import get_default_demo_user_id

router = APIRouter(prefix="/api/learning-sessions", tags=["learning-sessions"], responses=COMMON_ERROR_RESPONSES)


def _reject_user_id_query(request: Request) -> None:
    if "user_id" in request.query_params:
        raise api_error(422, "user_id is not accepted for demo learning-session APIs", "user_id_not_allowed")


def _map_learning_session_error(exc: Exception) -> Exception:
    if isinstance(exc, LearningSessionNotFoundError):
        return api_error(404, "Learning session not found", "learning_session_not_found")
    if isinstance(exc, LearningSessionAlreadyActiveError):
        return api_error(409, "An active learning session already exists", "learning_session_active_conflict")
    if isinstance(exc, LearningSessionNotActiveError):
        return api_error(409, "Learning session is not active", "learning_session_not_active")
    if isinstance(exc, InvalidLearningSessionTransitionError):
        return api_error(409, str(exc), "invalid_learning_session_transition")
    if isinstance(exc, InvalidLearningSessionEventError):
        return api_error(422, str(exc), "invalid_learning_session_event")
    if isinstance(exc, InvalidLearningSessionPaginationError):
        return api_error(422, str(exc), "invalid_learning_session_pagination")
    if isinstance(exc, LearningSessionIdempotencyConflictError):
        return api_error(409, str(exc), "learning_session_idempotency_conflict")
    return exc


@router.post(
    "",
    response_model=LearningSessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_reject_user_id_query)],
)
async def create_learning_session(
    request: CreateLearningSessionRequest,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        session = db.learning_session_repository.start_session(
            user_id=user_id,
            language=request.language,
            planned_minutes=request.planned_minutes,
        )
    except Exception as exc:  # pragma: no cover
        raise _map_learning_session_error(exc) from exc
    return {"success": True, "session": session}


@router.get(
    "/active",
    response_model=LearningSessionActiveResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def get_active_learning_session(
    language: LanguageCode = Query(...),
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        session = db.learning_session_repository.find_active_session(user_id=user_id, language=language)
    except Exception as exc:  # pragma: no cover
        raise _map_learning_session_error(exc) from exc
    return {"success": True, "session": session}


@router.get(
    "",
    response_model=LearningSessionListResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def list_learning_sessions(
    language: LanguageCode | None = Query(None),
    limit: int = Query(20, ge=1, le=MAX_LEARNING_SESSION_PAGE_SIZE),
    cursor: str | None = Query(None),
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        page = db.learning_session_repository.list_session_history(
            user_id=user_id,
            language=language,
            limit=limit,
            cursor=cursor,
        )
    except Exception as exc:  # pragma: no cover
        raise _map_learning_session_error(exc) from exc
    return {
        "success": True,
        "sessions": page.sessions,
        "limit": page.limit,
        "has_more": page.has_more,
        "next_cursor": page.next_cursor,
    }


@router.get(
    "/{session_id}",
    response_model=LearningSessionDetailResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def get_learning_session(
    session_id: str,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        session = db.learning_session_repository.get_session(session_id=session_id, user_id=user_id)
    except Exception as exc:  # pragma: no cover
        raise _map_learning_session_error(exc) from exc
    return {"success": True, "session": session}


@router.post(
    "/{session_id}/events",
    response_model=LearningSessionEventDetailResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def append_learning_session_event(
    session_id: str,
    request: AppendLearningSessionEventRequest,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        event = db.learning_session_repository.append_event(
            session_id=session_id,
            user_id=user_id,
            event_type=request.event_type,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            metadata=request.metadata,
            idempotency_key=request.idempotency_key,
        )
    except Exception as exc:  # pragma: no cover
        raise _map_learning_session_error(exc) from exc
    return {"success": True, "event": event}


@router.get(
    "/{session_id}/events",
    response_model=LearningSessionEventListResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def list_learning_session_events(
    session_id: str,
    limit: int = Query(50, ge=1, le=MAX_LEARNING_SESSION_PAGE_SIZE),
    cursor: str | None = Query(None),
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        page = db.learning_session_repository.list_events(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
            cursor=cursor,
        )
    except Exception as exc:  # pragma: no cover
        raise _map_learning_session_error(exc) from exc
    return {
        "success": True,
        "events": page.events,
        "limit": page.limit,
        "has_more": page.has_more,
        "next_cursor": page.next_cursor,
    }


@router.post(
    "/{session_id}/complete",
    response_model=LearningSessionDetailResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def complete_learning_session(
    session_id: str,
    request: CompleteLearningSessionRequest,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        session = db.learning_session_repository.complete_session(
            session_id=session_id,
            user_id=user_id,
            idempotency_key=request.idempotency_key,
        )
    except Exception as exc:  # pragma: no cover
        raise _map_learning_session_error(exc) from exc
    return {"success": True, "session": session}


@router.post(
    "/{session_id}/abandon",
    response_model=LearningSessionDetailResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def abandon_learning_session(
    session_id: str,
    request: AbandonLearningSessionRequest,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        session = db.learning_session_repository.abandon_session(
            session_id=session_id,
            user_id=user_id,
            idempotency_key=request.idempotency_key,
        )
    except Exception as exc:  # pragma: no cover
        raise _map_learning_session_error(exc) from exc
    return {"success": True, "session": session}


@router.get(
    "/{session_id}/summary",
    response_model=LearningSessionSummaryResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def get_learning_session_summary(
    session_id: str,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        summary = db.learning_session_repository.produce_summary(session_id=session_id, user_id=user_id)
    except Exception as exc:  # pragma: no cover
        raise _map_learning_session_error(exc) from exc
    return {"success": True, "summary": summary}
