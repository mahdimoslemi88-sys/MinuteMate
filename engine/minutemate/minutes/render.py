"""Markdown renderers for the structured minutes document."""

from __future__ import annotations

from minutemate.minutes.models import MinutesDocument
from minutemate.text.renderers import fmt_ts

_EMPTY = "_موردی ثبت نشد._"


def render_minutes_markdown(document: MinutesDocument) -> str:
    meeting = document.meeting
    lines: list[str] = []

    lines.append(f"# صورت‌جلسه — {meeting.title}")
    lines.append("")
    lines.append(f"**تاریخ:** {meeting.date}  ")
    lines.append(f"**مدت:** {fmt_duration(meeting.duration_seconds)}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## حاضرین")
    lines.append("")
    if document.speakers:
        for speaker in document.speakers:
            role = f" — *{speaker.role}*" if speaker.role else ""
            lines.append(f"- {speaker.name} (`{speaker.speaker_id}`){role}")
    else:
        lines.append(_EMPTY)
    lines.append("")

    lines.append("## خلاصهٔ مدیریتی")
    lines.append("")
    lines.append(meeting.summary or _EMPTY)
    lines.append("")

    lines.append("## موضوعات")
    lines.append("")
    if document.topics:
        for topic in document.topics:
            lines.append(f"### {topic.id}. {topic.title}")
            lines.append("")
            if topic.summary:
                lines.append(topic.summary)
                lines.append("")
            lines.append(f"شاهد: {_witnesses(topic.utterance_ids)}")
            lines.append("")
    else:
        lines.append(_EMPTY)
        lines.append("")

    lines.append("## مصوبات")
    lines.append("")
    if document.decisions:
        for decision in document.decisions:
            suffix = " ⚠️" if decision.needs_review else ""
            lines.append(f"- **{decision.id}.** {decision.text}{suffix}")
            lines.append(f"  - شاهد: {_witnesses(decision.utterance_ids)}")
    else:
        lines.append(_EMPTY)
    lines.append("")

    lines.append("## سؤالات باز")
    lines.append("")
    if document.open_questions:
        for question in document.open_questions:
            lines.append(f"- **{question.id}.** {question.text}")
            if question.utterance_ids:
                lines.append(f"  - شاهد: {_witnesses(question.utterance_ids)}")
    else:
        lines.append(_EMPTY)
    lines.append("")

    lines.append("## اقدامات")
    lines.append("")
    lines.append(render_action_items_table(document))
    lines.append("")

    if document.needs_review:
        lines.append("## نیازمند بازبینی")
        lines.append("")
        for item in document.needs_review:
            lines.append(f"- `{item.field}` — {item.reason}")
        lines.append("")

    if document.source:
        lines.append("---")
        lines.append("")
        lines.append(
            f"> تولیدشده با `{document.source.provider}` / `{document.source.model}` "
            f"(prompt `{document.source.prompt_version}`) در {document.source.generated_at}."
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_action_items_table(document: MinutesDocument) -> str:
    lines: list[str] = []
    lines.append("| # | اقدام | مسئول | مهلت | اولویت | معیار پذیرش |")
    lines.append("| :-- | :-- | :-- | :-- | :-- | :-- |")
    if not document.action_items:
        lines.append("| — | " + _EMPTY.replace("_", "") + " | — | — | — | — |")
        return "\n".join(lines)

    for item in document.action_items:
        owner = item.owner_name or "نامشخص"
        if item.needs_review:
            owner += " ⚠️"
        due = item.due_date or (item.due_text or "—")
        lines.append(
            "| {id} | {title} | {owner} | {due} | {priority} | {criteria} |".format(
                id=item.id,
                title=item.title.replace("|", "/"),
                owner=owner,
                due=due.replace("|", "/"),
                priority=item.priority,
                criteria=(item.acceptance_criteria or "—").replace("|", "/"),
            )
        )
    return "\n".join(lines)


def render_action_items_markdown(document: MinutesDocument) -> str:
    lines: list[str] = []
    lines.append(f"# اقدامات جلسه — {document.meeting.title}")
    lines.append("")
    lines.append(f"**تاریخ:** {document.meeting.date}  ")
    lines.append("")
    lines.append(render_action_items_table(document))
    lines.append("")

    lines.append("## ماتریس مسئولیت (RACI)")
    lines.append("")
    lines.append("| اقدام | R (مجری) | A (تصویب‌کننده) | C (مشورت) | I (مطلع) |")
    lines.append("| :-- | :-- | :-- | :-- | :-- |")
    if document.action_items:
        for item in document.action_items:
            owner = item.owner_name or "نامشخص"
            lines.append(f"| {item.id} | {owner} | {owner} | — | — |")
    else:
        lines.append("| — | — | — | — | — |")
    lines.append("")

    lines.append("## جزئیات")
    lines.append("")
    if document.action_items:
        for item in document.action_items:
            lines.append(f"### {item.id}. {item.title}")
            lines.append("")
            lines.append(f"- مسئول: {item.owner_name or 'نامشخص'}")
            lines.append(f"- مهلت: {item.due_date or item.due_text or '—'}")
            lines.append(f"- اولویت: {item.priority}")
            lines.append(f"- معیار پذیرش: {item.acceptance_criteria or '—'}")
            lines.append(f"- شاهد: {_witnesses(item.utterance_ids)}")
            lines.append("")
    else:
        lines.append(_EMPTY)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def fmt_duration(seconds: float) -> str:
    total = int(round(seconds or 0))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours} ساعت و {minutes} دقیقه"
    if minutes:
        return f"{minutes} دقیقه و {secs} ثانیه"
    return f"{secs} ثانیه"


def _witnesses(ids: list[str]) -> str:
    if not ids:
        return "—"
    return ", ".join(f"`{value}`" for value in ids)
