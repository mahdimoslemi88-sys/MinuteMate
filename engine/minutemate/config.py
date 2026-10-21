"""Engine configuration model and job payload mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from urllib.parse import urlparse

from minutemate.env import cuda_device_count
from minutemate.errors import InputError

DEVICES = ("auto", "cuda", "cpu")
MINUTES_PROVIDERS = ("none", "openai-compatible", "ollama")
DEFAULT_API_KEY_ENV = "MINUTEMATE_LLM_API_KEY"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


@dataclass
class MinutesConfig:
    enabled: bool = False
    provider: str = "none"
    base_url: str | None = None
    model: str | None = None
    api_key_env: str = DEFAULT_API_KEY_ENV
    temperature: float = 0.2
    max_output_tokens: int = 4000
    timeout_seconds: int = 120
    chunk_seconds: int = 900
    language: str = "fa"
    template: str = "official-v1"
    include_action_items: bool = True
    redact: bool = False

    @classmethod
    def from_payload(cls, payload: Any) -> "MinutesConfig":
        data = payload or {}
        if not isinstance(data, dict):
            raise InputError("کلید minutes باید یک object باشد.")

        if "apiKey" in data or "api_key" in data:
            raise InputError(
                "کلید API نباید داخل job باشد.",
                hint="کلید فقط از متغیر محیطی نام‌برده در apiKeyEnv خوانده می‌شود.",
            )

        return cls(
            enabled=bool(data.get("enabled", False)),
            provider=str(data.get("provider") or "none").lower(),
            base_url=data.get("baseUrl") or data.get("base_url"),
            model=data.get("model"),
            api_key_env=str(
                data.get("apiKeyEnv") or data.get("api_key_env") or DEFAULT_API_KEY_ENV
            ),
            temperature=float(data.get("temperature", 0.2)),
            max_output_tokens=int(data.get("maxOutputTokens", data.get("max_output_tokens", 4000)) or 4000),
            timeout_seconds=int(data.get("timeoutSeconds", data.get("timeout_seconds", 120)) or 120),
            chunk_seconds=int(data.get("chunkSeconds", data.get("chunk_seconds", 900)) or 900),
            language=str(data.get("language") or "fa"),
            template=str(data.get("template") or "official-v1"),
            include_action_items=bool(
                data.get("includeActionItems", data.get("include_action_items", True))
            ),
            redact=bool(data.get("redact", False)),
        )

    def is_active(self) -> bool:
        return self.enabled and self.provider != "none"

    def validate(self) -> None:
        if self.provider not in MINUTES_PROVIDERS:
            raise InputError(
                f"provider نامعتبر: {self.provider}",
                hint="مقادیر مجاز: none, openai-compatible, ollama",
            )

        if not self.is_active():
            return

        if self.provider == "openai-compatible":
            if not self.base_url:
                raise InputError("برای provider=openai-compatible مقدار baseUrl الزامی است.")
            if not self.model:
                raise InputError("برای provider=openai-compatible مقدار model الزامی است.")
        elif self.provider == "ollama":
            if not self.base_url:
                self.base_url = DEFAULT_OLLAMA_URL
            if not self.model:
                raise InputError("برای provider=ollama مقدار model الزامی است.")

        if self.base_url:
            _validate_base_url(self.base_url)

        if self.timeout_seconds <= 0:
            raise InputError("timeoutSeconds باید بزرگ‌تر از صفر باشد.")

        if self.chunk_seconds < 60:
            raise InputError("chunkSeconds باید حداقل ۶۰ ثانیه باشد.")


def _validate_base_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and (parsed.hostname or "") in {"127.0.0.1", "localhost"}:
        return
    raise InputError(
        "baseUrl باید https باشد.",
        hint="فقط http برای Ollama روی 127.0.0.1/localhost مجاز است.",
    )


def _parallel_value(value: Any) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value or "auto").strip().lower()


@dataclass
class EngineConfig:
    audio_path: str
    output_dir: str = ""
    stem: str = "meeting"
    title: str | None = None
    date: str | None = None
    num_speakers: int = 4
    device: str = "auto"
    compute_type: str = "auto"
    language: str = "fa"
    ffmpeg_bin: str = "ffmpeg"
    models_dir: str | None = None
    beam_size: int = 1
    batch_size: int = 0
    asr_chunk_seconds: float = 1800.0
    asr_chunk_overlap_seconds: float = 5.0
    speaker_embedding: str = "wespeaker"
    asr_model: str = "turbo"
    asr_provider: str = "local"  # local | groq
    groq_model: str = "whisper-large-v3-turbo"
    parallel_stages: str = "auto"
    auto_download_models: bool = False
    num_threads: int = 6
    speaker_map: dict[int, Any] = field(default_factory=dict)
    session_dir: str | None = None
    sessions_root: str | None = None
    metrics_dir: str | None = None
    minutes: MinutesConfig = field(default_factory=MinutesConfig)

    @classmethod
    def from_payload(cls, payload: dict) -> "EngineConfig":
        audio = payload.get("audioPath") or payload.get("audio_path")
        output = payload.get("outputDirectory") or payload.get("outDir") or payload.get("output_dir")
        session_dir = payload.get("sessionDirectory") or payload.get("session_dir")
        sessions_root = payload.get("sessionsRoot") or payload.get("sessions_root")
        if not audio:
            raise InputError("مسیر فایل ورودی مشخص نشده است.", hint="کلید audioPath در job الزامی است.")
        if not output and not session_dir and not sessions_root:
            raise InputError(
                "مسیر پوشه خروجی مشخص نشده است.",
                hint="کلید outputDirectory یا sessionDirectory/sessionsRoot در job الزامی است.",
            )

        raw_map = payload.get("speakerMap") or payload.get("speaker_map") or {}
        speaker_map: dict[int, Any] = {}
        for key, value in raw_map.items():
            try:
                speaker_map[int(key)] = value
            except (TypeError, ValueError):
                continue

        return cls(
            audio_path=str(audio),
            output_dir=str(output or ""),
            stem=str(payload.get("stem") or "meeting"),
            title=payload.get("title"),
            date=payload.get("date"),
            num_speakers=int(payload.get("numSpeakers", payload.get("num_speakers", 4)) or 0),
            device=str(payload.get("device") or "auto").lower(),
            compute_type=str(payload.get("computeType") or payload.get("compute_type") or "auto").lower(),
            language=str(payload.get("language") or "fa"),
            ffmpeg_bin=str(payload.get("ffmpegPath") or payload.get("ffmpeg_bin") or "ffmpeg"),
            models_dir=payload.get("modelsDir") or payload.get("models_dir"),
            beam_size=int(payload.get("beamSize", payload.get("beam_size", 1)) or 1),
            batch_size=int(payload.get("batchSize", payload.get("batch_size", 0)) or 0),
            asr_chunk_seconds=float(payload.get("asrChunkSeconds", 1800.0) if payload.get("asrChunkSeconds", 1800.0) is not None else 1800.0),
            asr_chunk_overlap_seconds=float(payload.get("asrChunkOverlapSeconds", 5.0) if payload.get("asrChunkOverlapSeconds", 5.0) is not None else 5.0),
            speaker_embedding=str(payload.get("speakerEmbedding", payload.get("speaker_embedding", "wespeaker")) or "wespeaker"),
            parallel_stages=_parallel_value(payload.get("parallelStages", payload.get("parallel_stages", "auto"))),
            auto_download_models=bool(payload.get("autoDownloadModels", payload.get("auto_download_models", False))),
            num_threads=int(payload.get("numThreads", payload.get("num_threads", 6)) or 6),
            speaker_map=speaker_map,
            session_dir=session_dir,
            sessions_root=sessions_root,
            metrics_dir=payload.get("metricsDirectory") or payload.get("metrics_dir"),
            minutes=MinutesConfig.from_payload(payload.get("minutes")),
            asr_model=str(payload.get("asrModel", payload.get("asr_model", "turbo")) or "turbo").lower(),
            asr_provider=str(payload.get("asrProvider", payload.get("asr_provider", "local")) or "local").lower(),
            groq_model=str(payload.get("groqModel", payload.get("groq_model", "whisper-large-v3-turbo")) or "whisper-large-v3-turbo"),
        )

    def resolved_device(self) -> str:
        device = (self.device or "auto").lower()
        if device not in DEVICES:
            raise InputError(f"دستگاه نامعتبر: {self.device}", hint="مقادیر مجاز: auto, cuda, cpu")
        if device == "auto":
            return "cuda" if cuda_device_count() > 0 else "cpu"
        return device

    def resolved_compute_type(self, device: str | None = None) -> str:
        compute = (self.compute_type or "auto").lower()
        if compute != "auto":
            return compute
        return "float16" if (device or self.resolved_device()) == "cuda" else "int8"

    def resolved_batch_size(self) -> int:
        return max(0, self.batch_size)

    def resolved_parallel(self, device: str) -> bool:
        if self.parallel_stages == "auto":
            return device == "cuda"
        return self.parallel_stages == "on"

    def effective_title(self) -> str:
        return self.title or f"جلسه {self.stem}"

    def effective_date(self) -> str:
        if self.date:
            return str(self.date)
        return date.today().isoformat()

    def validate(self) -> None:
        from pathlib import Path

        audio = Path(self.audio_path)
        if not audio.exists():
            raise InputError(f"فایل ورودی پیدا نشد: {self.audio_path}")

        if self.num_speakers < 0:
            raise InputError("تعداد گویندگان نمی‌تواند منفی باشد.")

        if self.parallel_stages not in {"auto", "on", "off"}:
            raise InputError("parallelStages باید auto، on یا off باشد.")
        if self.asr_chunk_seconds < 0:
            raise InputError("asrChunkSeconds نمی‌تواند منفی باشد.", hint="۰ یعنی بدون بخش‌بندی.")
        if self.asr_chunk_overlap_seconds < 0:
            raise InputError("asrChunkOverlapSeconds نمی‌تواند منفی باشد.")
        if self.asr_chunk_seconds > 0 and self.asr_chunk_overlap_seconds >= self.asr_chunk_seconds:
            raise InputError("هم‌پوشانی چانک ASR باید کمتر از طول چانک باشد.")
        if self.batch_size < 0:
            raise InputError("batchSize نمی‌تواند منفی باشد.", hint="۰ یعنی خاموش؛ برای GPU مقدار ۴ تا ۱۶ پیشنهاد می‌شود.")
        if self.batch_size > 64:
            raise InputError("batchSize بیش از ۶۴ پشتیبانی نمی‌شود.")

        self.minutes.validate()
        self.resolved_device()
