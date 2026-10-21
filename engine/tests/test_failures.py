from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from minutemate.asr import whisper as whisper_module
from minutemate.audio.ffmpeg import ensure_ffmpeg, preprocess
from minutemate.config import EngineConfig
from minutemate.errors import CancelledError, CudaUnavailableError, FfmpegError, InputError, ModelMissingError
from minutemate.events import NullEventSink
from minutemate.job import JobContext
from minutemate.pipeline import run


def _config(tmp_path: Path, **overrides) -> EngineConfig:
    audio = tmp_path / "in.wav"
    if not audio.exists():
        audio.write_bytes(b"RIFF")
    payload = {
        "audioPath": str(audio),
        "outputDirectory": str(tmp_path / "out"),
        "stem": "failure",
        "modelsDir": str(tmp_path / "models"),
    }
    payload.update(overrides)
    return EngineConfig.from_payload(payload)


def test_missing_audio_is_input_error(tmp_path):
    config = _config(tmp_path)
    Path(config.audio_path).unlink()

    with pytest.raises(InputError):
        config.validate()


def test_invalid_device_is_input_error(tmp_path):
    config = _config(tmp_path, device="tpu")

    with pytest.raises(InputError):
        config.resolved_device()


def test_missing_ffmpeg_is_reported():
    with pytest.raises(FfmpegError) as info:
        ensure_ffmpeg("mm-ffmpeg-does-not-exist")

    assert info.value.hint


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_corrupt_audio_fails_with_ffmpeg_error(tmp_path):
    broken = tmp_path / "broken.wav"
    broken.write_bytes(b"RIFF\x00\x00\x00\x00not-audio")

    with pytest.raises(FfmpegError):
        preprocess(broken, tmp_path / "out" / "clean.wav", ffmpeg_bin="ffmpeg")


def test_missing_models_block_run(tmp_path, monkeypatch):
    config = _config(tmp_path)
    monkeypatch.setattr("minutemate.pipeline.model_registry.verify", lambda *args, **kwargs: [Path("missing-model.bin")])

    with pytest.raises(ModelMissingError) as info:
        run(config, JobContext(config, NullEventSink()))

    assert "missing-model.bin" in (info.value.hint or "")


def test_cuda_load_failure_has_cpu_hint(tmp_path, monkeypatch):
    import faster_whisper

    def boom(*args, **kwargs):
        raise RuntimeError("cublas64_12.dll is not found")

    monkeypatch.setattr(faster_whisper, "WhisperModel", boom)
    config = _config(tmp_path)
    ctx = JobContext(config, NullEventSink())

    with pytest.raises(CudaUnavailableError) as info:
        whisper_module.transcribe(
            tmp_path / "clean.wav",
            tmp_path / "out",
            "failure",
            tmp_path / "models",
            "fa",
            "cuda",
            "float16",
            1,
            ctx,
        )

    assert "cpu" in (info.value.hint or "")


def test_cancel_is_cooperative(tmp_path):
    ctx = JobContext(_config(tmp_path), NullEventSink())
    ctx.cancel()

    with pytest.raises(CancelledError):
        ctx.check_cancel()


def test_preflight_reports_engine_version(tmp_path):
    from minutemate import __version__
    from minutemate.pipeline import preflight

    result = preflight(_config(tmp_path, modelsDir=str(tmp_path)))

    assert result["engineVersion"] == __version__
    assert result["batchSize"] == 0
    assert result["beamSize"] == 1
    assert "cudaAvailable" in result


def test_batch_size_is_parsed_and_validated(tmp_path):
    assert _config(tmp_path, batchSize=8).resolved_batch_size() == 8

    with pytest.raises(InputError):
        _config(tmp_path, batchSize=-1).validate()
    with pytest.raises(InputError):
        _config(tmp_path, batchSize=65).validate()


def test_batched_transcription_passes_batch_size(tmp_path, monkeypatch):
    import faster_whisper

    calls: dict[str, dict] = {}

    class FakeSegment:
        id = 0
        start = 0.0
        end = 1.0
        text = "سلام"
        words: list = []

    class FakeInfo:
        duration = 1.0
        language = "fa"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            calls["init"] = kwargs

        def transcribe(self, audio, **kwargs):
            calls["plain"] = kwargs
            return iter([FakeSegment()]), FakeInfo()

    class FakeBatched:
        def __init__(self, model):
            pass

        def transcribe(self, audio, **kwargs):
            calls["batched"] = kwargs
            return iter([FakeSegment()]), FakeInfo()

    monkeypatch.setattr(faster_whisper, "WhisperModel", FakeModel)
    monkeypatch.setattr(faster_whisper, "BatchedInferencePipeline", FakeBatched)
    ctx = JobContext(_config(tmp_path), NullEventSink())

    whisper_module.transcribe(
        tmp_path / "clean.wav",
        tmp_path / "out",
        "failure",
        tmp_path / "models",
        "fa",
        "cuda",
        "int8_float16",
        1,
        ctx,
        num_threads=6,
        batch_size=8,
    )

    assert calls["batched"]["batch_size"] == 8
    assert "plain" not in calls
    assert calls["init"]["cpu_threads"] == 0


def test_cuda_out_of_memory_is_recoverable(tmp_path, monkeypatch):
    import faster_whisper

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio, **kwargs):
            raise RuntimeError("CUDA out of memory. Tried to allocate ...")

    monkeypatch.setattr(faster_whisper, "WhisperModel", FakeModel)
    ctx = JobContext(_config(tmp_path), NullEventSink())

    with pytest.raises(CudaUnavailableError) as info:
        whisper_module.transcribe(
            tmp_path / "clean.wav",
            tmp_path / "out",
            "failure",
            tmp_path / "models",
            "fa",
            "cuda",
            "float16",
            1,
            ctx,
        )

    assert "batchSize" in (info.value.hint or "")


def test_cuda_transcription_falls_back_to_cpu(tmp_path, monkeypatch):
    calls: list[tuple[str, str]] = []

    def fake_transcribe(*args, **kwargs):
        device = kwargs["device"]
        compute_type = kwargs["compute_type"]
        calls.append((device, compute_type))
        if device == "cuda":
            raise CudaUnavailableError("cublas64_12.dll is not found", hint="cpu")
        return {"segments": []}

    monkeypatch.setattr(whisper_module, "transcribe", fake_transcribe)
    ctx = JobContext(_config(tmp_path), NullEventSink())

    result, device, compute_type = whisper_module.transcribe_with_fallback(
        tmp_path / "clean.wav",
        tmp_path / "out",
        "failure",
        tmp_path / "models",
        "fa",
        "cuda",
        "float16",
        1,
        ctx,
    )

    assert result == {"segments": []}
    assert (device, compute_type) == ("cpu", "int8")
    assert calls == [("cuda", "float16"), ("cpu", "int8")]


def test_cpu_failure_is_not_swallowed(tmp_path, monkeypatch):
    def fake_transcribe(*args, **kwargs):
        raise CudaUnavailableError("boom", hint="cpu")

    monkeypatch.setattr(whisper_module, "transcribe", fake_transcribe)
    ctx = JobContext(_config(tmp_path), NullEventSink())

    with pytest.raises(CudaUnavailableError):
        whisper_module.transcribe_with_fallback(
            tmp_path / "clean.wav",
            tmp_path / "out",
            "failure",
            tmp_path / "models",
            "fa",
            "cpu",
            "int8",
            1,
            ctx,
        )
