from pathlib import Path

from minutemate.config import EngineConfig
from minutemate.events import EventType
from minutemate.job import JobContext
from minutemate.pipeline import _download_missing_models


class RecordingSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


def test_download_missing_models_reports_progress(tmp_path, monkeypatch):
    import minutemate.models.downloader as downloader

    def fake_download(groups, models_dir=None, progress=None, cancel=None, log=None):
        progress("whisper/model.bin", 50, 100)
        return []

    monkeypatch.setattr(downloader, "download_groups", fake_download)
    sink = RecordingSink()
    config = EngineConfig(
        audio_path=str(tmp_path / "input.wav"),
        output_dir=str(tmp_path / "out"),
        auto_download_models=True,
    )
    ctx = JobContext(config, sink)

    class Missing:
        rel_path = "whisper/model.bin"

    _download_missing_models(config, ctx, [Missing()])

    stages = [event for event in sink.events if event.type == EventType.STAGE]
    assert stages[0].stage == "models"
    assert any(event.progress and event.progress > 0.4 for event in stages)
    assert stages[-1].status == "done"
    assert ctx.stage_seconds["models"] >= 0
