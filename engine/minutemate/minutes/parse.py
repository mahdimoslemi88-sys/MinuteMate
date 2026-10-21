"""Parsing, validation and merging of LLM extraction payloads."""

from __future__ import annotations

import json
import re
from datetime import date

from minutemate.errors import LlmBadResponseError
from minutemate.text.normalize import normalize

_FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\s*|\s*```$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PRIORITIES = {"high", "medium", "low"}


def parse_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = _FENCE.sub("", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise LlmBadResponseError("پاسخ مدل JSON معتبر نبود.")

    try:
        payload = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as error:
        raise LlmBadResponseError("پاسخ مدل JSON معتبر نبود.", hint=str(error)) from error

    if not isinstance(payload, dict):
        raise LlmBadResponseError("پاسخ مدل باید یک object JSON باشد.")

    return payload


def normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", normalize(str(value or "")).strip())


def _witnesses(raw: dict, valid_ids: set[str]) -> list[str]:
    values = raw.get("utteranceIds") or raw.get("utterance_ids") or []
    if not isinstance(values, list):
        return []
    seen: list[str] = []
    for value in values:
        text = str(value).strip()
        if text in valid_ids and text not in seen:
            seen.append(text)
    return seen


def validate_extraction(
    payload: dict,
    valid_ids: set[str],
    speaker_names: dict[str, str],
) -> dict:
    topics: list[dict] = []
    decisions: list[dict] = []
    action_items: list[dict] = []
    open_questions: list[dict] = []
    needs_review: list[dict] = []

    summary = normalize_text(payload.get("summary"))

    for index, raw in enumerate(_as_list(payload.get("topics"))):
        if not isinstance(raw, dict):
            continue
        title = normalize_text(raw.get("title"))
        witnesses = _witnesses(raw, valid_ids)
        if not title:
            continue
        if not witnesses:
            needs_review.append(
                {"field": f"topics[{index}]", "reason": "بدون شاهد utterance؛ حذف شد."}
            )
            continue
        topics.append(
            {"title": title, "summary": normalize_text(raw.get("summary")), "utteranceIds": witnesses}
        )

    for index, raw in enumerate(_as_list(payload.get("decisions"))):
        if not isinstance(raw, dict):
            continue
        text = normalize_text(raw.get("text"))
        witnesses = _witnesses(raw, valid_ids)
        if not text:
            continue
        if not witnesses:
            needs_review.append(
                {"field": f"decisions[{index}]", "reason": "بدون شاهد utterance؛ حذف شد."}
            )
            continue
        decisions.append({"text": text, "utteranceIds": witnesses, "needsReview": False})

    for index, raw in enumerate(_as_list(payload.get("actionItems") or payload.get("action_items"))):
        if not isinstance(raw, dict):
            continue
        title = normalize_text(raw.get("title"))
        witnesses = _witnesses(raw, valid_ids)
        if not title:
            continue
        if not witnesses:
            needs_review.append(
                {"field": f"actionItems[{index}]", "reason": "بدون شاهد utterance؛ حذف شد."}
            )
            continue

        owner_id = str(raw.get("ownerSpeakerId") or raw.get("owner_speaker_id") or "").strip() or None
        if owner_id and owner_id not in speaker_names:
            owner_id = None
        owner_name = speaker_names.get(owner_id, "") if owner_id else ""

        priority = str(raw.get("priority") or "medium").strip().lower()
        if priority not in _PRIORITIES:
            priority = "medium"

        due_text = normalize_text(raw.get("dueText") or raw.get("due_text"))
        due_date = raw.get("dueDate") or raw.get("due_date")
        needs_review_item = False
        if isinstance(due_date, str) and _ISO_DATE.match(due_date.strip()):
            due_date = due_date.strip()
            try:
                date.fromisoformat(due_date)
            except ValueError:
                due_date = None
        else:
            due_date = None

        if due_date is None and due_text:
            needs_review_item = True
            needs_review.append(
                {
                    "field": f"actionItems[{index}].dueDate",
                    "reason": f"تاریخ صریح نیست؛ از «{due_text}» استنباط شده.",
                }
            )

        action_items.append(
            {
                "title": title,
                "ownerSpeakerId": owner_id,
                "ownerName": owner_name,
                "dueDate": due_date,
                "dueText": due_text,
                "priority": priority,
                "acceptanceCriteria": normalize_text(
                    raw.get("acceptanceCriteria") or raw.get("acceptance_criteria")
                ),
                "utteranceIds": witnesses,
                "needsReview": needs_review_item,
            }
        )

    for index, raw in enumerate(_as_list(payload.get("openQuestions") or payload.get("open_questions"))):
        if not isinstance(raw, dict):
            continue
        text = normalize_text(raw.get("text"))
        if not text:
            continue
        open_questions.append({"text": text, "utteranceIds": _witnesses(raw, valid_ids)})

    return {
        "summary": summary,
        "topics": topics,
        "decisions": decisions,
        "actionItems": action_items,
        "openQuestions": open_questions,
        "needsReview": needs_review,
    }


def merge_extractions(parts: list[dict]) -> dict:
    merged = {
        "summary": "",
        "topics": [],
        "decisions": [],
        "actionItems": [],
        "openQuestions": [],
        "needsReview": [],
    }

    summaries: list[str] = []
    topic_index: dict[str, dict] = {}
    decision_index: dict[str, dict] = {}
    action_index: dict[str, dict] = {}
    question_index: dict[str, dict] = {}

    for part in parts:
        summary = normalize_text(part.get("summary"))
        if summary and summary not in summaries:
            summaries.append(summary)

        for topic in part.get("topics", []):
            key = topic["title"]
            existing = topic_index.get(key)
            if existing is None:
                topic_index[key] = {"title": topic["title"], "summary": topic.get("summary", ""), "utteranceIds": list(topic["utteranceIds"])}
            else:
                if len(topic.get("summary", "")) > len(existing["summary"]):
                    existing["summary"] = topic["summary"]
                _union(existing["utteranceIds"], topic["utteranceIds"])

        for decision in part.get("decisions", []):
            key = decision["text"]
            existing = decision_index.get(key)
            if existing is None:
                decision_index[key] = {"text": decision["text"], "utteranceIds": list(decision["utteranceIds"]), "needsReview": bool(decision.get("needsReview"))}
            else:
                _union(existing["utteranceIds"], decision["utteranceIds"])

        for item in part.get("actionItems", []):
            key = item["title"]
            existing = action_index.get(key)
            if existing is None:
                action_index[key] = dict(item)
                action_index[key]["utteranceIds"] = list(item["utteranceIds"])
            else:
                _union(existing["utteranceIds"], item["utteranceIds"])
                if not existing.get("ownerSpeakerId") and item.get("ownerSpeakerId"):
                    existing["ownerSpeakerId"] = item["ownerSpeakerId"]
                    existing["ownerName"] = item.get("ownerName", "")
                if not existing.get("dueText") and item.get("dueText"):
                    existing["dueText"] = item["dueText"]
                    existing["dueDate"] = item.get("dueDate")
                if not existing.get("acceptanceCriteria") and item.get("acceptanceCriteria"):
                    existing["acceptanceCriteria"] = item["acceptanceCriteria"]

        for question in part.get("openQuestions", []):
            key = question["text"]
            existing = question_index.get(key)
            if existing is None:
                question_index[key] = {"text": question["text"], "utteranceIds": list(question["utteranceIds"])}
            else:
                _union(existing["utteranceIds"], question["utteranceIds"])

        merged["needsReview"].extend(part.get("needsReview", []))

    merged["summary"] = " ".join(summaries).strip()
    merged["topics"] = list(topic_index.values())
    merged["decisions"] = list(decision_index.values())
    merged["actionItems"] = list(action_index.values())
    merged["openQuestions"] = list(question_index.values())
    return merged


def assign_ids(merged: dict) -> dict:
    result = dict(merged)
    result["topics"] = [
        {"id": f"t{index}", **topic} for index, topic in enumerate(merged.get("topics", []), start=1)
    ]
    result["decisions"] = [
        {"id": f"d{index}", **decision} for index, decision in enumerate(merged.get("decisions", []), start=1)
    ]
    result["actionItems"] = [
        {"id": f"a{index}", **item} for index, item in enumerate(merged.get("actionItems", []), start=1)
    ]
    result["openQuestions"] = [
        {"id": f"q{index}", **question} for index, question in enumerate(merged.get("openQuestions", []), start=1)
    ]
    return result


def _as_list(value: object) -> list:
    if isinstance(value, list):
        return value
    return []


def _union(target: list[str], values: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)
