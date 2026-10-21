import json
import socket

import pytest

from minutemate.config import MinutesConfig
from minutemate.errors import (
    InputError,
    LlmAuthMissingError,
    LlmBadResponseError,
    LlmTimeoutError,
    LlmUnavailableError,
)
from minutemate.minutes.provider import (
    OllamaProvider,
    OpenAiCompatibleProvider,
    create_provider,
)

MESSAGES = [{"role": "user", "content": "hi"}]


def _openai_config(**overrides) -> MinutesConfig:
    data = {
        "enabled": True,
        "provider": "openai-compatible",
        "baseUrl": "https://api.example.com/v1",
        "model": "gpt-x",
    }
    data.update(overrides)
    return MinutesConfig.from_payload(data)


def test_create_provider_rejects_none():
    with pytest.raises(InputError):
        create_provider(MinutesConfig.from_payload({"enabled": True, "provider": "none"}))


def test_openai_requires_api_key_env(monkeypatch):
    monkeypatch.delenv("MINUTEMATE_LLM_API_KEY", raising=False)
    with pytest.raises(LlmAuthMissingError):
        OpenAiCompatibleProvider(_openai_config())


def test_openai_sends_bearer_and_parses_content(monkeypatch):
    monkeypatch.setenv("MINUTEMATE_LLM_API_KEY", "secret")
    captured = {}

    def transport(request, timeout):
        captured["url"] = request.full_url
        captured["auth"] = request.headers.get("Authorization")
        captured["timeout"] = timeout
        body = {"choices": [{"message": {"content": "hello"}}]}
        return 200, json.dumps(body)

    provider = OpenAiCompatibleProvider(_openai_config(), transport)
    result = provider.complete(MESSAGES, temperature=0.2, max_tokens=100, timeout=30)

    assert result == "hello"
    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["auth"] == "Bearer secret"
    assert captured["timeout"] == 30


def test_openai_maps_auth_status(monkeypatch):
    monkeypatch.setenv("MINUTEMATE_LLM_API_KEY", "secret")
    provider = OpenAiCompatibleProvider(_openai_config(), lambda request, timeout: (401, "nope"))
    with pytest.raises(LlmAuthMissingError):
        provider.complete(MESSAGES, temperature=0.2, max_tokens=100, timeout=30)


def test_openai_maps_server_error(monkeypatch):
    monkeypatch.setenv("MINUTEMATE_LLM_API_KEY", "secret")
    provider = OpenAiCompatibleProvider(_openai_config(), lambda request, timeout: (503, "down"))
    with pytest.raises(LlmUnavailableError):
        provider.complete(MESSAGES, temperature=0.2, max_tokens=100, timeout=30)


def test_openai_maps_timeout(monkeypatch):
    monkeypatch.setenv("MINUTEMATE_LLM_API_KEY", "secret")

    def transport(request, timeout):
        raise socket.timeout("too slow")

    provider = OpenAiCompatibleProvider(_openai_config(), transport)
    with pytest.raises(LlmTimeoutError):
        provider.complete(MESSAGES, temperature=0.2, max_tokens=100, timeout=30)


def test_openai_maps_bad_body(monkeypatch):
    monkeypatch.setenv("MINUTEMATE_LLM_API_KEY", "secret")
    provider = OpenAiCompatibleProvider(_openai_config(), lambda request, timeout: (200, "not json"))
    with pytest.raises(LlmBadResponseError):
        provider.complete(MESSAGES, temperature=0.2, max_tokens=100, timeout=30)


def test_ollama_uses_default_local_url():
    config = MinutesConfig.from_payload({"enabled": True, "provider": "ollama", "model": "llama3"})
    captured = {}

    def transport(request, timeout):
        captured["url"] = request.full_url
        return 200, json.dumps({"message": {"content": "ok"}})

    provider = OllamaProvider(config, transport)
    result = provider.complete(MESSAGES, temperature=0.2, max_tokens=100, timeout=30)

    assert result == "ok"
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
