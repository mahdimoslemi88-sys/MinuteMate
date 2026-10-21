"""Orchestration for the minutes stage."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from minutemate.config import EngineConfig, MinutesConfig
from minutemate.errors import (
    LlmBadResponseError,
    LlmTimeoutError,
    LlmUnavailableError,
    MinutesParseError,
)
from minutemate.events import Stage
from minutemate.job import JobContext
from minutemate.minutes import chunking, parse, prompt, render
from minutemate.minutes.models import (
    ActionItem,
    Decision,
    Meeting,
    MinutesDocument,
    NeedsReview,
    OpenQuestion,
    Source,
    Speaker,
    Topic,
)
from minutemate.minutes.prompt import CORRECTION_PROMPT
from minutemate.minutes.provider import LlmProvider, create_provider

PROMPT_VERSION = "official-v1"
_RETRYABLE = (LlmBadResponseError, LlmTimeoutError, LlmUnavailableError)


def run_minutes(
    *,
    config: EngineConfig,
    ctx: JobContext,
    transcript_path: str | Path,
    out_dir: str | Path,
    stem: str,
    title: str,
    date_str: str,
    duration: float,
    speaker_map: dict | None = None,
) -> list[Path]:
    minutes = config.minutes
    out_dir = Path(out_dir)

    ctx.stage_start(Stage.MINUTES, "تولید صورت‌جلسه")

    if not minutes.is_active():
        ctx.log("مرحلهٔ صورت‌جلسه غیرفعال است (enabled=false یا provider=none).")
        ctx.stage_done(Stage.MINUTES, "غیرفعال")
        return []

    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        raise MinutesParseError(
            "فایل رونویسی ساختاریافته برای تولید صورت‌جلسه پیدا نشد.",
            hint=str(transcript_path),
        )

    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    raw_utterances = data.get("utterances") or []
    items = chunking.build_transcript(raw_utterances)
    if not items:
        raise MinutesParseError("رونویسی هیچ جملهٔ قابل استفاده‌ای ندارد.")

    speakers = _build_speakers(items, speaker_map)
    speaker_names = {speaker.speaker_id: speaker.name for speaker in speakers}
    valid_ids = {item["id"] for item in items}

    chunks = chunking.chunk_transcript(items, minutes.chunk_seconds)
    provider = create_provider(minutes)
    transcript_sha = chunking.transcript_sha256(items)

    extractions: list[dict] = []
    total = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        ctx.check_cancel()
        chunk_text = chunking.transcript_text(chunk, speaker_names)
        messages = prompt.build_extraction_messages(
            chunk_text, language=minutes.language, template=minutes.template
        )
        extractions.append(_extract(provider, messages, minutes, valid_ids, speaker_names))
        ctx.stage_progress(Stage.MINUTES, index / (total + 1), message=f"قطعه {index} از {total}")

    ctx.check_cancel()
    merged = parse.merge_extractions(extractions)
    final = parse.assign_ids(merged)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    document = _build_document(
        final=final,
        speakers=speakers,
        title=title,
        date_str=date_str,
        duration=duration,
        language=minutes.language,
        provider=provider,
        prompt_version=PROMPT_VERSION,
        generated_at=generated_at,
        chunk_count=total,
        transcript_sha=transcript_sha,
    )

    minutes_json = out_dir / f"{stem}.minutes.json"
    minutes_json.write_text(
        json.dumps(document.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    minutes_md = out_dir / "03_official_meeting_minutes.md"
    minutes_md.write_text(render.render_minutes_markdown(document), encoding="utf-8")

    artifacts = [minutes_md]
    if minutes.include_action_items:
        actions_md = out_dir / "04_action_items.md"
        actions_md.write_text(render.render_action_items_markdown(document), encoding="utf-8")
        artifacts.append(actions_md)
    artifacts.append(minutes_json)

    for path in artifacts:
        ctx.artifact(kind=path.name, path=path)

    ctx.stage_progress(Stage.MINUTES, 1.0, force=True)
    ctx.stage_done(Stage.MINUTES)

    if document.needs_review:
        ctx.log(f"{len(document.needs_review)} مورد برای بازبینی علامت خورد.", level="warning")

    return artifacts


def _extract(
    provider: LlmProvider,
    messages: list[dict],
    minutes: MinutesConfig,
    valid_ids: set[str],
    speaker_names: dict[str, str],
) -> dict:
    current = messages
    last_error: Exception | None = None

    for _ in range(2):
        try:
            text = provider.complete(
                current,
                temperature=minutes.temperature,
                max_tokens=minutes.max_output_tokens,
                timeout=minutes.timeout_seconds,
            )
            payload = parse.parse_json(text)
            return parse.validate_extraction(payload, valid_ids, speaker_names)
        except _RETRYABLE as error:
            last_error = error
            current = messages + [{"role": "user", "content": CORRECTION_PROMPT}]

    assert last_error is not None
    raise last_error


def _build_speakers(items: list[dict], speaker_map: dict | None) -> list[Speaker]:
    mapping = speaker_map or {}
    speakers: list[Speaker] = []
    seen: set[int] = set()

    for item in items:
        index = item["speakerIndex"]
        if index in seen:
            continue
        seen.add(index)

        raw = mapping.get(index)
        if isinstance(raw, str):
            speakers.append(Speaker(speaker_id=f"spk{index}", name=raw, role="", source="speakerMap"))
        elif isinstance(raw, dict):
            name = str(raw.get("name") or f"گوینده {index + 1}")
            role = str(raw.get("role") or "")
            speakers.append(Speaker(speaker_id=f"spk{index}", name=name, role=role, source="speakerMap"))
        else:
            speakers.append(
                Speaker(speaker_id=f"spk{index}", name=f"گوینده {index + 1}", role="", source="auto")
            )

    return speakers


def _build_document(
    *,
    final: dict,
    speakers: list[Speaker],
    title: str,
    date_str: str,
    duration: float,
    language: str,
    provider: LlmProvider,
    prompt_version: str,
    generated_at: str,
    chunk_count: int,
    transcript_sha: str,
) -> MinutesDocument:
    topics = [
        Topic(
            id=topic["id"],
            title=topic["title"],
            summary=topic.get("summary", ""),
            utterance_ids=topic.get("utteranceIds", []),
        )
        for topic in final.get("topics", [])
    ]
    decisions = [
        Decision(
            id=decision["id"],
            text=decision["text"],
            utterance_ids=decision.get("utteranceIds", []),
            needs_review=bool(decision.get("needsReview")),
        )
        for decision in final.get("decisions", [])
    ]
    action_items = [
        ActionItem(
            id=item["id"],
            title=item["title"],
            owner_speaker_id=item.get("ownerSpeakerId"),
            owner_name=item.get("ownerName", ""),
            due_date=item.get("dueDate"),
            due_text=item.get("dueText", ""),
            priority=item.get("priority", "medium"),
            acceptance_criteria=item.get("acceptanceCriteria", ""),
            utterance_ids=item.get("utteranceIds", []),
            needs_review=bool(item.get("needsReview")),
        )
        for item in final.get("actionItems", [])
    ]
    open_questions = [
        OpenQuestion(
            id=question["id"],
            text=question["text"],
            utterance_ids=question.get("utteranceIds", []),
        )
        for question in final.get("openQuestions", [])
    ]
    needs_review = [
        NeedsReview(field=item.get("field", ""), reason=item.get("reason", ""))
        for item in final.get("needsReview", [])
    ]

    return MinutesDocument(
        meeting=Meeting(
            title=title,
            date=date_str,
            duration_seconds=float(duration or 0.0),
            language=language,
            summary=final.get("summary", ""),
        ),
        speakers=speakers,
        topics=topics,
        decisions=decisions,
        action_items=action_items,
        open_questions=open_questions,
        needs_review=needs_review,
        source=Source(
            provider=getattr(provider, "name", "unknown"),
            model=getattr(provider, "model", ""),
            prompt_version=prompt_version,
            generated_at=generated_at,
            chunk_count=chunk_count,
            transcript_sha256=transcript_sha,
        ),
    )
