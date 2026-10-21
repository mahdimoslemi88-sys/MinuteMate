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


def chunk_windows(duration: float, chunk_seconds: float, overlap_seconds: float) -> list[tuple[float, float]]:
    if chunk_seconds <= 0 or duration <= chunk_seconds:
        return [(0.0, duration)]
    step = max(1.0, chunk_seconds - max(0.0, overlap_seconds))
    windows: list[tuple[float, float]] = []
    start = 0.0
    while start < duration:
        end = min(duration, start + chunk_seconds)
        windows.append((start, end))
        if end >= duration:
            break
        if duration - end <= max(overlap_seconds, chunk_seconds * 0.1):
            windows[-1] = (start, duration)
            break
        start += step
    return windows


def merge_chunk_records(chunks: list[list[dict]]) -> list[dict]:
    merged: list[dict] = []
    for records in chunks:
        for record in records:
            if merged:
                center = (record["start"] + record["end"]) / 2
                if center <= merged[-1]["end"] + 1e-6:
                    continue
            record["id"] = len(merged)
            merged.append(record)
    return merged


def _write_chunk(source: Path, target: Path, start: float, end: float) -> None:
    import numpy as np
    from scipy.io import wavfile

    from minutemate.audio.wav import read_wav

    samples, sample_rate = read_wav(source, start, end)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    wavfile.write(str(target), sample_rate, pcm)


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
    num_threads: int = 0,
    batch_size: int = 0,
    eta_rate: float | None = None,
    chunk_seconds: float = 0.0,
    overlap_seconds: float = 5.0,
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
        model = WhisperModel(
            str(model_dir),
            device=device,
            compute_type=compute_type,
            cpu_threads=num_threads if device == "cpu" else 0,
        )
    except Exception as exc:
        if device == "cuda":
            raise CudaUnavailableError(
                "راه‌اندازی Whisper روی GPU ناموفق بود.",
                hint=f"{exc}\nدستگاه را روی cpu و دقت را int8 بگذارید.",
            ) from exc
        raise StageError(f"بارگذاری مدل Whisper ناموفق بود: {exc}") from exc

    ctx.log(f"مدل در {time.time() - started:.1f} ثانیه بارگذاری شد.")

    transcribe_kwargs = {
        "language": language,
        "beam_size": beam_size,
        "word_timestamps": True,
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": 500},
        "condition_on_previous_text": False,
        "temperature": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    }

    def start_stream(path: Path):
        try:
            if batch_size > 0:
                from faster_whisper import BatchedInferencePipeline

                return BatchedInferencePipeline(model).transcribe(
                    str(path),
                    batch_size=batch_size,
                    **transcribe_kwargs,
                )
            return model.transcribe(str(path), **transcribe_kwargs)
        except Exception as exc:
            message = str(exc)
            if device == "cuda" and "out of memory" in message.lower():
                raise CudaUnavailableError(
                    "حافظهٔ GPU برای رونویسی کافی نبود.",
                    hint="batchSize را کم کنید یا دستگاه را cpu/int8 بگذارید.",
                ) from exc
            raise StageError(f"رونویسی ناموفق بود: {message}") from exc

    from minutemate.audio.wav import duration_seconds

    try:
        total_duration = duration_seconds(audio_path)
    except Exception:
        total_duration = 0.0

    chunked = chunk_seconds > 0 and total_duration > chunk_seconds
    windows = chunk_windows(total_duration, chunk_seconds, overlap_seconds)
    if chunked:
        ctx.log(
            f"صدای طولانی شناسایی شد؛ رونویسی در {len(windows)} چانک "
            f"{chunk_seconds / 60:.0f} دقیقه‌ای با {overlap_seconds:.0f} ثانیه هم‌پوشانی."
        )
    if batch_size > 0:
        ctx.log(f"حالت batch فعال است (batchSize={batch_size}).")
    if total_duration > 0 and eta_rate:
        ctx.stage_progress(
            Stage.TRANSCRIPTION,
            0.0,
            eta_seconds=total_duration * eta_rate,
            force=True,
        )

    collected: list[list[dict]] = []
    language_result = language
    info_duration = 0.0
    for offset, end in windows:
        ctx.check_cancel()
        target = audio_path
        if chunked:
            target = out_dir / f".{stem}.chunk-{int(offset)}.wav"
            _write_chunk(audio_path, target, offset, end)
        records: list[dict] = []
        try:
            stream, info = start_stream(target)
            chunk_duration = float(getattr(info, "duration", 0.0) or 0.0)
            info_duration = max(info_duration, offset + chunk_duration)
            if total_duration <= 0 and chunk_duration > 0:
                total_duration = offset + chunk_duration
                if eta_rate:
                    ctx.stage_progress(
                        Stage.TRANSCRIPTION,
                        0.0,
                        eta_seconds=total_duration * eta_rate,
                        force=True,
                    )
            language_result = getattr(info, "language", language) or language
            for segment in stream:
                ctx.check_cancel()
                start = round(segment.start + offset, 3)
                finish = round(segment.end + offset, 3)
                words = [
                    {
                        "start": round(word.start + offset, 3),
                        "end": round(word.end + offset, 3),
                        "word": word.word,
                        "probability": round(word.probability, 3),
                    }
                    for word in (segment.words or [])
                ]
                records.append(
                    {
                        "id": segment.id,
                        "start": start,
                        "end": finish,
                        "text": segment.text.strip(),
                        "words": words,
                    }
                )
                if total_duration > 0:
                    eta_seconds = (total_duration - finish) * eta_rate if eta_rate else None
                    ctx.stage_progress(
                        Stage.TRANSCRIPTION,
                        min(1.0, finish / total_duration),
                        eta_seconds=eta_seconds,
                    )
        finally:
            if chunked:
                target.unlink(missing_ok=True)
        collected.append(records)

    if chunked:
        segments = merge_chunk_records(collected)
    else:
        segments = collected[0] if collected else []
    duration = total_duration or info_duration
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for segment in segments:
            handle.write(json.dumps(segment, ensure_ascii=False) + "\n")

    result = {
        "audio": str(audio_path),
        "language": language_result,
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


def transcribe_with_fallback(
    audio_path: str | Path,
    out_dir: str | Path,
    stem: str,
    model_dir: str | Path,
    language: str,
    device: str,
    compute_type: str,
    beam_size: int,
    ctx: JobContext,
    num_threads: int = 0,
    batch_size: int = 0,
    eta_rate: float | None = None,
    eta_rate_cpu: float | None = None,
    chunk_seconds: float = 0.0,
    overlap_seconds: float = 5.0,
) -> tuple[dict, str, str]:
    try:
        result = transcribe(
            audio_path,
            out_dir,
            stem,
            model_dir,
            language,
            device=device,
            compute_type=compute_type,
            beam_size=beam_size,
            ctx=ctx,
            num_threads=num_threads,
            batch_size=batch_size,
            eta_rate=eta_rate,
            chunk_seconds=chunk_seconds,
            overlap_seconds=overlap_seconds,
        )
        return result, device, compute_type
    except CudaUnavailableError as error:
        if device != "cuda":
            raise
        ctx.log(
            f"اجرای GPU ناموفق بود؛ تلاش دوباره روی CPU با int8. {error}",
            level="warning",
        )
        result = transcribe(
            audio_path,
            out_dir,
            stem,
            model_dir,
            language,
            device="cpu",
            compute_type="int8",
            beam_size=beam_size,
            ctx=ctx,
            num_threads=num_threads,
            eta_rate=eta_rate_cpu,
            chunk_seconds=chunk_seconds,
            overlap_seconds=overlap_seconds,
        )
        return result, "cpu", "int8"

