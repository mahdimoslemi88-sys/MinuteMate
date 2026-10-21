import wave
from pathlib import Path

import numpy as np

from minutemate.asr import whisper as whisper_module
from minutemate.config import EngineConfig
from minutemate.events import NullEventSink
from minutemate.job import JobContext


def _config(tmp_path: Path) -> EngineConfig:
    return EngineConfig(
        audio_path=str(tmp_path / "input.wav"),
        output_dir=str(tmp_path / "out"),
        stem="long",
        device="cpu",
        compute_type="int8",
        asr_chunk_seconds=2.0,
        asr_chunk_overlap_seconds=0.5,
    )


def _write_wav(path: Path, seconds: float, sample_rate: int = 16000) -> None:
    samples = (np.sin(np.linspace(0, 40, int(seconds * sample_rate))) * 8000).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())


def test_chunk_windows_short_audio_is_single_window():
    assert whisper_module.chunk_windows(60.0, 1800.0, 5.0) == [(0.0, 60.0)]
    assert whisper_module.chunk_windows(60.0, 0.0, 5.0) == [(0.0, 60.0)]


def test_chunk_windows_overlaps_and_covers_two_hours():
    windows = whisper_module.chunk_windows(7200.0, 1800.0, 5.0)

    assert windows[0] == (0.0, 1800.0)
    assert windows[-1] == (5385.0, 7200.0)
    assert len(windows) == 4
    assert windows[1][0] == 1795.0


def test_merge_chunk_records_drops_overlap_duplicates():
    chunks = [
        [
            {"id": 0, "start": 0.0, "end": 10.0, "text": "الف", "words": []},
            {"id": 1, "start": 10.0, "end": 14.0, "text": "ب", "words": []},
        ],
        [
            {"id": 0, "start": 9.0, "end": 13.0, "text": "تکراری", "words": []},
            {"id": 1, "start": 12.0, "end": 17.0, "text": "ج", "words": []},
        ],
    ]

    merged = whisper_module.merge_chunk_records(chunks)

    assert [record["text"] for record in merged] == ["الف", "ب", "ج"]
    assert [record["id"] for record in merged] == [0, 1, 2]


def test_transcribe_chunks_long_audio_with_offsets(tmp_path, monkeypatch):
    import faster_whisper

    audio = tmp_path / "long.wav"
    _write_wav(audio, 5.0)

    class FakeSegment:
        id = 0
        start = 0.0
        end = 1.9
        text = "سلام"
        words: list = []

    class FakeInfo:
        duration = 2.0
        language = "fa"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, path, **kwargs):
            return iter([FakeSegment()]), FakeInfo()

    monkeypatch.setattr(faster_whisper, "WhisperModel", FakeModel)
    config = _config(tmp_path)
    ctx = JobContext(config, NullEventSink())

    result = whisper_module.transcribe(
        audio,
        tmp_path / "work",
        "long",
        tmp_path / "models",
        "fa",
        "cpu",
        "int8",
        1,
        ctx,
        chunk_seconds=2.0,
        overlap_seconds=0.5,
    )

    assert [segment["start"] for segment in result["segments"]] == [0.0, 1.5, 3.0]
    assert [segment["id"] for segment in result["segments"]] == [0, 1, 2]
    assert result["duration"] == 5.0
    assert not list((tmp_path / "work").glob("*.chunk-*.wav"))
    assert (tmp_path / "work" / "long.segments.json").exists()
