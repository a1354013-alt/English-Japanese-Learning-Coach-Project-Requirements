"""
Async Ollama client for Language Coach.

Uses httpx.AsyncClient so LLM calls yield the event loop instead of blocking it.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, Literal, Optional, Union

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Per-operation timeouts (connect vs read tuned for local Ollama + large payloads)
HEALTH_CHECK_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
CHAT_TIMEOUT = httpx.Timeout(120.0, connect=10.0, read=120.0)
STRUCTURED_JSON_TIMEOUT = httpx.Timeout(240.0, connect=15.0, read=240.0)
LESSON_GENERATION_TIMEOUT = httpx.Timeout(600.0, connect=30.0, read=600.0)

GenerateTimeoutProfile = Literal["chat", "structured_json", "lesson"]


def _timeout_for_profile(profile: Union[GenerateTimeoutProfile, Literal["health"]]) -> httpx.Timeout:
    if profile == "health":
        return HEALTH_CHECK_TIMEOUT
    if profile == "chat":
        return CHAT_TIMEOUT
    if profile == "lesson":
        return LESSON_GENERATION_TIMEOUT
    return STRUCTURED_JSON_TIMEOUT


class OllamaClient:
    """Async client for Ollama HTTP API (streaming generate + tags health)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        max_retries: int = 1,
    ) -> None:
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model_name = model_name or settings.model_name
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
            )
            logger.debug("ollama_async_client_created", extra={"base_url": self.base_url})
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("ollama_async_client_closed")
        self._client = None

    async def _stream_generate(
        self,
        data: Dict[str, Any],
        timeout: httpx.Timeout,
    ) -> str:
        """
        POST /api/generate with stream=true and concatenate JSON line payloads.
        """
        client = await self._get_client()
        full_response = ""
        async with client.stream("POST", "/api/generate", json=data, timeout=timeout) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    if "response" in chunk:
                        full_response += chunk["response"]
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    logger.debug(
                        "ollama_stream_non_json_line",
                        extra={"preview": line[:120]},
                    )
                    continue
        return full_response

    async def _make_generate_request(
        self,
        data: Dict[str, Any],
        timeout: httpx.Timeout,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        try:
            text = await self._stream_generate(data, timeout)
            return {"response": text, "success": True}
        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_http_status_error",
                extra={
                    "status_code": e.response.status_code,
                    "path": "/api/generate",
                    "retry_count": retry_count,
                },
            )
            return {
                "response": "",
                "success": False,
                "error": f"HTTP {e.response.status_code} from Ollama",
            }
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            return await self._retry_or_fail_generate(
                data, timeout, retry_count, e, error_label="connect"
            )
        except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
            return await self._retry_or_fail_generate(
                data, timeout, retry_count, e, error_label="timeout"
            )
        except httpx.RequestError as e:
            logger.error(
                "ollama_request_error",
                extra={"error": str(e), "retry_count": retry_count},
            )
            return {"response": "", "success": False, "error": f"Request failed: {e!s}"}
        except Exception as e:
            logger.exception("ollama_unexpected_error")
            return {"response": "", "success": False, "error": f"Unexpected error: {e!s}"}

    async def _retry_or_fail_generate(
        self,
        data: Dict[str, Any],
        timeout: httpx.Timeout,
        retry_count: int,
        exc: Exception,
        *,
        error_label: str,
    ) -> Dict[str, Any]:
        if retry_count < self.max_retries:
            logger.warning(
                "ollama_retry_scheduled",
                extra={
                    "attempt": retry_count + 1,
                    "max_retries": self.max_retries,
                    "reason": error_label,
                    "error": str(exc),
                },
            )
            await asyncio.sleep(1.0)
            return await self._make_generate_request(data, timeout, retry_count + 1)
        logger.error(
            "ollama_retries_exhausted",
            extra={
                "reason": error_label,
                "error": str(exc),
                "retries": self.max_retries,
            },
        )
        return {
            "response": "",
            "success": False,
            "error": f"{error_label} failed after {self.max_retries} retries: {exc!s}",
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        format: str = "json",
        model: Optional[str] = None,
        use_cache: bool = True,
        timeout_profile: GenerateTimeoutProfile = "structured_json",
    ) -> Dict[str, Any]:
        """
        Run Ollama /api/generate with async streaming.

        timeout_profile:
          - lesson: long read for full lesson JSON
          - structured_json: writing analysis, study plans, etc.
          - chat: WebSocket turns (plain text)
        """
        target_model = model or self.model_name
        timeout = _timeout_for_profile(timeout_profile)
        cache_key: Optional[str] = None

        if use_cache:
            from cache import cache

            # Include temperature and format in cache key to avoid collisions
            cache_key = (
                f"ollama:{target_model}:{format}:{temperature}:"
                f"{hashlib.md5((prompt + (system_prompt or '')).encode()).hexdigest()}"
            )
            cached_res = cache.get(cache_key)
            if cached_res:
                logger.debug("ollama_cache_hit", extra={"model": target_model})
                return cached_res

        data: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            data["system"] = system_prompt
        if format == "json":
            data["format"] = "json"

        result = await self._make_generate_request(data, timeout)

        if use_cache and cache_key and result.get("success"):
            from cache import cache

            cache.set(cache_key, result)

        return result

    async def check_model_availability(self, model_name: Optional[str] = None) -> bool:
        """GET /api/tags with a short timeout (health checks only)."""
        timeout = _timeout_for_profile("health")
        target_model = model_name or self.model_name
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=timeout)
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            ready = any(target_model in name for name in model_names)
            if not ready:
                logger.warning(
                    "ollama_model_missing",
                    extra={"expected": target_model, "available": model_names},
                )
            return ready
        except httpx.HTTPStatusError as e:
            logger.warning(
                "ollama_health_http_error",
                extra={"status_code": e.response.status_code},
            )
            return False
        except httpx.RequestError as e:
            logger.warning("ollama_health_request_failed", extra={"error": str(e)})
            return False
        except Exception as e:
            logger.exception("ollama_health_unexpected", extra={"error": str(e)})
            return False

    @staticmethod
    def parse_json_response(response_text: str) -> Optional[Dict[str, Any]]:
        if not response_text:
            return None
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        if "```json" in response_text:
            try:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        return None


ollama_client = OllamaClient()
