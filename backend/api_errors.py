"""Shared API error helpers and handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from models import ApiErrorPayload

logger = logging.getLogger(__name__)


COMMON_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ApiErrorPayload, "description": "Bad request"},
    409: {"model": ApiErrorPayload, "description": "Conflict"},
    404: {"model": ApiErrorPayload, "description": "Not found"},
    413: {"model": ApiErrorPayload, "description": "Payload too large"},
    422: {"model": ApiErrorPayload, "description": "Validation error"},
    500: {"model": ApiErrorPayload, "description": "Internal server error"},
    503: {"model": ApiErrorPayload, "description": "Service unavailable"},
}


class ApiHTTPException(HTTPException):
    def __init__(self, status_code: int, message: str, code: str) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.code = code


def error_payload(message: str, code: str, *, detail: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": True,
        "message": message,
        "code": code,
    }
    if detail is not None:
        payload["detail"] = detail
    return payload


def api_error(status_code: int, message: str, code: str) -> HTTPException:
    return ApiHTTPException(status_code=status_code, message=message, code=code)


async def http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, HTTPException):
        return await unhandled_exception_handler(_, exc)
    detail = exc.detail
    if isinstance(exc, ApiHTTPException):
        payload = error_payload(exc.message, exc.code, detail=exc.message)
    elif isinstance(detail, dict) and {"error", "message", "code"}.issubset(detail.keys()):
        payload = detail
    elif isinstance(detail, str):
        payload = error_payload(detail, _default_code_for_status(exc.status_code), detail=detail)
    else:
        payload = error_payload(
            "Request failed",
            _default_code_for_status(exc.status_code),
            detail=detail,
        )
    return JSONResponse(status_code=exc.status_code, content=payload)


async def validation_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await unhandled_exception_handler(_, exc)
    errors = jsonable_encoder(exc.errors())
    message = "; ".join(str(item.get("msg", "Validation error")) for item in errors) or "Validation failed"
    code = _validation_error_code(_, errors)
    if code == "invalid_chat_language":
        bad_language = _extract_invalid_chat_language(errors)
        message = f"Unsupported chat language: {bad_language}" if bad_language else "Unsupported chat language"
    return JSONResponse(
        status_code=422,
        content=error_payload(message, code, detail=errors),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_request_error", extra={"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=500,
        content=error_payload(
            "Internal server error",
            "internal_server_error",
            detail="Internal server error",
        ),
    )


def _default_code_for_status(status_code: int) -> str:
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        500: "internal_server_error",
        503: "service_unavailable",
    }
    return mapping.get(status_code, f"http_{status_code}")


def _validation_error_code(request: Request, errors: list[dict[str, Any]]) -> str:
    if request.url.path.startswith("/api/chat/") and _extract_invalid_chat_language(errors) is not None:
        return "invalid_chat_language"
    if request.url.path.startswith("/api/chat/") and _extract_invalid_chat_scenario(errors) is not None:
        return "invalid_chat_scenario"
    if request.url.path.startswith("/api/learning-sessions"):
        return _learning_session_validation_error_code(errors)
    return "validation_error"


def _learning_session_validation_error_code(errors: list[dict[str, Any]]) -> str:
    if any("learning_session_semantics:" in str(item.get("msg", "")) for item in errors):
        return "invalid_learning_session_semantics"
    field_names = {str(loc[-1]) for item in errors if (loc := item.get("loc")) and isinstance(loc, (list, tuple))}
    if "user_id" in field_names:
        return "user_id_not_allowed"
    if "language" in field_names:
        return "invalid_learning_session_language"
    if "event_type" in field_names:
        return "invalid_learning_session_event_type"
    if "entity_type" in field_names:
        return "invalid_learning_session_entity_type"
    if "cursor" in field_names or "limit" in field_names:
        return "invalid_learning_session_pagination"
    if "metadata" in field_names:
        return "invalid_learning_session_metadata"
    return "validation_error"


def _extract_invalid_chat_language(errors: list[dict[str, Any]]) -> str | None:
    for item in errors:
        loc = item.get("loc") or ()
        if not isinstance(loc, (list, tuple)) or not loc:
            continue
        if loc[-1] != "language":
            continue
        if item.get("type") != "literal_error":
            continue
        value = item.get("input")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _extract_invalid_chat_scenario(errors: list[dict[str, Any]]) -> str | None:
    for item in errors:
        loc = item.get("loc") or ()
        if not isinstance(loc, (list, tuple)) or not loc:
            continue
        if loc[-1] != "scenario_id":
            continue
        if item.get("type") not in {"literal_error", "value_error"}:
            continue
        value = item.get("input")
        if isinstance(value, str) and value.strip():
            return value
    return None
