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
from minutemate.minutes.render import (
    fmt_duration,
    render_action_items_markdown,
    render_minutes_markdown,
)


def _document() -> MinutesDocument:
    return MinutesDocument(
        meeting=Meeting(title="جلسهٔ بودجه", date="2026-10-20", duration_seconds=3720, summary="خلاصهٔ کل"),
        speakers=[Speaker(speaker_id="spk0", name="مهدی", role="سرپرست")],
        topics=[Topic(id="t1", title="بودجه", summary="بحث", utterance_ids=["u0001"])],
        decisions=[Decision(id="d1", text="تصویب شد", utterance_ids=["u0001"])],
        action_items=[
            ActionItem(
                id="a1",
                title="ارسال گزارش",
                owner_speaker_id="spk0",
                owner_name="مهدی",
                due_date="2026-11-01",
                priority="high",
                acceptance_criteria="ارسال شد",
                utterance_ids=["u0002"],
            )
        ],
        open_questions=[OpenQuestion(id="q1", text="سؤال؟", utterance_ids=["u0001"])],
        needs_review=[NeedsReview(field="topics[0]", reason="شاهد ندارد")],
        source=Source(
            provider="openai-compatible",
            model="gpt-x",
            prompt_version="official-v1",
            generated_at="2026-10-20T00:00:00+00:00",
            chunk_count=2,
            transcript_sha256="abc",
        ),
    )


def test_minutes_markdown_contains_sections():
    text = render_minutes_markdown(_document())
    assert "# صورت‌جلسه — جلسهٔ بودجه" in text
    assert "## مصوبات" in text
    assert "**d1.** تصویب شد" in text
    assert "`u0001`" in text
    assert "## نیازمند بازبینی" in text
    assert "openai-compatible" in text


def test_action_items_markdown_has_raci():
    text = render_action_items_markdown(_document())
    assert "## ماتریس مسئولیت (RACI)" in text
    assert "| a1 | مهدی |" in text
    assert "2026-11-01" in text


def test_fmt_duration_humanizes():
    assert fmt_duration(3720) == "1 ساعت و 2 دقیقه"
    assert fmt_duration(90) == "1 دقیقه و 30 ثانیه"
    assert fmt_duration(30) == "30 ثانیه"


def test_empty_document_renders_placeholders():
    document = MinutesDocument(meeting=Meeting(title="خالی", date="2026-10-20"))
    text = render_minutes_markdown(document)
    assert "_موردی ثبت نشد._" in text
    assert "RACI" in render_action_items_markdown(document)
