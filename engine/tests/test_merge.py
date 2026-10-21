import json

from minutemate.config import EngineConfig
from minutemate.events import NullEventSink
from minutemate.job import JobContext
from minutemate.merge.align import merge_transcription_and_diarization


def _context(tmp_path) -> JobContext:
    config = EngineConfig(audio_path="audio.wav", output_dir=str(tmp_path))
    return JobContext(config, NullEventSink())


def test_merge_assigns_speakers_by_overlap(tmp_path):
    segments = {
        "audio": "audio.wav",
        "segments": [
            {"id": 0, "start": 0.0, "end": 1.0, "text": "سلام", "words": [
                {"start": 0.0, "end": 0.5, "word": "سلام", "probability": 0.9},
            ]},
            {"id": 1, "start": 5.0, "end": 6.0, "text": "خوبی", "words": [
                {"start": 5.0, "end": 5.6, "word": "خوبی", "probability": 0.9},
            ]},
        ],
    }
    speakers = {
        "audio": "audio.wav",
        "turns": [
            {"start": 0.0, "end": 2.0, "speaker": 0},
            {"start": 4.5, "end": 6.5, "speaker": 1},
        ],
    }

    segments_path = tmp_path / "segments.json"
    speakers_path = tmp_path / "speakers.json"
    segments_path.write_text(json.dumps(segments, ensure_ascii=False), encoding="utf-8")
    speakers_path.write_text(json.dumps(speakers, ensure_ascii=False), encoding="utf-8")

    result = merge_transcription_and_diarization(
        segments_path, speakers_path, tmp_path, "session", _context(tmp_path)
    )

    speakers_seen = [utterance["speaker"] for utterance in result["utterances"]]
    assert speakers_seen == [0, 1]
    assert result["utterances"][0]["text"] == "سلام"


def test_merge_flags_overlapping_speech(tmp_path):
    segments = {
        "audio": "audio.wav",
        "segments": [
            {"id": 0, "start": 1.1, "end": 1.9, "text": "همزمان", "words": [
                {"start": 1.1, "end": 1.9, "word": "همزمان", "probability": 0.9},
            ]},
        ],
    }
    speakers = {
        "audio": "audio.wav",
        "turns": [
            {"start": 0.0, "end": 2.0, "speaker": 0},
            {"start": 1.0, "end": 3.0, "speaker": 1},
        ],
    }
    segments_path = tmp_path / "segments.json"
    speakers_path = tmp_path / "speakers.json"
    segments_path.write_text(json.dumps(segments, ensure_ascii=False), encoding="utf-8")
    speakers_path.write_text(json.dumps(speakers, ensure_ascii=False), encoding="utf-8")

    result = merge_transcription_and_diarization(
        segments_path, speakers_path, tmp_path, "session", _context(tmp_path)
    )

    assert result["overlapCount"] == 1
    assert result["utterances"][0]["overlap"] is True


def test_merge_without_turns_keeps_text(tmp_path):
    segments = {
        "audio": "audio.wav",
        "segments": [
            {"id": 0, "start": 0.0, "end": 1.0, "text": "یک", "words": []},
            {"id": 1, "start": 1.2, "end": 2.0, "text": "دو", "words": []},
        ],
    }
    segments_path = tmp_path / "segments.json"
    speakers_path = tmp_path / "speakers.json"
    segments_path.write_text(json.dumps(segments, ensure_ascii=False), encoding="utf-8")
    speakers_path.write_text(json.dumps({"turns": []}, ensure_ascii=False), encoding="utf-8")

    result = merge_transcription_and_diarization(
        segments_path, speakers_path, tmp_path, "session", _context(tmp_path)
    )

    assert len(result["utterances"]) == 1
    assert result["utterances"][0]["text"] == "یک دو"
