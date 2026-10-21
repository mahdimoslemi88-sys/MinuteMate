import os

from minutemate import cli


def test_env_file_from_explicit_variable(tmp_path, monkeypatch):
    env_file = tmp_path / "custom.env"
    env_file.write_text("MINUTEMATE_TEST_ENV_VALUE=from-file\n", encoding="utf-8")
    monkeypatch.setenv("MINUTEMATE_ENV_FILE", str(env_file))
    monkeypatch.delenv("MINUTEMATE_TEST_ENV_VALUE", raising=False)

    cli._load_env_files()

    assert os.environ.get("MINUTEMATE_TEST_ENV_VALUE") == "from-file"


def test_env_file_does_not_override_existing_value(tmp_path, monkeypatch):
    env_file = tmp_path / "custom.env"
    env_file.write_text("MINUTEMATE_TEST_ENV_VALUE=from-file\n", encoding="utf-8")
    monkeypatch.setenv("MINUTEMATE_ENV_FILE", str(env_file))
    monkeypatch.setenv("MINUTEMATE_TEST_ENV_VALUE", "already-set")

    cli._load_env_files()

    assert os.environ.get("MINUTEMATE_TEST_ENV_VALUE") == "already-set"


def test_empty_keys_are_loaded_as_empty(tmp_path, monkeypatch):
    env_file = tmp_path / "custom.env"
    env_file.write_text("GROQ_API_KEY=\n", encoding="utf-8")
    monkeypatch.setenv("MINUTEMATE_ENV_FILE", str(env_file))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    cli._load_env_files()

    assert os.environ.get("GROQ_API_KEY") == ""
