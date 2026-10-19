"""Speaker diarization orchestration with progress and cancellation."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from minutemate.audio.wav import read_wav
from minutemate.diarization.cluster import choose_k, silhouette
from minutemate.diarization.embedder import SpeakerEmbedder
from minutemate.events import Stage
from minutemate.job import JobContext

CHUNK_SECONDS = 600.0
SEGMENTATION_SHARE = 0.45
EMBEDDING_SHARE = 0.40


def segmentation_turns(samples, sample_rate, seg_model, seg_emb_model, num_threads, start_offset):
    import sherpa_onnx as so

    seg_cfg = so.OfflineSpeakerSegmentationModelConfig(
        pyannote=so.OfflineSpeakerSegmentationPyannoteModelConfig(
            model=str(seg_model), window_shift_ratio=0.25
        ),
        num_threads=num_threads,
        debug=False,
        provider="cpu",
    )
    emb_cfg = so.SpeakerEmbeddingExtractorConfig(
        model=str(seg_emb_model), num_threads=num_threads, debug=False, provider="cpu"
    )
    cl_cfg = so.FastClusteringConfig(threshold=0.05, num_clusters=-1, compute_confidence=False)
    diar = so.OfflineSpeakerDiarization(
        config=so.OfflineSpeakerDiarizationConfig(
            segmentation=seg_cfg,
            embedding=emb_cfg,
            clustering=cl_cfg,
            min_duration_off=0.4,
            min_duration_on=0.2,
        )
    )
    result = diar.process(samples)
    turns = [
        {"start": float(s.start) + start_offset, "end": float(s.end) + start_offset}
        for s in result.sort_by_start_time()
    ]

    merged: list[dict] = []
    for turn in turns:
        if merged and turn["start"] - merged[-1]["end"] < 0.25:
            merged[-1]["end"] = max(merged[-1]["end"], turn["end"])
            continue
        merged.append(turn)
    return [t for t in merged if t["end"] - t["start"] >= 0.3]


def turn_embedding(embedder, samples, sample_rate, start, end, chunk=3.0, overlap=0.5, offset=0.0):
    start, end = start - offset, end - offset
    a, b = int(start * sample_rate), int(end * sample_rate)
    wav = samples[a:b]
    if len(wav) < sample_rate * 0.5:
        return None
    step = chunk * (1.0 - overlap)
    starts = [0.0]
    while starts[-1] + chunk < len(wav) / sample_rate:
        starts.append(starts[-1] + step)
    vectors = []
    for s in starts:
        piece = wav[int(s * sample_rate): int((s + chunk) * sample_rate)]
        if len(piece) < sample_rate * 0.5:
            continue
        embedding = embedder.embed(piece)
        if embedding is not None:
            vectors.append(embedding)
    if not vectors:
        return None
    vector = np.mean(vectors, axis=0)
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 1e-8 else None


def _fmt(seconds: float) -> str:
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def run_diarization(
    audio_path: str | Path,
    out_dir: str | Path,
    stem: str,
    num_speakers: int,
    seg_model: str | Path,
    seg_emb_model: str | Path,
    emb_model: str | Path,
    num_threads: int,
    device: str,
    ctx: JobContext,
) -> dict:
    audio_path = Path(audio_path).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    samples, sample_rate = read_wav(str(audio_path))
    total_duration = len(samples) / float(sample_rate or 1)
    ctx.log(f"صدای ورودی: {total_duration:.1f} ثانیه ({total_duration / 60:.1f} دقیقه) @ {sample_rate}Hz")

    started = time.time()
    raw_turns: list[dict] = []
    if total_duration > CHUNK_SECONDS:
        num_chunks = int(np.ceil(total_duration / CHUNK_SECONDS))
        ctx.log(f"صدای طولانی شناسایی شد؛ بخش‌بندی در {num_chunks} چانک ۱۰ دقیقه‌ای.")
        for index in range(num_chunks):
            ctx.check_cancel()
            start_sec = index * CHUNK_SECONDS
            end_sec = min(total_duration, (index + 1) * CHUNK_SECONDS)
            chunk = samples[int(start_sec * sample_rate): int(end_sec * sample_rate)]
            raw_turns.extend(
                segmentation_turns(chunk, sample_rate, seg_model, seg_emb_model, num_threads, start_offset=start_sec)
            )
            ctx.stage_progress(
                Stage.DIARIZATION,
                SEGMENTATION_SHARE * (index + 1) / num_chunks,
                message=f"بخش‌بندی گویندگان چانک {index + 1}/{num_chunks}",
            )
    else:
        raw_turns = segmentation_turns(samples, sample_rate, seg_model, seg_emb_model, num_threads, 0.0)
        ctx.stage_progress(Stage.DIARIZATION, SEGMENTATION_SHARE, message="بخش‌بندی گویندگان", force=True)

    raw_turns.sort(key=lambda t: t["start"])
    turns: list[dict] = []
    for turn in raw_turns:
        if turns and turn["start"] - turns[-1]["end"] < 0.25:
            turns[-1]["end"] = max(turns[-1]["end"], turn["end"])
            continue
        turns.append(turn)
    turns = [t for t in turns if t["end"] - t["start"] >= 0.3]

    if not turns:
        ctx.log("هیچ نوبت گفتاری شناسایی نشد؛ خروجی گویندگان خالی است.", level="warning")
        merged: list[dict] = []
        auto_k = 1
    else:
        embedder = SpeakerEmbedder(str(emb_model), window_type="hamming", num_threads=num_threads, device=device)

        windows = []
        for turn in turns:
            duration = turn["end"] - turn["start"]
            count = max(1, int(round(duration / 3.0)))
            for i in range(count):
                ws = turn["start"] + i * duration / count
                we = turn["start"] + (i + 1) * duration / count
                if we - ws >= 1.0:
                    windows.append({"start": ws, "end": we, "turn": turn})

        vectors = []
        valid_windows = []
        for index, window in enumerate(windows):
            ctx.check_cancel()
            embedding = turn_embedding(
                embedder, samples, sample_rate, window["start"], window["end"], chunk=4.0, overlap=0.0
            )
            if embedding is not None:
                vectors.append(embedding)
                valid_windows.append(window)
            if windows:
                ctx.stage_progress(
                    Stage.DIARIZATION,
                    SEGMENTATION_SHARE + EMBEDDING_SHARE * (index + 1) / len(windows),
                    message="استخراج ویژگی صوتی گویندگان",
                )
        windows = valid_windows

        if not vectors:
            merged = []
            auto_k = 1
        else:
            X = np.stack(vectors)
            Z = X - X.mean(axis=0)
            Z /= np.linalg.norm(Z, axis=1, keepdims=True)

            from scipy.cluster.hierarchy import fcluster

            auto_k, auto_labels, auto_sil, linkage_matrix = choose_k(Z, min_share=0.02, max_k=12)
            ctx.log(f"تعداد گوینده خودکار: k={auto_k} (silhouette={auto_sil:.3f})")

            if num_speakers > 1:
                labels = fcluster(linkage_matrix, num_speakers, criterion="maxclust")
                sil = silhouette(Z, labels)
                ctx.log(f"تعداد گوینده اعمال‌شده: k={num_speakers} (silhouette={sil:.3f})")
            else:
                labels = auto_labels
                sil = auto_sil

            ctx.stage_progress(Stage.DIARIZATION, SEGMENTATION_SHARE + EMBEDDING_SHARE + 0.05, message="خوشه‌بندی گویندگان")

            turn_index = {id(t): i for i, t in enumerate(turns)}
            votes: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
            for window, label in zip(windows, labels):
                votes[turn_index[id(window["turn"])]][int(label)] += window["end"] - window["start"]
            turn_label = {i: max(votes[i].items(), key=lambda kv: kv[1])[0] for i in votes}

            durations: dict[int, float] = defaultdict(float)
            for i, label in turn_label.items():
                durations[label] += turns[i]["end"] - turns[i]["start"]
            order = {old: i for i, old in enumerate(sorted(durations, key=lambda c: -durations[c]))}

            by_time = sorted(turn_label.items(), key=lambda kv: turns[kv[0]]["start"])
            smoothed: list[tuple[dict, int]] = []
            for i, label in by_time:
                turn = turns[i]
                if (turn["end"] - turn["start"]) < 1.0 and smoothed:
                    label = smoothed[-1][1]
                smoothed.append((turn, order[int(label)]))

            merged = []
            for turn, speaker in smoothed:
                if merged and merged[-1]["speaker"] == speaker and turn["start"] - merged[-1]["end"] < 0.6:
                    merged[-1]["end"] = turn["end"]
                    continue
                merged.append({"start": round(turn["start"], 3), "end": round(turn["end"], 3), "speaker": speaker})

    out_path = out_dir / f"{stem}.speakers.json"
    txt_path = out_dir / f"{stem}.speakers.txt"

    with txt_path.open("w", encoding="utf-8") as handle:
        for turn in merged:
            handle.write(f"Speaker_{turn['speaker'] + 1:02d}\n")
            handle.write(f"Start: {_fmt(turn['start'])}\n")
            handle.write(f"End: {_fmt(turn['end'])}\n\n")

    result = {
        "audio": str(audio_path),
        "num_speakers": len({t["speaker"] for t in merged}),
        "auto_detected_k": auto_k,
        "turns": merged,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    ctx.stage_progress(Stage.DIARIZATION, 1.0, force=True)
    ctx.log(f"تفکیک گویندگان پایان یافت: {len(merged)} نوبت در {time.time() - started:.1f} ثانیه.")
    return result
