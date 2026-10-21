"""Pipeline orchestration: preprocess, diarize, transcribe, merge, export."""

from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from minutemate import session
from minutemate.models import registry as model_registry
from minutemate.asr.whisper import transcribe_with_fallback
from minutemate.asr.groq import GroqChunkedTranscriber, get_groq_api_key, GroqConfig
from minutemate.audio.ffmpeg import ensure_ffmpeg, preprocess, probe
from minutemate.config import EngineConfig
from minutemate.diarization.segmenter import run_diarization
from minutemate.env import setup_windows_cuda
from minutemate.errors import ModelMissingError, StageError
from minutemate.events import Stage
from minutemate.job import JobContext
from minutemate.merge.align import merge_transcription_and_diarization
from minutemate.minutes.stage import run_minutes
from minutemate.paths import ensure_dir, resolve_data_dir
from minutemate.speed import SpeedProfile
from minutemate.text.renderers import export_deliverables
from minutemate.events import Stage
from minutemate.job import JobContext
from minutemate.merge.align import merge_transcription_and_diarization
from minutemate.minutes.stage import run_minutes
from minutemate.paths import ensure_dir, resolve_data_dir
from minutemate.speed import SpeedProfile
from minutemate.text.renderers import export_deliverables


def preflight(config: EngineConfig) -> dict:
    from minutemate import __version__
    from minutemate.audio.ffmpeg import ensure_ffmpeg
    from minutemate.env import cuda_device_count

    models_dir = model_registry.resolve(config.models_dir, config.speaker_embedding, config.asr_model).models_dir
    missing = model_registry.verify(models_dir, model_registry.required_group_ids(config.asr_model))
    ffmpeg = None
    ffmpeg_error = None
    try:
        ffmpeg = ensure_ffmpeg(config.ffmpeg_bin)
    except Exception as exc:
        ffmpeg_error = str(exc)

    device = config.resolved_device()
    gpu_count = cuda_device_count()
    return {
        "engineVersion": __version__,
        "modelsDir": str(models_dir),
        "modelsReady": not missing,
        "missingModels": [str(item) for item in missing],
        "ffmpeg": ffmpeg,
        "ffmpegError": ffmpeg_error,
        "device": device,
        "computeType": config.resolved_compute_type(device),
        "beamSize": config.beam_size,
        "batchSize": config.resolved_batch_size(),
        "speakerEmbedding": config.speaker_embedding,
        "speakerEmbeddings": sorted(model_registry.EMBEDDINGS),
        "gpuCount": gpu_count,
        "cudaAvailable": gpu_count > 0,
    }


def _download_missing_models(config: EngineConfig, ctx: JobContext, missing: list, group_ids: list[str] | None = None) -> None:
    from minutemate.models.downloader import download_groups, format_progress

    names = [item.rel_path for item in missing]
    state = {"index": 0, "current": names[0] if names else ""}

    def on_progress(rel_path: str, downloaded: int, total: int) -> None:
        if rel_path != state["current"]:
            state["current"] = rel_path
            state["index"] = min(len(names) - 1, state["index"] + 1)
        share = downloaded / total if total > 0 else 0.0
        fraction = (state["index"] + share) / max(1, len(names))
        ctx.stage_progress(
            Stage.MODELS,
            min(0.99, fraction),
            message=format_progress(rel_path, downloaded, total),
        )

    ctx.stage_start(Stage.MODELS, "دانلود مدل‌های لازم (فقط بار اول)")
    ctx.log(f"{len(names)} فایل مدل ناقص است؛ دانلود خودکار آغاز شد.")
    download_groups(
        group_ids,
        models_dir=config.models_dir,
        progress=on_progress,
        cancel=lambda: ctx.cancelled,
        log=lambda message: ctx.log(message),
    )
    ctx.stage_done(Stage.MODELS, "مدل‌ها آماده شدند")


def run(config: EngineConfig, ctx: JobContext) -> dict:
    config.validate()
    setup_windows_cuda()

    required = model_registry.required_group_ids(config.asr_model)
    missing = model_registry.verify(config.models_dir, required)
    if missing and not config.auto_download_models:
        raise ModelMissingError(
            f"{len(missing)} فایل مدل پیدا نشد یا ناقص است.",
            hint="؛ ".join(str(item) for item in missing[:5]),
        )

    resolved = model_registry.resolve(config.models_dir, config.speaker_embedding, config.asr_model)
    device = config.resolved_device()
    compute_type = config.resolved_compute_type(device)
    stem = config.stem
    speed_profile = SpeedProfile.load(config.metrics_dir or (resolve_data_dir() / "metrics"))

    layout = session.resolve_layout(
        session_dir=config.session_dir,
        sessions_root=config.sessions_root,
        output_dir=config.output_dir,
        stem=stem,
        title=config.effective_title(),
        date_str=config.effective_date(),
    )
    session.ensure_layout(layout)
    session_source: dict = {}
    manifest_path = layout.root / "session.json"

    if layout.is_session:
        raw_name = Path(config.audio_path).name
        raw_target = layout.raw_dir / raw_name
        if not raw_target.exists():
            shutil.copy2(config.audio_path, raw_target)
        session_source = {
            "fileName": raw_name,
            "sizeBytes": raw_target.stat().st_size,
            "sha256": session.sha256_file(raw_target),
            "sampleRate": 16000,
            "channels": 1,
        }
        session.write_manifest(
            manifest_path,
            session.build_manifest(
                session_id=layout.root.name,
                title=config.effective_title(),
                date_str=config.effective_date(),
                source=session_source,
                status="raw",
            ),
        )

    out_dir = ensure_dir(layout.out_dir)
    work_dir = ensure_dir(layout.work_dir)

    ctx.started(f"{Path(config.audio_path).name} · {device} ({compute_type})")

    if missing:
        _download_missing_models(config, ctx, missing, required)
        missing = model_registry.verify(config.models_dir, required)
        if missing:
            raise ModelMissingError(
                f"{len(missing)} فایل مدل پس از دانلود هم ناقص است.",
                hint="؛ ".join(str(item) for item in missing[:5]),
            )

    processed_wav = work_dir / f"{stem}_16k_mono.wav"
    ctx.stage_start(Stage.PREPROCESS, "نرمال‌سازی و تبدیل صدا")
    if processed_wav.exists() and processed_wav.stat().st_size > 1024:
        ctx.log(f"فایل پیش‌پردازش‌شده موجود است: {processed_wav.name}")
        ctx.stage_progress(Stage.PREPROCESS, 1.0, force=True)
    else:
        source_duration = 0.0
        try:
            source_duration = probe(config.audio_path, config.ffmpeg_bin).duration
        except Exception:
            source_duration = 0.0
        preprocess_rate = speed_profile.stage_rate(device, compute_type, "preprocess")
        preprocess(
            config.audio_path,
            processed_wav,
            ffmpeg_bin=config.ffmpeg_bin,
            progress=lambda fraction: ctx.stage_progress(
                Stage.PREPROCESS,
                fraction,
                eta_seconds=(1.0 - fraction) * source_duration * preprocess_rate if source_duration else None,
            ),
            cancel=lambda: ctx.cancelled,
        )
    ctx.stage_done(Stage.PREPROCESS)

    def run_diarization_stage() -> None:
        ctx.stage_start(Stage.DIARIZATION, "تفکیک گویندگان")
        run_diarization(
            processed_wav,
            out_dir=work_dir,
            stem=stem,
            num_speakers=config.num_speakers,
            seg_model=resolved.segmentation_model,
            seg_emb_model=resolved.segmentation_embedding,
            emb_model=resolved.speaker_embedding,
            num_threads=config.num_threads,
            device="gpu" if device == "cuda" else "cpu",
            ctx=ctx,
        )
        ctx.stage_done(Stage.DIARIZATION)

    def run_groq_transcription_stage() -> dict:
        ctx.log("استفاده از Groq Cloud API (whisper-large-v3-turbo)")
        api_key = get_groq_api_key()
        if not api_key:
            raise StageError(
                "Groq API key تنظیم نشده است. "
                "متغیر محیطی GROQ_API_KEY را در .env تنظیم کنید."
            )

        # Get VAD segments from diarization (speaker turns)
        speakers_path = out_dir / f"{stem}.speakers.json"
        if not speakers_path.exists():
            raise StageError("فایل speakers.json یافت نشد. دایاریزیشن باید اول اجرا شود.")

        import json
        with open(speakers_path, "r", encoding="utf-8") as f:
            speakers_data = json.load(f)
        vad_segments = speakers_data.get("turns", [])

        if not vad_segments:
            # Fallback: single chunk for entire audio
            from minutemate.audio.wav import duration_seconds
            total_dur = duration_seconds(processed_wav)
            vad_segments = [{"start": 0.0, "end": total_dur}]

        ctx.stage_start(Stage.TRANSCRIPTION, f"رونویسی از طریق Groq ({config.groq_model})")

        transcriber = GroqChunkedTranscriber(
            config=GroqConfig(
                api_key=api_key,
                model=config.groq_model,
                language=config.language,
            ),
            chunk_sec=30,
            overlap_sec=1.0,
            ffmpeg_bin=config.ffmpeg_bin,
        )

        # Progress callback
        def progress_cb(chunk_idx: int, total_chunks: int, time_range: str):
            ctx.stage_progress(
                Stage.TRANSCRIPTION,
                chunk_idx / total_chunks,
                message=f"چانک {chunk_idx}/{total_chunks}: {time_range}",
            )

        groq_result = transcriber.transcribe_long(
            processed_wav,
            vad_segments,
            prompt=None,
            progress_cb=progress_cb,
        )

        # Convert Groq result to expected format
        result = {
            "audio": str(processed_wav),
            "language": groq_result.language or config.language,
            "duration": groq_result.duration,
            "segments": groq_result.segments,
        }

        # Save segments.json for merge stage
        segments_json = work_dir / f"{stem}.segments.json"
        with open(segments_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Also save .segments.jsonl
        segments_jsonl = work_dir / f"{stem}.segments.jsonl"
        with open(segments_jsonl, "w", encoding="utf-8") as f:
            for seg in result["segments"]:
                f.write(json.dumps(seg, ensure_ascii=False) + "\n")

        ctx.stage_done(Stage.TRANSCRIPTION)
        ctx.log(f"رونویسی Groq کامل شد: {len(result['segments'])} قطعه")
        return result

    def run_transcription_stage() -> dict:
        nonlocal device, compute_type
        ctx.stage_start(Stage.TRANSCRIPTION, "رونویسی گفتار")

        # If using Groq provider, use cloud API with chunked transcription
        if config.asr_provider == "groq":
            return run_groq_transcription_stage()

        # Local Whisper (existing logic)
        transcription_rate = speed_profile.stage_rate(device, compute_type, "transcription")
        cpu_rate = speed_profile.stage_rate("cpu", "int8", "transcription")
        asr_compute_type = compute_type
        if config.asr_model in {"fa", "persian", "fa-large-v3"} and device == "cuda":
            asr_compute_type = "int8_float16"
        elif config.asr_model in {"fa", "persian", "fa-large-v3"} and device == "cpu":
            asr_compute_type = "int8"
        result, device, compute_type = transcribe_with_fallback(
            processed_wav,
            out_dir=work_dir,
            stem=stem,
            model_dir=resolved.whisper_dir,
            language=config.language,
            device=device,
            compute_type=asr_compute_type,
            beam_size=config.beam_size,
            ctx=ctx,
            num_threads=config.num_threads,
            batch_size=config.resolved_batch_size(),
            eta_rate=transcription_rate,
            eta_rate_cpu=cpu_rate,
            chunk_seconds=config.asr_chunk_seconds,
            overlap_seconds=config.asr_chunk_overlap_seconds,
        )
        ctx.stage_done(Stage.TRANSCRIPTION)
        return result

    if config.resolved_parallel(device):
        ctx.log("دیاریزیشن و رونویسی به‌صورت موازی اجرا می‌شوند.")
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="minutemate") as pool:
            diarization_future = pool.submit(run_diarization_stage)
            transcription_future = pool.submit(run_transcription_stage)
            try:
                asr_result = transcription_future.result()
            except Exception:
                diarization_future.cancel()
                raise
            diarization_future.result()
    else:
        run_diarization_stage()
        asr_result = run_transcription_stage()

    ctx.stage_start(Stage.MERGE, "ادغام متن و گویندگان")
    merged = merge_transcription_and_diarization(
        segments_path=work_dir / f"{stem}.segments.json",
        speakers_path=work_dir / f"{stem}.speakers.json",
        out_dir=work_dir,
        stem=stem,
        ctx=ctx,
    )
    ctx.stage_done(Stage.MERGE)

    ctx.stage_start(Stage.EXPORT, "تولید گزارش‌ها")
    speaker_map = {int(k): v for k, v in (config.speaker_map or {}).items()}
    deliverable_paths = export_deliverables(
        raw_segments=asr_result["segments"],
        utterances=merged["utterances"],
        out_dir=out_dir,
        title=config.effective_title(),
        date_str=config.effective_date(),
        speaker_map=speaker_map,
    )
    for path in deliverable_paths:
        ctx.artifact(kind=path.name, path=path)
    ctx.stage_progress(Stage.EXPORT, 1.0, force=True)
    ctx.stage_done(Stage.EXPORT)

    duration = asr_result.get("duration")
    if duration is None and merged["utterances"]:
        duration = max(float(item.get("end", 0.0)) for item in merged["utterances"])

    minutes_paths = run_minutes(
        config=config,
        ctx=ctx,
        transcript_path=work_dir / f"{stem}_transcript.json",
        out_dir=out_dir,
        stem=stem,
        title=config.effective_title(),
        date_str=config.effective_date(),
        duration=float(duration or 0.0),
        speaker_map=speaker_map,
    )
    deliverable_paths = [*deliverable_paths, *minutes_paths]

    num_speakers = len({u["speaker"] for u in merged["utterances"]})
    speed_profile.record(device, compute_type, ctx.stage_seconds, float(duration or 0.0))

    if layout.is_session:
        session_source["durationSeconds"] = duration
        session.write_manifest(
            manifest_path,
            session.build_manifest(
                session_id=layout.root.name,
                title=config.effective_title(),
                date_str=config.effective_date(),
                source=session_source,
                run={
                    "device": device,
                    "computeType": compute_type,
                    "language": config.language,
                    "numSpeakersRequested": config.num_speakers,
                    "numSpeakersDetected": num_speakers,
                    "engineVersion": session.engine_version(),
                    "models": {
                        "whisper": Path(model_registry.WHISPER_DIR).name,
                        "segmentation": Path(model_registry.SEGMENTATION_DIR).name,
                        "embedding": resolved.speaker_embedding.stem,
                    },
                    "durationSeconds": round(ctx.elapsed(), 1),
                    "stageSeconds": dict(ctx.stage_seconds),
                    "overlapCount": merged.get("overlapCount", 0),
                },
                speakers=_session_speakers(merged["utterances"], speaker_map),
                artifacts=session.collect_artifacts(layout.root, deliverable_paths),
                status="minutes" if minutes_paths else "transcribed",
            ),
        )

    ctx.done(f"{len(merged['utterances'])} utterance · {out_dir}")
    return {
        "outputDir": str(out_dir),
        "workDir": str(work_dir),
        "sessionDir": str(layout.root) if layout.is_session else None,
        "artifacts": [str(path) for path in deliverable_paths],
        "utterances": merged["utterances"],
        "numSpeakers": num_speakers,
        "language": asr_result.get("language"),
        "duration": asr_result.get("duration"),
    }


def _session_speakers(utterances: list[dict], speaker_map: dict) -> list[dict]:
    entries: list[dict] = []
    for index in sorted({utterance["speaker"] for utterance in utterances}):
        raw = (speaker_map or {}).get(index)
        name: str | None = None
        role: str | None = None
        if isinstance(raw, str):
            name = raw
        elif isinstance(raw, dict):
            name = raw.get("name") or None
            role = raw.get("role") or None
        entries.append(
            {
                "id": index,
                "name": name,
                "role": role,
                "confidence": "high" if name else "unknown",
            }
        )
    return entries
