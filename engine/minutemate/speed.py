"""Persistent device speed history used for ETA estimates."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

SCHEMA_VERSION = 1
MAX_SAMPLES = 5
STAGES = ("preprocess", "diarization", "transcription")

DEFAULT_RATES: dict[str, dict[str, float]] = {
    "cpu": {"preprocess": 0.01, "diarization": 0.06, "transcription": 0.40},
    "cuda": {"preprocess": 0.01, "diarization": 0.06, "transcription": 0.08},
}
RATE_LIMITS = (0.001, 5.0)


def normalize_key(device: str, compute_type: str) -> str:
    return f"{(device or 'cpu').lower()}:{(compute_type or 'auto').lower()}"


def default_rate(device: str, stage: str) -> float:
    rates = DEFAULT_RATES.get((device or "cpu").lower(), DEFAULT_RATES["cpu"])
    return rates.get(stage, 0.0)


class SpeedProfile:
    def __init__(self, path: Path, profiles: dict[str, dict[str, list[float]]] | None = None) -> None:
        self.path = path
        self.profiles = profiles or {}

    @classmethod
    def load(cls, metrics_dir: str | Path | None) -> "SpeedProfile":
        path = Path(metrics_dir) / "device_speed.json" if metrics_dir else Path("device_speed.json")
        profiles: dict[str, dict[str, list[float]]] = {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload.get("profiles"), dict):
                profiles = payload["profiles"]
        except (OSError, ValueError):
            profiles = {}
        return cls(path, profiles)

    def stage_rate(self, device: str, compute_type: str, stage: str) -> float:
        samples = self._samples(device, compute_type, stage)
        if samples:
            return _clamp(statistics.median(samples))
        return default_rate(device, stage)

    def record(self, device: str, compute_type: str, stage_seconds: dict[str, float], duration: float) -> None:
        if duration <= 0:
            return
        key = normalize_key(device, compute_type)
        entry = self.profiles.setdefault(key, {})
        for stage in STAGES:
            seconds = float(stage_seconds.get(stage, 0.0) or 0.0)
            if seconds <= 0:
                continue
            samples = entry.setdefault(stage, [])
            samples.append(_clamp(seconds / duration))
            del samples[:-MAX_SAMPLES]
        self._save()

    def _samples(self, device: str, compute_type: str, stage: str) -> list[float]:
        exact = self.profiles.get(normalize_key(device, compute_type), {})
        if stage in exact:
            return exact[stage]
        device_wide = self.profiles.get(f"{(device or 'cpu').lower()}:default", {})
        return device_wide.get(stage, [])

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"schemaVersion": SCHEMA_VERSION, "profiles": self.profiles}
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            pass


def _clamp(value: float) -> float:
    return max(RATE_LIMITS[0], min(RATE_LIMITS[1], value))
