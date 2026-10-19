"""16-bit PCM WAV reading helpers."""

from __future__ import annotations

import wave
from collections.abc import Iterator
from pathlib import Path

import numpy as np


def read_wav(
    path: str | Path,
    start: float | None = None,
    end: float | None = None,
) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        sample_rate = handle.getframerate()
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        total = handle.getnframes()
        if width != 2:
            raise ValueError(f"expected 16-bit PCM, got {width * 8}-bit")

        first = 0 if start is None else int(start * sample_rate)
        last = total if end is None else min(total, int(end * sample_rate))
        handle.setpos(first)
        raw = handle.readframes(max(0, last - first))

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return np.ascontiguousarray(samples), sample_rate


def duration_seconds(path: str | Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate() or 1)


def iter_chunks(
    samples: np.ndarray,
    sample_rate: int,
    chunk_seconds: float,
) -> Iterator[tuple[float, np.ndarray]]:
    total = len(samples)
    chunk_size = max(1, int(chunk_seconds * sample_rate))
    offset = 0
    while offset < total:
        end = min(total, offset + chunk_size)
        yield offset / sample_rate, samples[offset:end]
        offset = end
