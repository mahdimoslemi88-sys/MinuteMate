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
