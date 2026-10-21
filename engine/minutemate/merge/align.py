"""Align word-level ASR segments with diarization turns into utterances."""

from __future__ import annotations

import json
from bisect import bisect_right
from pathlib import Path

from minutemate.events import Stage
from minutemate.job import JobContext


def merge_transcription_and_diarization(
    segments_path: str | Path,
    speakers_path: str | Path,
    out_dir: str | Path,
    stem: str,
    ctx: JobContext,
    max_utterance: float = 30.0,
    gap: float = 2.0,
) -> dict:
    segments_data = json.loads(Path(segments_path).read_text(encoding="utf-8"))
    speakers_data = json.loads(Path(speakers_path).read_text(encoding="utf-8"))
    turns = speakers_data.get("turns", [])

    if not turns:
        utterances = _utterances_without_speakers(segments_data.get("segments", []), max_utterance, gap)
    else:
        turns_sorted = sorted(turns, key=lambda t: t["start"])
        starts = [t["start"] for t in turns_sorted]
        overlap_windows = _overlap_windows(turns_sorted)

        def overlaps(a: float, b: float) -> bool:
            return any(min(b, end) - max(a, start) >= 0.15 for start, end in overlap_windows)

        def speaker_at(a: float, b: float) -> int:
            i = max(0, bisect_right(starts, a) - 2)
            best, best_overlap = -1, 0.0
            for turn in turns_sorted[i: i + 5]:
                overlap = min(b, turn["end"]) - max(a, turn["start"])
                if overlap > best_overlap:
                    best, best_overlap = turn["speaker"], overlap
            if best >= 0:
                return best
            j = min(
                range(len(turns_sorted)),
                key=lambda k: min(abs(turns_sorted[k]["end"] - a), abs(turns_sorted[k]["start"] - b)),
            )
            return turns_sorted[j]["speaker"]

        utterances = _utterances_with_speakers(
            segments_data.get("segments", []), speaker_at, overlaps, max_utterance, gap
        )
        overlap_count = sum(1 for utterance in utterances if utterance.get("overlap"))
        if overlap_count:
            ctx.log(f"{overlap_count} utterance با گفتار هم‌زمان علامت‌گذاری شد؛ تخصیص گوینده ممکن است نادرست باشد.", level="warning")

    out_file = Path(out_dir) / f"{stem}_transcript.json"
    result = {
        "audio": segments_data.get("audio"),
        "utterances": utterances,
        "overlapCount": sum(1 for utterance in utterances if utterance.get("overlap")),
    }
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    ctx.stage_progress(Stage.MERGE, 1.0, force=True)
    ctx.log(f"ادغام انجام شد: {len(utterances)} utterance")
    return result


def _overlap_windows(turns: list[dict]) -> list[tuple[float, float]]:
    windows: list[tuple[float, float]] = []
    active: list[dict] = []
    for turn in turns:
        active = [item for item in active if item["end"] > turn["start"]]
        for item in active:
            start = max(turn["start"], item["start"])
            end = min(turn["end"], item["end"])
            if end - start >= 0.15:
                windows.append((start, end))
        active.append(turn)
    return windows


def _collect_words(segments, speaker_of, overlap_of):
    words = []
    for segment in segments:
        text = segment["text"].strip()
        if not text:
            continue
        if segment.get("words"):
            for word in segment["words"]:
                if not word["word"].strip():
                    continue
                words.append({
                    "start": word["start"],
                    "end": word["end"],
                    "text": word["word"],
                    "speaker": speaker_of(word["start"], word["end"]),
                    "overlap": overlap_of(word["start"], word["end"]),
                })
        else:
            words.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": text,
                "speaker": speaker_of(segment["start"], segment["end"]),
                "overlap": overlap_of(segment["start"], segment["end"]),
            })
    words.sort(key=lambda w: w["start"])
    return words


def _utterances_with_speakers(
    segments, speaker_of, overlap_of, max_utterance: float, gap: float
) -> list[dict]:
    words = _collect_words(segments, speaker_of, overlap_of)
    utterances: list[dict] = []
    for word in words:
        if utterances:
            current = utterances[-1]
            same = current["speaker"] == word["speaker"]
            close = word["start"] - current["end"] <= gap
            long_enough = word["end"] - current["start"] <= max_utterance
            if same and close and long_enough:
                current["words"].append(word)
                current["end"] = word["end"]
                current["overlap"] = current.get("overlap", False) or word.get("overlap", False)
                continue
        utterances.append({
            "speaker": word["speaker"],
            "start": word["start"],
            "end": word["end"],
            "overlap": bool(word.get("overlap")),
            "words": [word],
        })
    for utterance in utterances:
        utterance["text"] = " ".join(w["text"].strip() for w in utterance["words"]).strip()
        utterance.pop("words")
        if not utterance.get("overlap"):
            utterance.pop("overlap", None)
    return utterances


def _utterances_without_speakers(segments, max_utterance: float, gap: float) -> list[dict]:
    utterances: list[dict] = []
    for segment in segments:
        text = segment["text"].strip()
        if not text:
            continue
        if utterances:
            current = utterances[-1]
            close = segment["start"] - current["end"] <= gap
            long_enough = segment["end"] - current["start"] <= max_utterance
            if close and long_enough:
                current["text"] = f"{current['text']} {text}".strip()
                current["end"] = segment["end"]
                continue
        utterances.append({
            "speaker": 0,
            "start": segment["start"],
            "end": segment["end"],
            "text": text,
        })
    return utterances
