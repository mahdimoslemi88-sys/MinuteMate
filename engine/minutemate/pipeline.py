"""Pipeline orchestration: preprocess, diarize, transcribe, merge, export."""

from __future__ import annotations

from pathlib import Path

from minutemate.models import registry as model_registry
from minutemate.asr.whisper import transcribe
from minutemate.audio.ffmpeg import preprocess
from minutemate.config import EngineConfig
from minutemate.diarization.segmenter import run_diarization
from minutemate.env import setup_windows_cuda
from minutemate.errors import ModelMissingError
from minutemate.events import Stage
from minutemate.job import JobContext
from minutemate.merge.align import merge_transcription_and_diarization
from minutemate.paths import ensure_dir
from minutemate.text.renderers import export_deliverables


def preflight(config: EngineConfig) -> dict:
    from minutemate.audio.ffmpeg import ensure_ffmpeg

    models_dir = model_registry.resolve(config.models_dir).models_dir
    missing = model_registry.verify(config.models_dir)
    ffmpeg = None
    ffmpeg_error = None
    try:
        ffmpeg = ensure_ffmpeg(config.ffmpeg_bin)
    except Exception as exc:
        ffmpeg_error = str(exc)

    device = config.resolved_device()
    return {
        "modelsDir": str(models_dir),
        "modelsReady": not missing,
        "missingModels": [str(item) for item in missing],
        "ffmpeg": ffmpeg,
        "ffmpegError": ffmpeg_error,
        "device": device,
        "computeType": config.resolved_compute_type(device),
    }


def run(config: EngineConfig, ctx: JobContext) -> dict:
    config.validate()
    setup_windows_cuda()

    missing = model_registry.verify(config.models_dir)
    if missing:
        raise ModelMissingError(
            f"{len(missing)} فایل مدل پیدا نشد یا ناقص است.",
            hint="؛ ".join(str(item) for item in missing[:5]),
        )

    resolved = model_registry.resolve(config.models_dir)
    device = config.resolved_device()
    compute_type = config.resolved_compute_type(device)
    out_dir = ensure_dir(config.output_dir)
    stem = config.stem

    ctx.started(f"{Path(config.audio_path).name} · {device} ({compute_type})")

    processed_wav = out_dir / f"{stem}_16k_mono.wav"
    ctx.stage_start(Stage.PREPROCESS, "نرمال‌سازی و تبدیل صدا")
    if processed_wav.exists() and processed_wav.stat().st_size > 1024:
        ctx.log(f"فایل پیش‌پردازش‌شده موجود است: {processed_wav.name}")
        ctx.stage_progress(Stage.PREPROCESS, 1.0, force=True)
    else:
        preprocess(
            config.audio_path,
            processed_wav,
            ffmpeg_bin=config.ffmpeg_bin,
            progress=lambda fraction: ctx.stage_progress(Stage.PREPROCESS, fraction),
            cancel=lambda: ctx.cancelled,
        )
    ctx.stage_done(Stage.PREPROCESS)

    ctx.stage_start(Stage.DIARIZATION, "تفکیک گویندگان")
    run_diarization(
        processed_wav,
        out_dir=out_dir,
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

    ctx.stage_start(Stage.TRANSCRIPTION, "رونویسی گفتار")
    asr_result = transcribe(
        processed_wav,
        out_dir=out_dir,
        stem=stem,
        model_dir=resolved.whisper_dir,
        language=config.language,
        device=device,
        compute_type=compute_type,
        beam_size=config.beam_size,
        ctx=ctx,
    )
    ctx.stage_done(Stage.TRANSCRIPTION)

    ctx.stage_start(Stage.MERGE, "ادغام متن و گویندگان")
    merged = merge_transcription_and_diarization(
        segments_path=out_dir / f"{stem}.segments.json",
        speakers_path=out_dir / f"{stem}.speakers.json",
        out_dir=out_dir,
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

    ctx.done(f"{len(merged['utterances'])} utterance · {out_dir}")
    return {
        "outputDir": str(out_dir),
        "artifacts": [str(path) for path in deliverable_paths],
        "utterances": merged["utterances"],
        "numSpeakers": len({u["speaker"] for u in merged["utterances"]}),
        "language": asr_result.get("language"),
        "duration": asr_result.get("duration"),
    }
