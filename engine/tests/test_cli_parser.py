import pytest

from minutemate.cli import _build_parser


@pytest.mark.parametrize("group", ["all", "diarization", "whisper", "whisper-fa"])
def test_download_accepts_group_flag(group):
    args = _build_parser().parse_args(["models", "download", "--group", group])
    assert args.group == group


def test_download_keeps_type_alias():
    args = _build_parser().parse_args(["models", "download", "--type", "whisper"])
    assert args.group == "whisper"


def test_download_rejects_unknown_group():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["models", "download", "--group", "nope"])
