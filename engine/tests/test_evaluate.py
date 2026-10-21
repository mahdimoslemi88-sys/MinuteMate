from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("evaluate", ROOT / "scripts" / "evaluate.py")
assert SPEC and SPEC.loader
evaluate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = evaluate
SPEC.loader.exec_module(evaluate)


def test_normalize_text_handles_persian_variants():
    assert evaluate.normalize_text("مي‌خواهم ۱۲۳، سلام!") == "می خواهم 123 سلام"
    assert evaluate.tokenize("كِتاب‌ها") == ["کتاب", "ها"]


def test_word_error_counts():
    counts = evaluate.edit_counts(["a", "b", "c"], ["a", "x", "c"])
    assert (counts.substitutions, counts.deletions, counts.insertions) == (1, 0, 0)
    assert counts.reference_length == 3
    assert counts.rate == pytest.approx(1 / 3)


def test_insertions_and_deletions():
    insertion = evaluate.edit_counts(["a", "b"], ["a", "x", "b"])
    assert (insertion.substitutions, insertion.deletions, insertion.insertions) == (0, 0, 1)
    deletion = evaluate.edit_counts(["a", "b", "c"], ["a", "c"])
    assert (deletion.substitutions, deletion.deletions, deletion.insertions) == (0, 1, 0)


def test_fallback_matcher_agrees_with_rapidfuzz(monkeypatch):
    reference = ["a", "b", "c", "d"]
    hypotheses = (["a", "x", "c", "d"], ["a", "c"], ["a", "b", "c", "d", "e"])
    expected = [evaluate.edit_counts(reference, hypothesis) for hypothesis in hypotheses]
    monkeypatch.setattr(evaluate, "Levenshtein", None)
    for hypothesis, want in zip(hypotheses, expected):
        actual = evaluate.edit_counts(reference, hypothesis)
        assert (actual.substitutions, actual.deletions, actual.insertions) == (
            want.substitutions,
            want.deletions,
            want.insertions,
        )


def test_character_error_rate_on_unspaced_persian():
    reference = "سلامدنیا"
    hypothesis = "سلامدنی"
    counts = evaluate.edit_counts(list(reference), list(hypothesis))
    assert counts.rate == pytest.approx(1 / len(reference))


def test_diarization_perfect_and_speaker_mapping():
    reference = [
        {"start": 0.0, "end": 5.0, "speaker": "A"},
        {"start": 5.0, "end": 10.0, "speaker": "B"},
    ]
    hypothesis = [
        {"start": 0.0, "end": 5.0, "speaker": "X"},
        {"start": 5.0, "end": 10.0, "speaker": "Y"},
    ]
    metrics = evaluate.diarization_metrics(reference, hypothesis)
    assert metrics["der"] == pytest.approx(0.0, abs=1e-9)
    assert metrics["jer"] == pytest.approx(0.0, abs=1e-9)
    assert metrics["speaker_count_error"] == 0
    assert metrics["mapping"] == {"A": "X", "B": "Y"}


def test_diarization_counts_false_alarm_and_speaker_error():
    reference = [{"start": 0.0, "end": 5.0, "speaker": "A"}]
    hypothesis = [
        {"start": 0.0, "end": 5.0, "speaker": "X"},
        {"start": 6.0, "end": 7.0, "speaker": "Z"},
    ]
    metrics = evaluate.diarization_metrics(reference, hypothesis)
    assert metrics["der"] > 0
    assert metrics["speaker_count_error"] == 1


def test_diarization_without_hypothesis_is_explicit():
    metrics = evaluate.diarization_metrics(
        [{"start": 0.0, "end": 5.0, "speaker": "A"}],
        [],
    )
    assert metrics["der"] is None
    assert metrics["note"]


def test_read_rttm_and_speaker_turns(tmp_path: Path):
    rttm = tmp_path / "sample.rttm"
    rttm.write_text(
        "SPEAKER sample 1 0.000 2.500 <NA> <NA> spk0 <NA> <NA>\n"
        "# comment\n"
        "SPEAKER sample 1 3.000 1.000 <NA> <NA> spk1 <NA> <NA>\n",
        encoding="utf-8",
    )
    turns = evaluate.read_rttm(rttm)
    assert turns == [
        {"start": 0.0, "end": 2.5, "speaker": "spk0"},
        {"start": 3.0, "end": 4.0, "speaker": "spk1"},
    ]

    speakers = tmp_path / "sample.speakers.json"
    speakers.write_text(
        json.dumps({"turns": [{"start": 1.0, "end": 2.0, "speaker": 0}]}),
        encoding="utf-8",
    )
    assert evaluate.read_speaker_turns(speakers) == [{"start": 1.0, "end": 2.0, "speaker": "0"}]


def test_read_hypothesis_prefers_transcript_json(tmp_path: Path):
    (tmp_path / "sample_transcript.json").write_text(
        json.dumps({"utterances": [{"speaker": 0, "start": 0.0, "end": 1.0, "text": "سلام"}]}),
        encoding="utf-8",
    )
    (tmp_path / "sample.txt").write_text("[0.00 - 1.00] متن اشتباه\n", encoding="utf-8")
    text, path = evaluate.read_hypothesis_text(tmp_path, "sample")
    assert text == "سلام"
    assert path and path.name == "sample_transcript.json"


def test_summarize_events_computes_stage_seconds():
    lines = [
        (0.2, json.dumps({"type": "started", "message": "x"})),
        (0.5, json.dumps({"type": "stage", "stage": "preprocess", "status": "running", "progress": 0})),
        (3.5, json.dumps({"type": "stage", "stage": "preprocess", "status": "done", "progress": 1})),
        (4.0, json.dumps({"type": "done", "durationSeconds": 4.0})),
    ]
    events, summary = evaluate.summarize_events(lines)
    assert len(events) == 4
    assert summary["stageSeconds"] == {"preprocess": 3.0}
    assert summary["done"]["durationSeconds"] == 4.0


def test_load_saved_engine_reads_events_file(tmp_path: Path):
    events = [
        {"type": "stage", "stage": "transcription", "status": "running", "_t": 1.0},
        {"type": "artifact", "path": "a.txt", "_t": 9.5},
        {"type": "stage", "stage": "transcription", "status": "done", "_t": 10.0},
        {"type": "done", "durationSeconds": 10.0, "_t": 10.2},
    ]
    (tmp_path / "sample.events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events),
        encoding="utf-8",
    )
    summary = evaluate.load_saved_engine(tmp_path, "sample")
    assert summary["stageSeconds"] == {"transcription": 9.0}
    assert summary["done"]["durationSeconds"] == 10.0
    assert summary["artifactCount"] == 1
    assert summary["returnCode"] == 0


def test_report_marks_draft_truth():
    report = {
        "meta": {
            "generatedAt": "2026-10-20 10:00:00",
            "engineVersion": "0.1.0",
            "commit": "abc1234",
            "device": "cpu",
            "computeType": "int8",
            "beamSize": 1,
            "numThreads": 6,
            "draftCount": 1,
        },
        "results": [
            {
                "id": "mm19-0062",
                "title": "sample",
                "condition": "far-field",
                "truthStatus": "draft",
                "wer": 0.5,
                "cer": 0.2,
                "wordCounts": {"substitutions": 1, "deletions": 0, "insertions": 0, "reference": 2},
                "diarization": {"der": 0.1, "jer": 0.2, "speaker_count_error": 0},
                "engine": {"wallSeconds": 10.0, "stageSeconds": {"transcription": 5.0}},
                "warnings": ["متن مرجع پیش‌نویس است."],
            }
        ],
    }
    markdown = evaluate.render_markdown(report)
    assert "draft" in markdown
    assert "50.0%" in markdown
    assert "⚠️" in markdown


def test_registry_paths_resolve_relative_to_registry(tmp_path: Path):
    registry = tmp_path / "registry.json"
    sample = {"audio": "audio/x.wav", "truthText": "truth/x.txt", "truthRttm": "truth/x.rttm"}
    paths = evaluate.resolve_sample_paths(registry, sample)
    assert paths["audio"] == tmp_path / "audio" / "x.wav"
    assert paths["truthText"] == tmp_path / "truth" / "x.txt"


def test_regression_gate_flags_worse_wer():
    report = {"results": [{"id": "a", "wer": 0.30, "diarization": {"der": 0.2}}, {"id": "b", "wer": 0.1}]}
    baseline = {"results": [{"id": "a", "wer": 0.28, "diarization": {"der": 0.2}}, {"id": "b", "wer": 0.1}]}

    findings = evaluate.regression_findings(report, baseline)

    assert len(findings) == 1
    assert findings[0]["metric"] == "WER"
    assert findings[0]["delta"] == pytest.approx(0.02)
    assert "WER" in evaluate.render_regressions(findings)


def test_regression_gate_allows_improvement_and_tolerance():
    report = {"results": [{"id": "a", "wer": 0.20, "diarization": {"der": 0.30}}]}
    baseline = {"results": [{"id": "a", "wer": 0.25, "diarization": {"der": 0.29}}]}

    assert evaluate.regression_findings(report, baseline) == []


def test_regression_gate_ignores_missing_metrics_and_samples():
    report = {"results": [{"id": "a"}, {"id": "new", "wer": 0.9}]}
    baseline = {"results": [{"id": "a", "wer": 0.1}]}

    assert evaluate.regression_findings(report, baseline) == []
