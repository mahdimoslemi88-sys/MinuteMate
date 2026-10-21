"""Groq Whisper API provider for MinuteMate.

OpenAI-compatible endpoint: https://api.groq.com/openai/v1/audio/transcriptions
Models: whisper-large-v3, whisper-large-v3-turbo
Free tier: 2,000 req/day, 7,200 audio sec/hour, 28,800 audio sec/day
Optimized for 30-second chunks.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from minutemate.errors import StageError


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_TRANSCRIBE_ENDPOINT = f"{GROQ_BASE_URL}/audio/transcriptions"

DEFAULT_MODEL = "whisper-large-v3-turbo"
FALLBACK_MODEL = "whisper-large-v3"

GROQ_MAX_FILE_MB = 100
GROQ_MAX_DURATION_SEC = 30 * 60  # 30 minutes practical limit per file
GROQ_OPTIMAL_CHUNK_SEC = 30  # Groq is optimized for 30-second segments


@dataclass
class GroqConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    language: str = "fa"
    timeout_sec: int = 60
    max_retries: int = 3
    retry_backoff_sec: float = 2.0


@dataclass
class TranscriptionResult:
    text: str
    language: str | None
    duration: float
    segments: list[dict[str, Any]]
    words: list[dict[str, Any]] | None


class GroqTranscriber:
    def __init__(self, config: GroqConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "User-Agent": "MinuteMate/0.1.0",
        })

    def transcribe_file(
        self,
        audio_path: str | Path,
        *,
        prompt: str | None = None,
        response_format: str = "verbose_json",
        timestamp_granularities: list[str] | None = None,
    ) -> TranscriptionResult:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise StageError(f"فایل صوتی پیدا نشد: {audio_path}")

        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > GROQ_MAX_FILE_MB:
            raise StageError(
                f"فایل صوتی بزرگ‌تر از {GROQ_MAX_FILE_MB} MB است ({file_size_mb:.1f} MB). "
                "فایل را چانک کنید یا فشرده‌تر enkode کنید."
            )

        data = {
            "model": self.config.model,
            "language": self.config.language,
            "response_format": response_format,
        }
        if prompt:
            data["prompt"] = prompt
        if timestamp_granularities:
            data["timestamp_granularities[]"] = timestamp_granularities

        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                with open(audio_path, "rb") as f:
                    files = {"file": (audio_path.name, f, "audio/mpeg")}
                    resp = self.session.post(
                        GROQ_TRANSCRIBE_ENDPOINT,
                        data=data,
                        files=files,
                        timeout=self.config.timeout_sec,
                    )
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("retry-after", "5"))
                    last_error = f"Rate limited (429). Retry after {retry_after}s"
                    if attempt < self.config.max_retries:
                        time.sleep(retry_after)
                        continue
                    raise StageError(last_error)
                resp.raise_for_status()
                result = resp.json()
                return self._parse_response(result)
            except requests.exceptions.Timeout:
                last_error = f"Timeout after {self.config.timeout_sec}s"
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                if e.response.status_code in (401, 403):
                    raise StageError(
                        "Groq API key نامعتبر یا منقضی شده. "
                        "کلید را در .env (GROQ_API_KEY) بررسی کنید."
                    ) from e
                if e.response.status_code == 413:
                    raise StageError("فایل صوتی بزرگ‌تر از حد مجاز 100 MB است.") from e
            except requests.exceptions.RequestException as e:
                last_error = f"Network error: {e}"

            if attempt < self.config.max_retries:
                backoff = self.config.retry_backoff_sec * (2 ** attempt)
                time.sleep(backoff)

        raise StageError(f"Groq transcription failed after {self.config.max_retries + 1} attempts: {last_error}")

    def _parse_response(self, data: dict) -> TranscriptionResult:
        text = data.get("text", "").strip()
        language = data.get("language")
        duration = data.get("duration", 0.0)

        segments = []
        words = None

        if "segments" in data:
            for seg in data["segments"]:
                segments.append({
                    "id": seg.get("id", len(segments)),
                    "start": seg.get("start", 0.0),
                    "end": seg.get("end", 0.0),
                    "text": seg.get("text", "").strip(),
                    "avg_logprob": seg.get("avg_logprob"),
                    "no_speech_prob": seg.get("no_speech_prob"),
                })

        if "words" in data and data["words"]:
            words = []
            for w in data["words"]:
                words.append({
                    "word": w.get("word", ""),
                    "start": w.get("start", 0.0),
                    "end": w.get("end", 0.0),
                    "probability": w.get("probability"),
                })

        return TranscriptionResult(
            text=text,
            language=language,
            duration=duration,
            segments=segments,
            words=words,
        )


def transcribe_groq(
    audio_path: str | Path,
    api_key: str,
    *,
    model: str = DEFAULT_MODEL,
    language: str = "fa",
    prompt: str | None = None,
    timeout_sec: int = 60,
) -> TranscriptionResult:
    """Convenience function for single-file transcription."""
    config = GroqConfig(
        api_key=api_key,
        model=model,
        language=language,
        timeout_sec=timeout_sec,
    )
    transcriber = GroqTranscriber(config)
    return transcriber.transcribe_file(audio_path, prompt=prompt)


class GroqChunkedTranscriber:
    """Transcribes long audio by splitting into 30-second chunks via VAD boundaries."""

    def __init__(
        self,
        config: GroqConfig,
        chunk_sec: int = GROQ_OPTIMAL_CHUNK_SEC,
        overlap_sec: float = 1.0,
        ffmpeg_bin: str = "ffmpeg",
    ):
        self.config = config
        self.chunk_sec = chunk_sec
        self.overlap_sec = overlap_sec
        self.ffmpeg_bin = ffmpeg_bin
        self.transcriber = GroqTranscriber(config)

    def transcribe_long(
        self,
        audio_path: str | Path,
        vad_segments: list[dict[str, float]],
        *,
        prompt: str | None = None,
        progress_cb: callable | None = None,
    ) -> TranscriptionResult:
        """Transcribe long audio using VAD segments grouped into ~30s chunks.

        Args:
            audio_path: Path to preprocessed WAV (16kHz mono)
            vad_segments: List of {"start": float, "end": float} from VAD
            prompt: Optional initial prompt for biasing
            progress_cb: Callback(chunk_index, total_chunks, chunk_result)

        Returns:
            Merged TranscriptionResult with adjusted timestamps
        """
        from minutemate.audio.wav import duration_seconds

        audio_path = Path(audio_path)
        total_dur = duration_seconds(audio_path)

        # Group VAD segments into chunks of ~chunk_sec
        chunks = self._group_vad_segments(vad_segments, total_dur)
        total_chunks = len(chunks)

        all_segments: list[dict] = []
        all_words: list[dict] = []
        full_text_parts: list[str] = []
        current_offset = 0.0

        for i, (chunk_start, chunk_end) in enumerate(chunks):
            if progress_cb:
                progress_cb(i + 1, total_chunks, f"{chunk_start:.1f}-{chunk_end:.1f}s")

            # Extract chunk to temp file using ffmpeg
            chunk_path = audio_path.parent / f".chunk_{i}_{audio_path.stem}.wav"
            try:
                import subprocess
                duration = chunk_end - chunk_start
                cmd = [
                    self.ffmpeg_bin, "-y", "-nostdin",
                    "-ss", str(chunk_start),
                    "-t", str(duration),
                    "-i", str(audio_path),
                    "-c:a", "pcm_s16le",
                    "-ar", "16000",
                    "-ac", "1",
                    str(chunk_path),
                ]
                subprocess.run(cmd, check=True, capture_output=True)

                # Transcribe chunk
                result = self.transcriber.transcribe_file(
                    chunk_path,
                    prompt=prompt,
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"],
                )

                # Adjust timestamps
                for seg in result.segments:
                    seg["start"] += chunk_start
                    seg["end"] += chunk_start
                    seg["id"] = len(all_segments)
                    all_segments.append(seg)

                if result.words:
                    for w in result.words:
                        w["start"] += chunk_start
                        w["end"] += chunk_start
                        all_words.append(w)

                full_text_parts.append(result.text)

            finally:
                if chunk_path.exists():
                    chunk_path.unlink(missing_ok=True)

        return TranscriptionResult(
            text=" ".join(full_text_parts).strip(),
            language=self.config.language,
            duration=total_dur,
            segments=all_segments,
            words=all_words if all_words else None,
        )

    def _group_vad_segments(
        self,
        vad_segments: list[dict[str, float]],
        total_duration: float,
    ) -> list[tuple[float, float]]:
        """Group VAD segments into chunks of ~chunk_sec with overlap."""
        if not vad_segments:
            return [(0.0, total_duration)]

        chunks: list[tuple[float, float]] = []
        current_start = vad_segments[0]["start"]
        current_end = current_start

        for seg in vad_segments:
            seg_start = seg["start"]
            seg_end = seg["end"]

            if seg_end - current_start > self.chunk_sec:
                # Close current chunk
                chunks.append((current_start, current_end + self.overlap_sec))
                # Start new chunk with overlap
                current_start = max(0.0, seg_start - self.overlap_sec)
                current_end = seg_end
            else:
                current_end = seg_end

        # Add final chunk
        if current_end > current_start:
            chunks.append((current_start, min(current_end + self.overlap_sec, total_duration)))

        return chunks


# Round-robin state for multiple API keys
_groq_key_index = 0
_groq_keys_cache: list[str] | None = None


def get_groq_api_keys() -> list[str]:
    """Get all Groq API keys from environment (comma-separated)."""
    global _groq_keys_cache
    if _groq_keys_cache is not None:
        return _groq_keys_cache

    raw = os.environ.get("GROQ_API_KEY") or os.environ.get("MINUTEMATE_GROQ_API_KEY") or ""
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    _groq_keys_cache = keys
    return keys


def get_groq_api_key() -> str | None:
    """Get next Groq API key using round-robin for load balancing across rate limits."""
    keys = get_groq_api_keys()
    if not keys:
        return None
    global _groq_key_index
    key = keys[_groq_key_index % len(keys)]
    _groq_key_index = (_groq_key_index + 1) % len(keys)
    return key