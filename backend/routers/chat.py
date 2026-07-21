"""Typed REST APIs for persisted chat conversation management."""

from __future__ import annotations

from typing import Any, Optional

from api_errors import COMMON_ERROR_RESPONSES, api_error
from database import db
from fastapi import APIRouter, Depends, Query, Request, status
from models import (
    ChatConversationCreateRequest,
    ChatConversationDeleteResponse,
    ChatConversationDetailResponse,
    ChatConversationListResponse,
    ChatConversationResponse,
    ChatScenarioListResponse,
    ChatScenarioResponse,
    ChatConversationUpdateRequest,
    ChatMessageListResponse,
    ChatMessageResponse,
)
from chat_scenarios import list_scenarios
from repositories.errors import (
    ConversationNotFoundError,
    InvalidChatLanguageError,
    InvalidChatPaginationError,
    InvalidChatScenarioError,
    InvalidChatSummaryCheckpointError,
    LessonLinkIntegrityError,
    LessonLinkNotFoundError,
)

from routers.deps import get_default_demo_user_id

router = APIRouter(prefix="/api/chat", tags=["chat"], responses=COMMON_ERROR_RESPONSES)


def _reject_user_id_query(request: Request) -> None:
    if "user_id" in request.query_params:
        raise api_error(422, "user_id is not accepted for demo chat APIs", "user_id_not_allowed")


def _map_chat_error(exc: Exception) -> Exception:
    if isinstance(exc, ConversationNotFoundError):
        return api_error(404, "Conversation not found", "conversation_not_found")
    if isinstance(exc, InvalidChatLanguageError):
        return api_error(422, str(exc), "invalid_chat_language")
    if isinstance(exc, InvalidChatScenarioError):
        return api_error(422, str(exc), "invalid_chat_scenario")
    if isinstance(exc, InvalidChatPaginationError):
        return api_error(422, str(exc), "invalid_chat_pagination")
    if isinstance(exc, InvalidChatSummaryCheckpointError):
        return api_error(422, str(exc), "invalid_summary_checkpoint")
    if isinstance(exc, LessonLinkNotFoundError):
        return api_error(404, "Lesson not found", "lesson_not_found")
    if isinstance(exc, LessonLinkIntegrityError):
        return api_error(409, "Lesson language must match the conversation language.", "lesson_language_mismatch")
    return exc


def _conversation_response(conversation: Any) -> ChatConversationResponse:
    return ChatConversationResponse.model_validate(conversation.model_dump(mode="python"))


def _message_response(message: Any) -> ChatMessageResponse:
    payload = message.model_dump(mode="python")
    payload.pop("idempotency_key", None)
    return ChatMessageResponse.model_validate(payload)


@router.post(
    "/conversations",
    response_model=ChatConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_reject_user_id_query)],
)
async def create_conversation(
    request: ChatConversationCreateRequest,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        conversation = db.chat_repository.create_conversation(
            user_id=user_id,
            language=request.language,
            scenario_id=request.scenario_id,
            title=request.title,
            lesson_id=request.lesson_id,
        )
    except Exception as exc:  # pragma: no cover - covered by typed mapping assertions
        raise _map_chat_error(exc) from exc
    return {"success": True, "conversation": _conversation_response(conversation)}


@router.get(
    "/conversations",
    response_model=ChatConversationListResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def list_conversations(
    language: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        conversations = db.chat_repository.list_conversations(user_id=user_id, language=language, limit=limit)
    except Exception as exc:  # pragma: no cover - covered by typed mapping assertions
        raise _map_chat_error(exc) from exc
    return {
        "success": True,
        "count": len(conversations),
        "conversations": [_conversation_response(conversation) for conversation in conversations],
    }


@router.get(
    "/scenarios",
    response_model=ChatScenarioListResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def get_scenarios(
    language: str = Query(...),
):
    try:
        normalized_language = db.chat_repository._normalize_language(language)
    except Exception as exc:  # pragma: no cover
        raise _map_chat_error(exc) from exc
    return {
        "success": True,
        "scenarios": [
            ChatScenarioResponse.model_validate(item) for item in list_scenarios(normalized_language)
        ],
    }


@router.get(
    "/conversations/{conversation_id}",
    response_model=ChatConversationDetailResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        conversation = db.chat_repository.get_conversation(conversation_id=conversation_id, user_id=user_id)
    except Exception as exc:  # pragma: no cover
        raise _map_chat_error(exc) from exc
    return {"success": True, "conversation": _conversation_response(conversation)}


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ChatConversationDetailResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def update_conversation(
    conversation_id: str,
    request: ChatConversationUpdateRequest,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        conversation = db.chat_repository.update_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            title=request.title if "title" in request.model_fields_set else None,
            lesson_id=request.lesson_id,
            set_lesson_id="lesson_id" in request.model_fields_set,
            summary=request.summary,
            summary_through_sequence=request.summary_through_sequence,
            set_summary="summary" in request.model_fields_set,
        )
    except Exception as exc:  # pragma: no cover
        raise _map_chat_error(exc) from exc
    return {"success": True, "conversation": _conversation_response(conversation)}


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ChatConversationDeleteResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        db.chat_repository.delete_conversation(conversation_id=conversation_id, user_id=user_id)
    except Exception as exc:  # pragma: no cover
        raise _map_chat_error(exc) from exc
    return {"success": True, "message": "Conversation deleted", "conversation_id": conversation_id}


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageListResponse,
    dependencies=[Depends(_reject_user_id_query)],
)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    before_sequence: Optional[int] = Query(None, gt=0),
    after_sequence: Optional[int] = Query(None, gt=0),
    user_id: str = Depends(get_default_demo_user_id),
):
    try:
        page = db.chat_repository.get_messages_page(
            conversation_id=conversation_id,
            user_id=user_id,
            limit=limit,
            before_sequence=before_sequence,
            after_sequence=after_sequence,
        )

        return {
            "success": True,
            "messages": [_message_response(message) for message in page.messages],
            "limit": limit,
            "has_more": page.has_more,
            "next_before_sequence": page.next_before_sequence,
            "next_after_sequence": page.next_after_sequence,
        }
    except Exception as exc:  # pragma: no cover
        raise _map_chat_error(exc) from exc
