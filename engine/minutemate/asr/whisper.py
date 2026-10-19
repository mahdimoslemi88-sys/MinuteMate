"""Whisper transcription via faster-whisper with progress and cancellation."""

from __future__ import annotations

import json
import time
from pathlib import Path

from minutemate.env import setup_windows_cuda
from minutemate.errors import CudaUnavailableError, StageError
from minutemate.events import Stage
from minutemate.job import JobContext


def _format_srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def transcribe(
    audio_path: str | Path,
    out_dir: str | Path,
    stem: str,
    model_dir: str | Path,
    language: str,
    device: str,
    compute_type: str,
    beam_size: int,
    ctx: JobContext,
) -> dict:
    setup_windows_cuda()
    audio_path = Path(audio_path).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = out_dir / f"{stem}.segments.jsonl"
    json_path = out_dir / f"{stem}.segments.json"
    txt_path = out_dir / f"{stem}.txt"
    srt_path = out_dir / f"{stem}.srt"

    from faster_whisper import WhisperModel

    ctx.log(f"بارگذاری مدل Whisper از {model_dir} روی {device.upper()} ({compute_type})")
    started = time.time()
    try:
        model = WhisperModel(str(model_dir), device=device, compute_type=compute_type)
    except Exception as exc:
        if device == "cuda":
            raise CudaUnavailableError(
                "راه‌اندازی Whisper روی GPU ناموفق بود.",
                hint=f"{exc}\nدستگاه را روی cpu و دقت را int8 بگذارید.",
            ) from exc
        raise StageError(f"بارگذاری مدل Whisper ناموفق بود: {exc}") from exc

    ctx.log(f"مدل در {time.time() - started:.1f} ثانیه بارگذاری شد.")

    try:
        stream, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=beam_size,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=True,
        )
    except Exception as exc:
        raise StageError(f"رونویسی ناموفق بود: {exc}") from exc

    duration = float(getattr(info, "duration", 0.0) or 0.0)
    segments: list[dict] = []

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for index, segment in enumerate(stream):
            ctx.check_cancel()
            words = [
                {
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                    "word": word.word,
                    "probability": round(word.probability, 3),
                }
                for word in (segment.words or [])
            ]
            record = {
                "id": segment.id,
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": segment.text.strip(),
                "words": words,
            }
            segments.append(record)
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()

            if duration > 0:
                ctx.stage_progress(Stage.TRANSCRIPTION, min(1.0, segment.end / duration))

    result = {
        "audio": str(audio_path),
        "language": info.language,
        "duration": duration,
        "segments": segments,
    }
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    with txt_path.open("w", encoding="utf-8") as handle:
        for segment in segments:
            handle.write(f"[{segment['start']:.2f} - {segment['end']:.2f}] {segment['text']}\n")

    with srt_path.open("w", encoding="utf-8") as handle:
        for index, segment in enumerate(segments, start=1):
            handle.write(f"{index}\n")
            handle.write(f"{_format_srt_time(segment['start'])} --> {_format_srt_time(segment['end'])}\n")
            handle.write(f"{segment['text']}\n\n")

    ctx.log(f"رونویسی پایان یافت: {len(segments)} قطعه در {time.time() - started:.1f} ثانیه.")
    return result
