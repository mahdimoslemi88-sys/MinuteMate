"""Typed engine errors carrying a stable code, a Persian message and an optional hint."""

from __future__ import annotations


class EngineError(Exception):
    code = "engine_error"

    def __init__(self, message: str, hint: str | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        if code:
            self.code = code


class InputError(EngineError):
    code = "input_invalid"


class ModelMissingError(EngineError):
    code = "model_missing"


class FfmpegError(EngineError):
    code = "ffmpeg_failed"


class CudaUnavailableError(EngineError):
    code = "cuda_unavailable"


class CancelledError(EngineError):
    code = "cancelled"

    def __init__(self, message: str = "پردازش توسط کاربر متوقف شد.") -> None:
        super().__init__(message)


class StageError(EngineError):
    code = "stage_failed"


def to_payload(error: EngineError) -> dict:
    payload = {"code": getattr(error, "code", "engine_error"), "message": error.message}
    hint = getattr(error, "hint", None)
    if hint:
        payload["hint"] = hint
    return payload
