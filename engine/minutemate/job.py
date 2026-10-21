"""Job context: configuration, event sink, cancellation and progress reporting."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from minutemate.config import EngineConfig
from minutemate.errors import CancelledError, EngineError, to_payload
from minutemate.events import EngineEvent, EventSink, EventType, Status
from minutemate.logging_setup import get_logger


class JobContext:
    def __init__(self, config: EngineConfig, sink: EventSink) -> None:
        self.config = config
        self.sink = sink
        self.logger = get_logger("minutemate.job")
        self._cancel = threading.Event()
        self._started = time.time()
        self._progress_state: dict[str, tuple[float, float]] = {}
        self._event_lock = threading.Lock()
        self._stage_started_at: dict[str, float] = {}
        self.stage_seconds: dict[str, float] = {}

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def cancel(self) -> None:
        self._cancel.set()

    def check_cancel(self) -> None:
        if self._cancel.is_set():
            raise CancelledError()

    def elapsed(self) -> float:
        return time.time() - self._started

    def emit(self, event: EngineEvent) -> None:
        with self._event_lock:
            self.sink.emit(event)

    def log(self, message: str, level: str = "info") -> None:
        self.logger.log(getattr(logging, level.upper(), logging.INFO), message)
        self.emit(EngineEvent(type=EventType.LOG, level=level, message=message))

    def started(self, message: str | None = None) -> None:
        self.emit(EngineEvent(type=EventType.STARTED, message=message))

    def stage_start(self, stage: str, message: str | None = None) -> None:
        self.logger.info("stage %s started", stage)
        self._stage_started_at[stage] = time.time()
        self.emit(EngineEvent(type=EventType.STAGE, stage=stage, status=Status.RUNNING, progress=0.0, message=message))

    def stage_progress(
        self,
        stage: str,
        fraction: float,
        message: str | None = None,
        eta_seconds: float | None = None,
        force: bool = False,
    ) -> None:
        fraction = max(0.0, min(1.0, fraction))
        now = time.time()
        last_at, last_value = self._progress_state.get(stage, (0.0, -1.0))
        if not force and fraction - last_value < 0.005 and now - last_at < 0.5:
            return
        self._progress_state[stage] = (now, fraction)
        self.emit(
            EngineEvent(
                type=EventType.STAGE,
                stage=stage,
                status=Status.RUNNING,
                progress=round(fraction, 4),
                eta_seconds=round(eta_seconds, 1) if eta_seconds is not None else None,
                message=message,
            )
        )

    def stage_done(self, stage: str, message: str | None = None) -> None:
        self.logger.info("stage %s done", stage)
        started = self._stage_started_at.pop(stage, None)
        if started is not None:
            self.stage_seconds[stage] = round(time.time() - started, 3)
        self.emit(
            EngineEvent(
                type=EventType.STAGE,
                stage=stage,
                status=Status.DONE,
                progress=1.0,
                message=message,
            )
        )

    def artifact(self, kind: str, path: Any) -> None:
        self.emit(EngineEvent(type=EventType.ARTIFACT, kind=kind, path=str(path)))

    def done(self, message: str | None = None) -> None:
        self.emit(
            EngineEvent(
                type=EventType.DONE,
                status=Status.DONE,
                message=message,
                duration_seconds=round(self.elapsed(), 1),
            )
        )

    def fail(self, error: EngineError) -> None:
        self.logger.error("%s: %s", getattr(error, "code", "engine_error"), error.message)
        payload = to_payload(error)
        self.emit(
            EngineEvent(
                type=EventType.ERROR,
                status=Status.FAILED,
                code=payload["code"],
                message=payload["message"],
                hint=payload.get("hint"),
            )
        )
