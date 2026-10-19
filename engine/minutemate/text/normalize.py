"""Data-driven Persian text normalization (half-spaces, terminology, fillers)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from minutemate.paths import resource_path

_FILLER = re.compile(r"\b(خب|یعنی|در واقع)\s+(خب|یعنی|در واقع)\b")
_WHITESPACE = re.compile(r"\s+")


@lru_cache(maxsize=4)
def _load_rules(path: str) -> tuple[list[tuple[re.Pattern[str], str]], ...]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rules: list[tuple[re.Pattern[str], str]] = []

    for term, replacement in data.get("terms", []):
        rules.append((re.compile(rf"\b{re.escape(term)}\b"), replacement))

    for pattern, replacement in data.get("regex", []):
        rules.append((re.compile(pattern), replacement))

    return tuple(rules)


def normalize(text: str, glossary: str | Path | None = None) -> str:
    if not text:
        return ""
    rules = _load_rules(str(glossary or resource_path("glossary_fa.json")))
    cleaned = text
    for pattern, replacement in rules:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = _FILLER.sub(r"\1", cleaned)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    return cleaned
