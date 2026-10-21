"""Prompt construction for the minutes extraction and merge calls."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

_EXTRACTION_SCHEMA = """{
  "summary": "string",
  "topics": [{"title": "string", "summary": "string", "utteranceIds": ["u0001"]}],
  "decisions": [{"text": "string", "utteranceIds": ["u0001"]}],
  "actionItems": [{"title": "string", "ownerSpeakerId": "spk0", "dueText": "string", "dueDate": "YYYY-MM-DD or null", "priority": "high|medium|low", "acceptanceCriteria": "string", "utteranceIds": ["u0001"]}],
  "openQuestions": [{"text": "string", "utteranceIds": ["u0001"]}]
}"""


@lru_cache(maxsize=None)
def _read(name: str) -> str:
    return (files("minutemate") / "resources" / "prompts" / name).read_text(encoding="utf-8").strip()


def _render(name: str, **values: str) -> str:
    text = _read(name)
    for key, value in values.items():
        text = text.replace(f"__{key.upper()}__", value)
    return text


SYSTEM_PROMPT = _read("minutes_system.md")
CORRECTION_PROMPT = _read("minutes_correction_fa.md")


def build_extraction_messages(chunk_text: str, *, language: str = "fa", template: str = "official-v1") -> list[dict]:
    user = _render(
        "minutes_extraction_fa.md",
        template=template,
        language=language,
        schema=_EXTRACTION_SCHEMA,
        text=chunk_text,
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def build_merge_messages(partials: list[dict], *, language: str = "fa", template: str = "official-v1") -> list[dict]:
    user = _render(
        "minutes_merge_fa.md",
        template=template,
        language=language,
        schema=_EXTRACTION_SCHEMA,
        partials=json.dumps(partials, ensure_ascii=False),
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
