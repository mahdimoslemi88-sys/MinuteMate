from __future__ import annotations

from minutemate.minutes.prompt import (
    CORRECTION_PROMPT,
    SYSTEM_PROMPT,
    build_extraction_messages,
    build_merge_messages,
)


def test_extraction_prompt_fills_placeholders() -> None:
    messages = build_extraction_messages("متن نمونه [u0001]", language="fa", template="official-v1")
    assert messages[0]["content"] == SYSTEM_PROMPT
    user = messages[1]["content"]
    assert "متن نمونه [u0001]" in user
    assert "official-v1" in user
    assert '"actionItems"' in user
    assert "__SCHEMA__" not in user
    assert "__TEXT__" not in user


def test_merge_prompt_and_correction_have_no_placeholders() -> None:
    user = build_merge_messages([{"summary": "جلسه"}])[1]["content"]
    assert '"summary": "جلسه"' in user
    assert "__PARTIALS__" not in user
    assert "__" not in CORRECTION_PROMPT
    assert "JSON" in CORRECTION_PROMPT
