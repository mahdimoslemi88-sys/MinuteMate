import json

import pytest

from minutemate.config import EngineConfig, MinutesConfig
from minutemate.errors import LlmAuthMissingError, LlmBadResponseError, MinutesParseError
from minutemate.events import NullEventSink
from minutemate.job import JobContext
from minutemate.minutes import stage


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0
        self.last_messages = None

    def complete(self, messages, *, temperature, max_tokens, timeout):
        self.calls += 1
        self.last_messages = messages
        payload = self.payloads[min(self.calls - 1, len(self.payloads) - 1)]
        if isinstance(payload, Exception):
            raise payload
        return payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)


GOOD_PAYLOAD = {
    "summary": "خلاصهٔ جلسه",
    "topics": [{"title": "بودجه", "summary": "بحث بودجه", "utteranceIds": ["u0001"]}],
    "decisions": [{"text": "بودجه تصویب شد", "utteranceIds": ["u0001"]}],
    "actionItems": [
        {
            "title": "ارسال گزارش",
            "ownerSpeakerId": "spk0",
            "dueText": "اول آبان",
            "dueDate": "2026-11-01",
            "priority": "high",
            "acceptanceCriteria": "گزارش ارسال شود",
            "utteranceIds": ["u0002"],
        }
    ],
    "openQuestions": [{"text": "میزان بودجه؟", "utteranceIds": ["u0001"]}],
}


def _config(**overrides):
    minutes = {
        "enabled": True,
        "provider": "openai-compatible",
        "baseUrl": "https://api.example.com/v1",
        "model": "gpt-x",
    }
    minutes.update(overrides)
    return EngineConfig(
        audio_path="audio.wav",
        output_dir="out",
        stem="session",
        minutes=MinutesConfig.from_payload(minutes),
    )


def _context(config):
    return JobContext(config, NullEventSink())


def _write_transcript(tmp_path, utterances=None):
    utterances = utterances or [
        {"speaker": 0, "start": 0.0, "end": 2.0, "text": "بودجه را تصویب کنیم"},
        {"speaker": 1, "start": 2.0, "end": 4.0, "text": "گزارش را می‌فرستم"},
    ]
    path = tmp_path / "session_transcript.json"
    path.write_text(json.dumps({"audio": "audio.wav", "utterances": utterances}, ensure_ascii=False), encoding="utf-8")
    return path


def _run(tmp_path, config, transcript=None):
    return stage.run_minutes(
        config=config,
        ctx=_context(config),
        transcript_path=transcript or _write_transcript(tmp_path),
        out_dir=tmp_path,
        stem="session",
        title="جلسهٔ بودجه",
        date_str="2026-10-20",
        duration=3600.0,
        speaker_map={0: {"name": "مهدی", "role": "سرپرست"}},
    )


def test_disabled_minutes_stage_returns_nothing(tmp_path, monkeypatch):
    config = _config(enabled=False)
    monkeypatch.setattr(stage, "create_provider", lambda minutes: pytest.fail("provider must not be created"))
    assert _run(tmp_path, config) == []
    assert not (tmp_path / "session.minutes.json").exists()


def test_stage_writes_all_artifacts(tmp_path, monkeypatch):
    provider = FakeProvider([GOOD_PAYLOAD])
    monkeypatch.setattr(stage, "create_provider", lambda minutes: provider)

    paths = _run(tmp_path, _config())

    names = [path.name for path in paths]
    assert names == [
        "03_official_meeting_minutes.md",
        "04_action_items.md",
        "session.minutes.json",
    ]
    document = json.loads((tmp_path / "session.minutes.json").read_text(encoding="utf-8"))
    assert document["schemaVersion"] == 1
    assert document["speakers"] == [
        {"speakerId": "spk0", "name": "مهدی", "role": "سرپرست", "source": "speakerMap"},
        {"speakerId": "spk1", "name": "گوینده 2", "role": "", "source": "auto"},
    ]
    assert document["actionItems"][0]["ownerName"] == "مهدی"
    assert document["source"]["provider"] == "fake"
    assert document["source"]["chunkCount"] == 1

    minutes_md = (tmp_path / "03_official_meeting_minutes.md").read_text(encoding="utf-8")
    assert "بودجه تصویب شد" in minutes_md
    assert "ماتریس مسئولیت" in (tmp_path / "04_action_items.md").read_text(encoding="utf-8")


def test_stage_skips_action_items_when_disabled(tmp_path, monkeypatch):
    provider = FakeProvider([GOOD_PAYLOAD])
    monkeypatch.setattr(stage, "create_provider", lambda minutes: provider)

    paths = _run(tmp_path, _config(includeActionItems=False))

    assert not (tmp_path / "04_action_items.md").exists()
    assert [path.name for path in paths] == ["03_official_meeting_minutes.md", "session.minutes.json"]


def test_stage_records_needs_review(tmp_path, monkeypatch):
    payload = dict(GOOD_PAYLOAD)
    payload["decisions"] = [{"text": "بدون شاهد", "utteranceIds": ["u9999"]}]
    provider = FakeProvider([payload])
    monkeypatch.setattr(stage, "create_provider", lambda minutes: provider)

    _run(tmp_path, _config())

    document = json.loads((tmp_path / "session.minutes.json").read_text(encoding="utf-8"))
    assert document["decisions"] == []
    assert document["needsReview"]


def test_stage_retries_bad_response_once(tmp_path, monkeypatch):
    provider = FakeProvider(["garbage", "still garbage"])
    monkeypatch.setattr(stage, "create_provider", lambda minutes: provider)

    with pytest.raises(LlmBadResponseError):
        _run(tmp_path, _config())

    assert provider.calls == 2


def test_stage_propagates_auth_error(tmp_path, monkeypatch):
    provider = FakeProvider([LlmAuthMissingError("no key")])
    monkeypatch.setattr(stage, "create_provider", lambda minutes: provider)

    with pytest.raises(LlmAuthMissingError):
        _run(tmp_path, _config())


def test_stage_requires_transcript(tmp_path, monkeypatch):
    provider = FakeProvider([GOOD_PAYLOAD])
    monkeypatch.setattr(stage, "create_provider", lambda minutes: provider)

    with pytest.raises(MinutesParseError):
        _run(tmp_path, _config(), transcript=tmp_path / "missing_transcript.json")
