from minutemate.models import registry


def test_resolve_paths(tmp_path):
    resolved = registry.resolve(tmp_path)

    assert resolved.models_dir == tmp_path
    assert resolved.segmentation_model.name == "model.onnx"
    assert resolved.speaker_embedding.name.endswith(".onnx")


def test_verify_reports_missing(tmp_path):
    missing = registry.verify(tmp_path)

    assert missing
    paths = {item.rel_path for item in missing}
    assert any("whisper" in path for path in paths)
    assert any("speaker" in path for path in paths)


def test_required_groups_turbo_skips_persian_model():
    groups = registry.required_group_ids("turbo")

    assert registry.WHISPER.id in groups
    assert registry.WHISPER_FA.id not in groups
    assert registry.DIARIZATION.id in groups


def test_required_groups_persian_uses_fa_model():
    for alias in ("fa", "persian", "fa-large-v3", "FA"):
        groups = registry.required_group_ids(alias)
        assert registry.WHISPER_FA.id in groups
        assert registry.WHISPER.id not in groups


def test_verify_with_required_groups_ignores_persian_model(tmp_path):
    missing = registry.verify(tmp_path, registry.required_group_ids("turbo"))

    paths = {item.rel_path for item in missing}
    assert paths
    assert not any("persian" in path for path in paths)


def test_resolve_persian_points_to_fa_dir(tmp_path):
    resolved = registry.resolve(tmp_path, asr_model="fa")

    assert resolved.whisper_dir.name == "faster-whisper-large-v3-persian-ct2-int8"
    assert resolved.whisper_dir == resolved.whisper_fa_dir


def test_resolve_turbo_points_to_turbo_dir(tmp_path):
    resolved = registry.resolve(tmp_path, asr_model="turbo")

    assert resolved.whisper_dir.name == "faster-whisper-large-v3-turbo"
