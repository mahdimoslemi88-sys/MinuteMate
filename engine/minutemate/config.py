"""Engine configuration model and job payload mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from minutemate.env import cuda_device_count
from minutemate.errors import InputError

DEVICES = ("auto", "cuda", "cpu")


@dataclass
class EngineConfig:
    audio_path: str
    output_dir: str
    stem: str = "meeting"
    title: str | None = None
    date: str | None = None
    num_speakers: int = 4
    device: str = "auto"
    compute_type: str = "auto"
    language: str = "fa"
    ffmpeg_bin: str = "ffmpeg"
    models_dir: str | None = None
    beam_size: int = 1
    num_threads: int = 6
    speaker_map: dict[int, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict) -> "EngineConfig":
        audio = payload.get("audioPath") or payload.get("audio_path")
        output = payload.get("outputDirectory") or payload.get("outDir") or payload.get("output_dir")
        if not audio:
            raise InputError("مسیر فایل ورودی مشخص نشده است.", hint="کلید audioPath در job الزامی است.")
        if not output:
            raise InputError("مسیر پوشه خروجی مشخص نشده است.", hint="کلید outputDirectory در job الزامی است.")

        raw_map = payload.get("speakerMap") or payload.get("speaker_map") or {}
        speaker_map: dict[int, Any] = {}
        for key, value in raw_map.items():
            try:
                speaker_map[int(key)] = value
            except (TypeError, ValueError):
                continue

        return cls(
            audio_path=str(audio),
            output_dir=str(output),
            stem=str(payload.get("stem") or "meeting"),
            title=payload.get("title"),
            date=payload.get("date"),
            num_speakers=int(payload.get("numSpeakers", payload.get("num_speakers", 4)) or 0),
            device=str(payload.get("device") or "auto").lower(),
            compute_type=str(payload.get("computeType") or payload.get("compute_type") or "auto").lower(),
            language=str(payload.get("language") or "fa"),
            ffmpeg_bin=str(payload.get("ffmpegPath") or payload.get("ffmpeg_bin") or "ffmpeg"),
            models_dir=payload.get("modelsDir") or payload.get("models_dir"),
            beam_size=int(payload.get("beamSize", payload.get("beam_size", 1)) or 1),
            num_threads=int(payload.get("numThreads", payload.get("num_threads", 6)) or 6),
            speaker_map=speaker_map,
        )

    def resolved_device(self) -> str:
        device = (self.device or "auto").lower()
        if device not in DEVICES:
            raise InputError(f"دستگاه نامعتبر: {self.device}", hint="مقادیر مجاز: auto, cuda, cpu")
        if device == "auto":
            return "cuda" if cuda_device_count() > 0 else "cpu"
        return device

    def resolved_compute_type(self, device: str | None = None) -> str:
        compute = (self.compute_type or "auto").lower()
        if compute != "auto":
            return compute
        return "float16" if (device or self.resolved_device()) == "cuda" else "int8"

    def effective_title(self) -> str:
        return self.title or f"جلسه {self.stem}"

    def effective_date(self) -> str:
        if self.date:
            return str(self.date)
        return date.today().isoformat()

    def validate(self) -> None:
        from pathlib import Path

        audio = Path(self.audio_path)
        if not audio.exists():
            raise InputError(f"فایل ورودی پیدا نشد: {self.audio_path}")

        if self.num_speakers < 0:
            raise InputError("تعداد گویندگان نمی‌تواند منفی باشد.")

        self.resolved_device()
