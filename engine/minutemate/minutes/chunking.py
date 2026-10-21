"""Transcript chunking and text shaping for the minutes stage."""

from __future__ import annotations

import hashlib
import json

from minutemate.text.normalize import normalize


def build_transcript(raw_utterances: list[dict]) -> list[dict]:
    items: list[dict] = []
    for index, utterance in enumerate(raw_utterances, start=1):
        text = normalize(str(utterance.get("text", ""))).strip()
        if not text:
            continue
        speaker_index = int(utterance.get("speaker", 0))
        items.append(
            {
                "id": f"u{index:04d}",
                "speakerIndex": speaker_index,
                "speakerId": f"spk{speaker_index}",
                "start": float(utterance.get("start", 0.0)),
                "end": float(utterance.get("end", 0.0)),
                "text": text,
            }
        )
    return items


def chunk_transcript(
    items: list[dict],
    chunk_seconds: int,
    max_utterances: int = 400,
) -> list[list[dict]]:
    if not items:
        return []

    chunks: list[list[dict]] = []
    current: list[dict] = []
    current_start = items[0]["start"]

    for item in items:
        too_long = bool(current) and (item["end"] - current_start) > chunk_seconds
        too_many = len(current) >= max_utterances
        if current and (too_long or too_many):
            chunks.append(current)
            current = []
            current_start = item["start"]
        current.append(item)

    if current:
        chunks.append(current)

    return chunks


def transcript_text(items: list[dict], speaker_names: dict[str, str] | None = None) -> str:
    names = speaker_names or {}
    lines: list[str] = []
    for item in items:
        label = names.get(item["speakerId"], item["speakerId"])
        lines.append(f"[{item['id']}] {label}: {item['text']}")
    return "\n".join(lines)


def transcript_sha256(items: list[dict]) -> str:
    canonical = json.dumps(items, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
