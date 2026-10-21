from minutemate.config import EngineConfig, MinutesConfig
from minutemate.errors import InputError
import pytest


def test_minutes_defaults_are_disabled():
    minutes = MinutesConfig.from_payload(None)
    assert minutes.enabled is False
    assert minutes.provider == "none"
    assert minutes.is_active() is False


def test_minutes_rejects_inline_api_key():
    with pytest.raises(InputError):
        MinutesConfig.from_payload({"enabled": True, "provider": "openai-compatible", "apiKey": "secret"})
    with pytest.raises(InputError):
        MinutesConfig.from_payload({"api_key": "secret"})


def test_minutes_validate_requires_model_when_active():
    minutes = MinutesConfig.from_payload(
        {"enabled": True, "provider": "openai-compatible", "baseUrl": "https://api.example.com"}
    )
    with pytest.raises(InputError):
        minutes.validate()


def test_minutes_validate_rejects_insecure_remote_url():
    minutes = MinutesConfig.from_payload(
        {
            "enabled": True,
            "provider": "openai-compatible",
            "baseUrl": "http://api.example.com",
            "model": "gpt-x",
        }
    )
    with pytest.raises(InputError):
        minutes.validate()


def test_minutes_validate_allows_local_http_and_https():
    local = MinutesConfig.from_payload(
        {"enabled": True, "provider": "ollama", "model": "llama3", "baseUrl": "http://127.0.0.1:11434"}
    )
    local.validate()
    assert local.base_url == "http://127.0.0.1:11434"

    remote = MinutesConfig.from_payload(
        {
            "enabled": True,
            "provider": "openai-compatible",
            "model": "gpt-x",
            "baseUrl": "https://api.example.com/v1",
        }
    )
    remote.validate()


def test_minutes_rejects_unknown_provider():
    minutes = MinutesConfig.from_payload({"enabled": True, "provider": "telepathy"})
    with pytest.raises(InputError):
        minutes.validate()


def test_engine_config_parses_minutes_block():
    config = EngineConfig.from_payload(
        {
            "audioPath": "a.wav",
            "outputDirectory": "out",
            "minutes": {"enabled": True, "provider": "ollama", "model": "llama3", "chunkSeconds": 300},
        }
    )
    assert config.minutes.enabled is True
    assert config.minutes.provider == "ollama"
    assert config.minutes.chunk_seconds == 300
