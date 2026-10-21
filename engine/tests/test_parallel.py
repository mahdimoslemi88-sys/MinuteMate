import io
import json
import threading
from pathlib import Path

import pytest

from minutemate.config import EngineConfig
from minutemate.errors import InputError
from minutemate.events import EngineEvent, EventType, JsonEventSink
from minutemate.job import JobContext
from minutemate.models import registry


class RecordingSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


def _config(tmp_path: Path, **overrides) -> EngineConfig:
    values = {
        "audio_path": str(tmp_path / "input.wav"),
        "output_dir": str(tmp_path / "out"),
        "stem": "parallel",
    }
    values.update(overrides)
    return EngineConfig(**values)


def test_parallel_resolution_follows_device(tmp_path):
    config = _config(tmp_path)

    assert config.resolved_parallel("cuda") is True
    assert config.resolved_parallel("cpu") is False
    assert _config(tmp_path, parallel_stages="on").resolved_parallel("cpu") is True
    assert _config(tmp_path, parallel_stages="off").resolved_parallel("cuda") is False


def test_parallel_value_validation(tmp_path):
    with pytest.raises(InputError):
        _config(tmp_path, parallel_stages="sometimes").validate()


def test_parallel_stages_keep_separate_progress(tmp_path):
    sink = RecordingSink()
    ctx = JobContext(_config(tmp_path), sink)

    ctx.stage_progress("diarization", 0.2, force=True)
    ctx.stage_progress("transcription", 0.2)

    stages = [event.stage for event in sink.events if event.type == EventType.STAGE]
    assert stages == ["diarization", "transcription"]


def test_json_sink_writes_whole_lines_across_threads():
    stream = io.StringIO()
    sink = JsonEventSink(stream)

    def _event(index: int) -> EngineEvent:
        return EngineEvent(type=EventType.LOG, message=f"line-{index}")

    def worker(start: int) -> None:
        for index in range(start, start + 50):
            sink.emit(_event(index))

    threads = [threading.Thread(target=worker, args=(index * 50,)) for index in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lines = stream.getvalue().splitlines()
    assert len(lines) == 200
    assert all(json.loads(line)["message"].startswith("line-") for line in lines)


def test_registry_selects_speaker_embedding(tmp_path):
    default = registry.resolve(tmp_path)
    alternative = registry.resolve(tmp_path, "3dspeaker")

    assert default.speaker_embedding.name.startswith("wespeaker")
    assert alternative.speaker_embedding.name.startswith("3dspeaker")
    with pytest.raises(InputError):
        registry.resolve(tmp_path, "missing-model.onnx")
