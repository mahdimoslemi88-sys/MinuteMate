"""Project and resource path resolution."""

from __future__ import annotations

import os
from pathlib import Path

MODELS_DIR_VARIABLE = "MINUTEMATE_MODELS_DIR"


def package_dir() -> Path:
    return Path(__file__).resolve().parent


def engine_dir() -> Path:
    return package_dir().parent


def project_root() -> Path:
    return engine_dir().parent


def resource_path(name: str) -> Path:
    return package_dir() / "resources" / name


def resolve_models_dir(explicit: str | os.PathLike[str] | None = None) -> Path:
    if explicit:
        return Path(os.path.expandvars(str(explicit))).expanduser().resolve()

    from_env = os.environ.get(MODELS_DIR_VARIABLE)
    if from_env:
        return Path(os.path.expandvars(from_env)).expanduser().resolve()

    return (project_root() / "models").resolve()


def ensure_dir(path: str | os.PathLike[str]) -> Path:
    resolved = Path(path).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved
