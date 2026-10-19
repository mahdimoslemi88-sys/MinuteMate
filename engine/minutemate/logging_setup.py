"""Logging configuration. All logs go to stderr so stdout stays a clean protocol channel."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_configured = False


def configure_logging(level: str = "INFO", log_file: str | Path | None = None) -> None:
    global _configured
    if _configured:
        return

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
