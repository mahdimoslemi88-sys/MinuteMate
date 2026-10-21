"""LLM providers for the minutes stage (OpenAI-compatible and Ollama)."""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Callable, Protocol

from minutemate.config import DEFAULT_API_KEY_ENV, MINUTES_PROVIDERS, MinutesConfig
from minutemate.errors import (
    InputError,
    LlmAuthMissingError,
    LlmBadResponseError,
    LlmTimeoutError,
    LlmUnavailableError,
)

Transport = Callable[[urllib.request.Request, int], "tuple[int, str]"]


def default_transport(request: urllib.request.Request, timeout: int) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")


class LlmProvider(Protocol):
    name: str
    model: str

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> str: ...


class _HttpProvider:
    name = "http"
    endpoint = ""

    def __init__(self, config: MinutesConfig, transport: Transport | None = None) -> None:
        self.model = config.model or ""
        self.transport = transport or default_transport

    def complete(
        self,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> str:
        request = self._build_request(messages, temperature, max_tokens)

        try:
            status, body = self.transport(request, timeout)
        except socket.timeout as error:
            raise LlmTimeoutError("مهلت پاسخ سرویس LLM به پایان رسید.") from error
        except TimeoutError as error:
            raise LlmTimeoutError("مهلت پاسخ سرویس LLM به پایان رسید.") from error
        except urllib.error.URLError as error:
            if isinstance(getattr(error, "reason", None), (socket.timeout, TimeoutError)):
                raise LlmTimeoutError("مهلت پاسخ سرویس LLM به پایان رسید.") from error
            raise LlmUnavailableError("اتصال به سرویس LLM برقرار نشد.") from error
        except OSError as error:
            raise LlmUnavailableError("اتصال به سرویس LLM برقرار نشد.") from error

        if status in (401, 403):
            raise LlmAuthMissingError(
                "سرویس LLM درخواست را رد کرد (کلید نامعتبر یا بدون دسترسی).",
                hint="مقدار متغیر محیطی کلید را بررسی کنید.",
            )

        if status < 200 or status >= 300:
            raise LlmUnavailableError(f"سرویس LLM پاسخ {status} برگرداند.")

        return self._extract_content(body)

    def _build_request(self, messages: list[dict], temperature: float, max_tokens: int) -> urllib.request.Request:
        raise NotImplementedError

    def _extract_content(self, body: str) -> str:
        raise NotImplementedError


class OpenAiCompatibleProvider(_HttpProvider):
    name = "openai-compatible"

    def __init__(self, config: MinutesConfig, transport: Transport | None = None) -> None:
        super().__init__(config, transport)
        self._base_url = (config.base_url or "").rstrip("/")
        key_env = config.api_key_env or DEFAULT_API_KEY_ENV
        api_key = os.environ.get(key_env) if key_env else None
        if not api_key:
            raise LlmAuthMissingError(
                f"متغیر محیطی {key_env} تنظیم نشده است.",
                hint=f"برای ارسال متن به سرویس LLM مقدار {key_env} را تنظیم کنید.",
            )
        self._api_key = api_key

    def _build_request(self, messages: list[dict], temperature: float, max_tokens: int) -> urllib.request.Request:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        ).encode("utf-8")
        return urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

    def _extract_content(self, body: str) -> str:
        try:
            payload = json.loads(body)
            return payload["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            raise LlmBadResponseError(
                "پاسخ سرویس LLM ساختار مورد انتظار را نداشت.",
                hint="سرویس باید پاسخ سازگار با OpenAI برگرداند.",
            ) from error


class OllamaProvider(_HttpProvider):
    name = "ollama"

    def __init__(self, config: MinutesConfig, transport: Transport | None = None) -> None:
        super().__init__(config, transport)
        self._base_url = (config.base_url or "http://127.0.0.1:11434").rstrip("/")

    def _build_request(self, messages: list[dict], temperature: float, max_tokens: int) -> urllib.request.Request:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
        ).encode("utf-8")
        return urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    def _extract_content(self, body: str) -> str:
        try:
            payload = json.loads(body)
            return payload["message"]["content"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise LlmBadResponseError(
                "پاسخ Ollama ساختار مورد انتظار را نداشت.",
            ) from error


def create_provider(config: MinutesConfig, transport: Transport | None = None) -> LlmProvider:
    provider = (config.provider or "none").lower()

    if provider not in MINUTES_PROVIDERS:
        raise InputError(f"provider نامعتبر: {provider}", hint="مقادیر مجاز: none, openai-compatible, ollama")

    if provider == "none":
        raise InputError("provider=none است؛ مرحلهٔ صورتجلسه غیرفعال است.")

    if provider == "openai-compatible":
        return OpenAiCompatibleProvider(config, transport)

    return OllamaProvider(config, transport)
