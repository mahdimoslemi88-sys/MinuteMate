"""FFmpeg/ffprobe helpers with progress reporting and cancellation."""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from minutemate.errors import CancelledError, FfmpegError


@dataclass(frozen=True)
class AudioInfo:
    duration: float
    sample_rate: int
    channels: int


def _resolve(binary: str) -> str:
    resolved = shutil.which(binary)
    if resolved:
        return resolved
    if Path(binary).exists():
        return binary
    return ""


def ensure_ffmpeg(ffmpeg_bin: str = "ffmpeg") -> str:
    resolved = _resolve(ffmpeg_bin)
    if not resolved:
        raise FfmpegError(
            f"برنامه FFmpeg پیدا نشد: {ffmpeg_bin}",
            hint="FFmpeg را نصب کنید یا مسیر آن را با --ffmpeg مشخص کنید.",
        )
    return resolved


def _probe_binary(ffmpeg_bin: str) -> str:
    ffmpeg_path = _resolve(ffmpeg_bin)
    if ffmpeg_path:
        candidate = Path(ffmpeg_path).with_name(Path(ffmpeg_path).name.replace("ffmpeg", "ffprobe"))
        if candidate.exists():
            return str(candidate)
    return _resolve("ffprobe")


def probe(input_path: str | Path, ffmpeg_bin: str = "ffmpeg") -> AudioInfo:
    ensure_ffmpeg(ffmpeg_bin)
    ffprobe = _probe_binary(ffmpeg_bin)
    if not ffprobe:
        return AudioInfo(0.0, 0, 0)

    command = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration:stream=sample_rate,channels",
        "-of", "json",
        str(input_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return AudioInfo(0.0, 0, 0)

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return AudioInfo(0.0, 0, 0)

    duration = float(payload.get("format", {}).get("duration") or 0.0)
    streams = payload.get("streams") or [{}]
    sample_rate = int(streams[0].get("sample_rate") or 0)
    channels = int(streams[0].get("channels") or 0)
    return AudioInfo(duration, sample_rate, channels)


def preprocess(
    input_path: str | Path,
    output_path: str | Path,
    ffmpeg_bin: str = "ffmpeg",
    target_lufs: float = -16.0,
    sample_rate: int = 16000,
    progress: Callable[[float], None] | None = None,
    cancel: Callable[[], bool] | None = None,
) -> Path:
    binary = ensure_ffmpeg(ffmpeg_bin)
    source = Path(input_path).resolve()
    target = Path(output_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    info = probe(source, ffmpeg_bin)
    audio_filter = "highpass=f=60"

    command = [
        binary,
        "-y",
        "-nostdin",
        "-i", str(source),
        "-af", audio_filter,
        "-ar", str(sample_rate),
        "-ac", "1",
        "-c:a", "pcm_s16le",
        "-progress", "pipe:1",
        "-nostats",
        "-loglevel", "error",
        str(target),
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    errors: list[str] = []

    def drain_stderr() -> None:
        assert process.stderr is not None
        for line in process.stderr:
            errors.append(line.rstrip())

    stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
    stderr_thread.start()

    assert process.stdout is not None
    for line in process.stdout:
        if cancel and cancel():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            stderr_thread.join(timeout=1)
            raise CancelledError()

        line = line.strip()
        if not line or progress is None or info.duration <= 0:
            continue
        if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
            value = line.split("=", 1)[1]
            if value.isdigit():
                seconds = int(value) / 1_000_000.0
                progress(min(1.0, seconds / info.duration))

    process.wait()
    stderr_thread.join(timeout=1)

    if process.returncode != 0:
        detail = "\n".join(errors[-8:]) if errors else "unknown error"
        raise FfmpegError(
            "پردازش صوتی با FFmpeg ناموفق بود.",
            hint=detail,
        )

    if progress:
        progress(1.0)
    return target
