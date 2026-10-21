from __future__ import annotations

import json

import pytest

from minutemate.config import EngineConfig
from minutemate.events import NullEventSink
from minutemate.job import JobContext
from minutemate.speed import SpeedProfile, default_rate, normalize_key


def _config(tmp_path) -> EngineConfig:
    audio = tmp_path / "in.wav"
    audio.write_bytes(b"RIFF")
    return EngineConfig.from_payload(
        {
            "audioPath": str(audio),
            "outputDirectory": str(tmp_path / "out"),
            "stem": "speed",
        }
    )


def test_default_rates_are_used_without_history(tmp_path):
    profile = SpeedProfile.load(tmp_path / "metrics")

    assert profile.stage_rate("cpu", "int8", "transcription") == default_rate("cpu", "transcription")
    assert profile.stage_rate("cuda", "float16", "transcription") == default_rate("cuda", "transcription")


def test_record_persists_median_rate(tmp_path):
    metrics = tmp_path / "metrics"
    profile = SpeedProfile.load(metrics)

    profile.record("cpu", "int8", {"transcription": 10.0, "diarization": 2.0}, duration=30.0)
    profile.record("cpu", "int8", {"transcription": 14.0, "diarization": 4.0}, duration=30.0)

    reloaded = SpeedProfile.load(metrics)
    assert reloaded.stage_rate("cpu", "int8", "transcription") == pytest.approx(0.4)
    assert reloaded.stage_rate("cpu", "int8", "diarization") == pytest.approx(0.1)

    payload = json.loads((metrics / "device_speed.json").read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == 1
    assert len(payload["profiles"][normalize_key("cpu", "int8")]["transcription"]) == 2


def test_record_keeps_last_five_samples(tmp_path):
    profile = SpeedProfile.load(tmp_path)

    for seconds in [3, 4, 5, 6, 7, 8]:
        profile.record("cpu", "int8", {"transcription": seconds}, duration=10.0)

    assert profile.profiles[normalize_key("cpu", "int8")]["transcription"] == [0.4, 0.5, 0.6, 0.7, 0.8]


def test_record_ignores_zero_duration_and_corrupt_file(tmp_path):
    profile = SpeedProfile.load(tmp_path)
    profile.record("cpu", "int8", {"transcription": 10.0}, duration=0.0)
    assert profile.profiles == {}

    path = tmp_path / "device_speed.json"
    path.write_text("{not json", encoding="utf-8")
    assert SpeedProfile.load(tmp_path).profiles == {}


def test_transcription_emits_history_based_eta(tmp_path, monkeypatch):
    import faster_whisper

    from minutemate.asr import whisper as whisper_module

    class FakeSegment:
        def __init__(self, end):
            self.id = 0
            self.start = 0.0
            self.end = end
            self.text = "سلام"
            self.words: list = []

    class FakeInfo:
        duration = 10.0
        language = "fa"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio, **kwargs):
            return iter([FakeSegment(2.0), FakeSegment(10.0)]), FakeInfo()

    class RecordingSink:
        def __init__(self):
            self.events = []

        def emit(self, event):
            self.events.append(event)

    monkeypatch.setattr(faster_whisper, "WhisperModel", FakeModel)
    sink = RecordingSink()
    ctx = JobContext(_config(tmp_path), sink)

    whisper_module.transcribe(
        tmp_path / "clean.wav",
        tmp_path / "out",
        "speed",
        tmp_path / "models",
        "fa",
        "cpu",
        "int8",
        1,
        ctx,
        eta_rate=0.5,
    )

    etas = [event.eta_seconds for event in sink.events if event.eta_seconds is not None]
    assert 5.0 in etas
    assert 4.0 in etas
    assert etas[-1] == 0.0


def test_job_context_records_stage_seconds(tmp_path):
    ctx = JobContext(_config(tmp_path), NullEventSink())

    ctx.stage_start("transcription")
    ctx.stage_done("transcription")

    assert ctx.stage_seconds["transcription"] >= 0
