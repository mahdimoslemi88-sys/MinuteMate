"""Deliverable renderers for raw and diarized transcripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from minutemate.text.normalize import normalize


def fmt_ts(seconds: float) -> str:
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def speaker_info(speaker: int, speaker_map: dict | None) -> tuple[int, str, str]:
    raw = (speaker_map or {}).get(speaker, {})
    if isinstance(raw, str):
        return speaker + 1, raw, ""
    if isinstance(raw, dict):
        speaker_id = raw.get("id", speaker + 1)
        name = raw.get("name", f"گوینده {speaker_id}")
        role = raw.get("role", "")
        return speaker_id, name, role
    return speaker + 1, f"گوینده {speaker + 1}", ""


def export_raw_transcript(
    raw_segments: list[dict],
    out_dir: str | Path,
    title: str,
    date_str: str,
) -> Path:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "01_raw_transcript.txt"

    with target.open("w", encoding="utf-8") as handle:
        handle.write("=" * 70 + "\n")
        handle.write(f"متن کامل خام جلسه (Raw Transcript) — {title}\n")
        handle.write(f"تاریخ: {date_str}\n")
        handle.write("=" * 70 + "\n\n")
        for segment in raw_segments:
            handle.write(f"[{fmt_ts(segment['start'])} --> {fmt_ts(segment['end'])}]  {segment['text'].strip()}\n")

    return target


def export_diarized_transcript(
    utterances: list[dict],
    out_dir: str | Path,
    title: str,
    date_str: str,
    speaker_map: dict | None = None,
) -> tuple[Path, Path]:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    txt_path = out_dir / "02_diarized_cleaned_transcript.txt"
    md_path = out_dir / "02_diarized_cleaned_transcript.md"

    with txt_path.open("w", encoding="utf-8") as handle:
        handle.write("=" * 70 + "\n")
        handle.write(f"رونویسی مرتب‌شده با تفکیک گویندگان — {title}\n")
        handle.write("=" * 70 + "\n\n")
        for utterance in utterances:
            speaker_id, name, role = speaker_info(utterance["speaker"], speaker_map)
            role_suffix = f" ({role})" if role else ""
            handle.write("-" * 32 + "\n")
            handle.write(f"[{fmt_ts(utterance['start'])}]\n")
            if name == f"گوینده {speaker_id}":
                handle.write(f"گوینده {speaker_id}{role_suffix}:\n\n")
            else:
                handle.write(f"گوینده {speaker_id} ({name}{role_suffix}):\n\n")
            handle.write(f"{normalize(utterance['text'])}\n")
            if utterance.get("overlap"):
                handle.write("\n[هم‌پوشانی گویندگان: تخصیص گوینده ممکن است نادرست باشد]\n")
            handle.write("\n")

    with md_path.open("w", encoding="utf-8") as handle:
        handle.write("# رونویسی مرتب‌شده و تفکیک‌شده بر اساس گویندگان\n\n")
        handle.write(f"> **موضوع:** {title}  \n> **تاریخ:** {date_str}  \n\n---\n\n")
        for utterance in utterances:
            speaker_id, name, role = speaker_info(utterance["speaker"], speaker_map)
            role_suffix = f" — *{role}*" if role else ""
            if name == f"گوینده {speaker_id}":
                handle.write(f"### `[{fmt_ts(utterance['start'])}]` گوینده {speaker_id}{role_suffix}\n\n")
            else:
                handle.write(f"### `[{fmt_ts(utterance['start'])}]` {name} (گوینده {speaker_id}){role_suffix}\n\n")
            handle.write(f"{normalize(utterance['text'])}\n\n")
            if utterance.get("overlap"):
                handle.write("> **هشدار:** گفتار هم‌زمان شناسایی شد؛ تخصیص گوینده ممکن است نادرست باشد.\n\n")
            handle.write("---\n\n")

    return txt_path, md_path


def export_deliverables(
    raw_segments: list[dict],
    utterances: list[dict],
    out_dir: str | Path,
    title: str,
    date_str: str,
    speaker_map: dict | None = None,
) -> list[Path]:
    paths = [export_raw_transcript(raw_segments, out_dir, title, date_str)]
    paths.extend(export_diarized_transcript(utterances, out_dir, title, date_str, speaker_map))
    return paths


def build_speaker_map(values: dict[int, Any] | None) -> dict[int, dict]:
    if not values:
        return {}
    return {int(key): value for key, value in values.items()}
