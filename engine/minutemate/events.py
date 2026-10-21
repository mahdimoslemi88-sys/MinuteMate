"""Engine event model and sinks. stdout is reserved for NDJSON in machine mode."""

from __future__ import annotations

import json
import sys
import threading
from dataclasses import dataclass
from typing import IO, Protocol


class EventType:
    STARTED = "started"
    STAGE = "stage"
    LOG = "log"
    ARTIFACT = "artifact"
    ERROR = "error"
    DONE = "done"


class Stage:
    MODELS = "models"
    PREPROCESS = "preprocess"
    DIARIZATION = "diarization"
    TRANSCRIPTION = "transcription"
    MERGE = "merge"
    EXPORT = "export"
    MINUTES = "minutes"


class Status:
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class EngineEvent:
    type: str
    stage: str | None = None
    status: str | None = None
    progress: float | None = None
    eta_seconds: float | None = None
    level: str | None = None
    message: str | None = None
    code: str | None = None
    hint: str | None = None
    kind: str | None = None
    path: str | None = None
    duration_seconds: float | None = None

    def to_payload(self) -> dict:
        raw = {
            "type": self.type,
            "stage": self.stage,
            "status": self.status,
            "progress": self.progress,
            "etaSeconds": self.eta_seconds,
            "level": self.level,
            "message": self.message,
            "code": self.code,
            "hint": self.hint,
            "kind": self.kind,
            "path": self.path,
            "durationSeconds": self.duration_seconds,
        }
        return {key: value for key, value in raw.items() if value is not None}


class EventSink(Protocol):
    def emit(self, event: EngineEvent) -> None: ...


class JsonEventSink:
    def __init__(self, stream: IO[str] | None = None) -> None:
        self._stream = stream or sys.stdout
        self._lock = threading.Lock()

    def emit(self, event: EngineEvent) -> None:
        line = json.dumps(event.to_payload(), ensure_ascii=False) + "\n"
        with self._lock:
            self._stream.write(line)
            self._stream.flush()


class TextEventSink:
    def __init__(self, stream: IO[str] | None = None) -> None:
        self._stream = stream or sys.stderr
        self._lock = threading.Lock()

    def emit(self, event: EngineEvent) -> None:
        if event.type == EventType.STAGE:
            percent = f"{event.progress * 100:5.1f}%" if event.progress is not None else "  -  "
            line = f"[{event.stage}] {percent} {event.message or ''}".rstrip()
        elif event.type == EventType.ARTIFACT:
            line = f"[artifact] {event.kind}: {event.path}"
        elif event.type == EventType.ERROR:
            line = f"[error] {event.message}"
        elif event.type == EventType.DONE:
            line = f"[done] {event.message or ''}".rstrip()
        elif event.type == EventType.STARTED:
            line = f"[started] {event.message or ''}".rstrip()
        else:
            line = f"[{event.level or 'info'}] {event.message or ''}".rstrip()
        with self._lock:
            self._stream.write(line + "\n")
            self._stream.flush()


class NullEventSink:
    def emit(self, event: EngineEvent) -> None:
        return None
