import pytest

from minutemate.errors import LlmBadResponseError
from minutemate.minutes import parse


VALID = {"u0001", "u0002"}
NAMES = {"spk0": "مهدی"}


def test_parse_json_strips_code_fences():
    payload = parse.parse_json('```json\n{"summary": "x"}\n```')
    assert payload["summary"] == "x"


def test_parse_json_rejects_non_json():
    with pytest.raises(LlmBadResponseError):
        parse.parse_json("متأسفم، نمی‌توانم.")


def test_validate_drops_items_without_witnesses():
    result = parse.validate_extraction(
        {
            "summary": "خلاصه",
            "topics": [{"title": "بدون شاهد"}, {"title": "با شاهد", "utteranceIds": ["u0001"]}],
            "decisions": [{"text": "تصویب", "utteranceIds": ["u9999"]}],
        },
        VALID,
        NAMES,
    )
    assert [topic["title"] for topic in result["topics"]] == ["با شاهد"]
    assert result["decisions"] == []
    assert len(result["needsReview"]) == 2


def test_validate_resolves_owner_and_due_date():
    result = parse.validate_extraction(
        {
            "actionItems": [
                {
                    "title": "ارسال گزارش",
                    "ownerSpeakerId": "spk0",
                    "dueDate": "2026-11-01",
                    "dueText": "اول آبان",
                    "priority": "HIGH",
                    "utteranceIds": ["u0002"],
                }
            ]
        },
        VALID,
        NAMES,
    )
    item = result["actionItems"][0]
    assert item["ownerName"] == "مهدی"
    assert item["dueDate"] == "2026-11-01"
    assert item["priority"] == "high"
    assert item["needsReview"] is False


def test_validate_flags_inferred_due_date_and_unknown_owner():
    result = parse.validate_extraction(
        {
            "actionItems": [
                {
                    "title": "پیگیری",
                    "ownerSpeakerId": "spk9",
                    "dueText": "هفتهٔ آینده",
                    "utteranceIds": ["u0001"],
                }
            ]
        },
        VALID,
        NAMES,
    )
    item = result["actionItems"][0]
    assert item["ownerSpeakerId"] is None
    assert item["ownerName"] == ""
    assert item["dueDate"] is None
    assert item["needsReview"] is True
    assert any("dueDate" in entry["field"] for entry in result["needsReview"])


def test_merge_dedupes_and_unions_witnesses():
    first = parse.validate_extraction(
        {
            "summary": "یک",
            "decisions": [{"text": "تصویب بودجه", "utteranceIds": ["u0001"]}],
            "actionItems": [{"title": "گزارش", "utteranceIds": ["u0001"]}],
        },
        VALID,
        NAMES,
    )
    second = parse.validate_extraction(
        {
            "summary": "دو",
            "decisions": [{"text": "تصویب بودجه", "utteranceIds": ["u0002"]}],
            "actionItems": [{"title": "گزارش", "utteranceIds": ["u0002"]}],
        },
        VALID,
        NAMES,
    )
    merged = parse.merge_extractions([first, second])
    assert merged["summary"] == "یک دو"
    assert len(merged["decisions"]) == 1
    assert merged["decisions"][0]["utteranceIds"] == ["u0001", "u0002"]
    assert merged["actionItems"][0]["utteranceIds"] == ["u0001", "u0002"]


def test_assign_ids_is_sequential():
    merged = {
        "summary": "",
        "topics": [{"title": "a"}, {"title": "b"}],
        "decisions": [{"text": "d"}],
        "actionItems": [{"title": "x"}],
        "openQuestions": [{"text": "q"}],
        "needsReview": [],
    }
    result = parse.assign_ids(merged)
    assert [topic["id"] for topic in result["topics"]] == ["t1", "t2"]
    assert result["decisions"][0]["id"] == "d1"
    assert result["actionItems"][0]["id"] == "a1"
    assert result["openQuestions"][0]["id"] == "q1"
