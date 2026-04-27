"""Shared API error helpers and handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


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


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
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


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = "; ".join(str(item.get("msg", "Validation error")) for item in errors) or "Validation failed"
    return JSONResponse(
        status_code=422,
        content=error_payload(message, "validation_error", detail=errors),
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
