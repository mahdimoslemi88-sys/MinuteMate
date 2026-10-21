import json
import os
from datetime import datetime, timedelta

import pytest

from minutemate import session
from minutemate.errors import InputError


def test_slugify_is_persian_safe():
    assert session.slugify("جلسهٔ هفتگی تیم فنی") == "جلسه-هفتگی-تیم-فنی"
    assert session.slugify("   ") == "session"
    assert session.slugify("A/B  C") == "a-b-c"


def test_build_session_id():
    assert session.build_session_id("2026-10-19", "جلسهٔ هفتگی") == "2026-10-19-جلسه-هفتگی"


def test_resolve_layout_flat_mode(tmp_path):
    layout = session.resolve_layout(
        session_dir=None,
        sessions_root=None,
        output_dir=tmp_path / "out",
        stem="s",
        title="t",
        date_str="2026-10-19",
    )
    assert layout.is_session is False
    assert layout.work_dir == layout.out_dir == layout.root


def test_resolve_layout_explicit_session(tmp_path):
    layout = session.resolve_layout(
        session_dir=tmp_path / "sessions" / "2026-10-19-x",
        sessions_root=None,
        output_dir=None,
        stem="s",
        title="t",
        date_str="2026-10-19",
    )
    assert layout.is_session is True
    assert layout.raw_dir == layout.root / "raw"
    assert layout.work_dir == layout.root / "work"
    assert layout.out_dir == layout.root / "out"


def test_resolve_layout_sessions_root_derives_id(tmp_path):
    layout = session.resolve_layout(
        session_dir=None,
        sessions_root=tmp_path / "sessions",
        output_dir=None,
        stem="s",
        title="جلسه بودجه",
        date_str="2026-10-19",
    )
    assert layout.root.name == "2026-10-19-جلسه-بودجه"


def test_resolve_layout_sessions_root_avoids_collision(tmp_path):
    root = tmp_path / "sessions"
    first = session.resolve_layout(
        session_dir=None,
        sessions_root=root,
        output_dir=None,
        stem="s",
        title="جلسه بودجه",
        date_str="2026-10-19",
    )
    first.root.mkdir(parents=True)

    second = session.resolve_layout(
        session_dir=None,
        sessions_root=root,
        output_dir=None,
        stem="s",
        title="جلسه بودجه",
        date_str="2026-10-19",
    )
    assert second.root != first.root
    assert second.root.name.endswith("-2")


def test_manifest_roundtrip(tmp_path):
    manifest = session.build_manifest(
        session_id="2026-10-19-x",
        title="جلسه",
        date_str="2026-10-19",
        source={"fileName": "a.mp3"},
        speakers=[{"id": 0, "name": "مهدی", "role": None, "confidence": "high"}],
        status="raw",
    )
    path = session.write_manifest(tmp_path / "session.json", manifest)
    loaded = session.read_manifest(path)
    assert loaded["schemaVersion"] == 1
    assert loaded["speakers"][0]["name"] == "مهدی"


def test_read_manifest_missing_returns_none(tmp_path):
    assert session.read_manifest(tmp_path / "nope.json") is None


def test_read_manifest_invalid_raises(tmp_path):
    bad = tmp_path / "session.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(InputError):
        session.read_manifest(bad)


def test_scan_sessions_and_index(tmp_path):
    root = tmp_path / "sessions"
    good = root / "2026-10-19-a"
    good.mkdir(parents=True)
    session.write_manifest(
        good / "session.json",
        session.build_manifest(session_id="2026-10-19-a", title="جلسه الف", date_str="2026-10-19"),
    )
    (root / "2026-10-18-b").mkdir(parents=True)

    entries = session.scan_sessions(root)
    assert [entry["id"] for entry in entries] == ["2026-10-19-a", "2026-10-18-b"]
    assert entries[0]["valid"] is True
    assert entries[1]["valid"] is False

    index_path = session.write_index(tmp_path, root)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["schemaVersion"] == 1
    assert len(index["sessions"]) == 2


def test_parse_age():
    assert session.parse_age("30d") == timedelta(days=30)
    assert session.parse_age("12h") == timedelta(hours=12)
    with pytest.raises(InputError):
        session.parse_age("soon")


def test_classify_artifact():
    assert session.classify_artifact("01_raw_transcript.txt") == "out"
    assert session.classify_artifact("session.minutes.json") == "out"
    assert session.classify_artifact("session.segments.json") == "work"
    assert session.classify_artifact("session_16k_mono.wav") == "work"
    assert session.classify_artifact("session_transcript.json") == "work"


def test_prune_work_respects_age_and_transcripts(tmp_path):
    root = tmp_path / "sessions"
    work = root / "2026-10-19-a" / "work"
    work.mkdir(parents=True)

    old_wav = work / "a_16k_mono.wav"
    old_transcript = work / "a_transcript.json"
    fresh = work / "a.segments.json"
    for path in (old_wav, old_transcript, fresh):
        path.write_text("x", encoding="utf-8")

    past = (datetime.now() - timedelta(days=40)).timestamp()
    os.utime(old_wav, (past, past))
    os.utime(old_transcript, (past, past))

    removed = session.prune_work(root, timedelta(days=30), keep_transcripts=True)
    assert removed == [old_wav]
    assert old_wav.exists() is False
    assert old_transcript.exists() is True
    assert fresh.exists() is True


def test_prune_work_dry_run_keeps_files(tmp_path):
    root = tmp_path / "sessions"
    work = root / "2026-10-19-a" / "work"
    work.mkdir(parents=True)
    old = work / "a.segments.json"
    old.write_text("x", encoding="utf-8")
    past = (datetime.now() - timedelta(days=100)).timestamp()
    os.utime(old, (past, past))

    removed = session.prune_work(root, timedelta(days=30), dry_run=True)
    assert removed == [old]
    assert old.exists() is True


def test_archive_session(tmp_path):
    root = tmp_path / "sessions"
    work = root / "2026-10-19-a" / "work"
    work.mkdir(parents=True)
    (work / "a.speakers.json").write_text("{}", encoding="utf-8")
    (work / "sub").mkdir()
    (work / "sub" / "x.txt").write_text("hi", encoding="utf-8")

    archive_path = session.archive_session(root, "2026-10-19-a", delete=True)
    assert archive_path.exists()
    assert work.exists() is False

    import zipfile

    with zipfile.ZipFile(archive_path) as archive:
        assert "a.speakers.json" in archive.namelist()
        assert "sub/x.txt" in archive.namelist()


def test_adopt_flat_output(tmp_path):
    flat = tmp_path / "flat"
    flat.mkdir()
    (flat / "session_16k_mono.wav").write_text("wav", encoding="utf-8")
    (flat / "session.segments.json").write_text("{}", encoding="utf-8")
    (flat / "01_raw_transcript.txt").write_text("raw", encoding="utf-8")
    (flat / "03_official_meeting_minutes.md").write_text("mins", encoding="utf-8")
    (flat / "session.minutes.json").write_text("{}", encoding="utf-8")

    destination = session.adopt_flat_output(
        flat,
        session_dir=tmp_path / "sessions" / "2026-10-19-x",
        session_id="2026-10-19-x",
        title="جلسه",
        date_str="2026-10-19",
    )

    assert (destination / "work" / "session_16k_mono.wav").exists()
    assert (destination / "work" / "session.segments.json").exists()
    assert (destination / "out" / "01_raw_transcript.txt").exists()
    assert (destination / "out" / "03_official_meeting_minutes.md").exists()
    assert (destination / "out" / "session.minutes.json").exists()
    assert not (flat / "01_raw_transcript.txt").exists()

    manifest = session.read_manifest(destination / "session.json")
    assert manifest["status"] == "minutes"
    assert any(item["kind"] == "03_official_meeting_minutes.md" for item in manifest["artifacts"])
