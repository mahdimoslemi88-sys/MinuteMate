"""Benchmark runner for MinuteMate: WER/CER/DER/JER, RTF and per-stage timing.

Examples:
    python scripts/evaluate.py --run-all
    python scripts/evaluate.py --hyp-dir data/benchmarks/work/mm19-0062 --out data/benchmarks/reports/report.md
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ENGINE_DIR = ROOT / "engine"
DEFAULT_REGISTRY = ROOT / "data" / "benchmarks" / "registry.json"
DEFAULT_WORK_DIR = ROOT / "data" / "benchmarks" / "work"
DEFAULT_REPORT_DIR = ROOT / "data" / "benchmarks" / "reports"

try:
    from rapidfuzz.distance import Levenshtein
except Exception:  # pragma: no cover - exercised only without rapidfuzz
    Levenshtein = None

_TRANSLATE = str.maketrans({
    "ي": "ی",
    "ى": "ی",
    "ك": "ک",
    "ۀ": "ه",
    "ة": "ه",
    "ؤ": "و",
    "إ": "ا",
    "أ": "ا",
    "ٱ": "ا",
    "\u200c": " ",
    "\u200d": " ",
    "\u200e": "",
    "\u200f": "",
})
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_PUNCT = re.compile(r"[^\w\s]")
WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFC", text or "")
    value = value.translate(_TRANSLATE).translate(_DIGITS)
    value = _DIACRITICS.sub("", value)
    value = _PUNCT.sub(" ", value)
    return WHITESPACE.sub(" ", value).strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    return normalized.split() if normalized else []


def normalize_chars(text: str) -> str:
    return normalize_text(text).replace(" ", "")


def portable_path(value: Any) -> Any:
    if not value:
        return value
    try:
        path = Path(str(value)).resolve()
        return path.relative_to(ROOT).as_posix()
    except (ValueError, OSError):
        return Path(str(value)).name


@dataclass
class EditCounts:
    substitutions: int = 0
    deletions: int = 0
    insertions: int = 0
    reference_length: int = 0

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def rate(self) -> float | None:
        if self.reference_length == 0:
            return None
        return self.errors / self.reference_length


def _fallback_counts(reference: list[str], hypothesis: list[str]) -> EditCounts:
    n, m = len(reference), len(hypothesis)
    if n * m > 4_000_000:
        raise RuntimeError(
            "rapidfuzz لازم است: pip install \"rapidfuzz>=3\" (برای متن‌های بلند)"
        )
    previous: list[tuple[int, int, int, int]] = [(j, 0, 0, j) for j in range(m + 1)]
    for i in range(1, n + 1):
        current: list[tuple[int, int, int, int]] = [(i, 0, i, 0)]
        for j in range(1, m + 1):
            if reference[i - 1] == hypothesis[j - 1]:
                current.append(previous[j - 1])
                continue
            candidates = [
                (previous[j - 1][0] + 1, previous[j - 1][1] + 1, previous[j - 1][2], previous[j - 1][3]),
                (previous[j][0] + 1, previous[j][1], previous[j][2] + 1, previous[j][3]),
                (current[j - 1][0] + 1, current[j - 1][1], current[j - 1][2], current[j - 1][3] + 1),
            ]
            current.append(min(candidates))
        previous = current
    _, substitutions, deletions, insertions = previous[m]
    return EditCounts(substitutions, deletions, insertions, n)


def edit_counts(reference: list[str], hypothesis: list[str]) -> EditCounts:
    if not reference:
        return EditCounts(0, 0, len(hypothesis), 0)
    if Levenshtein is None:
        return _fallback_counts(reference, hypothesis)

    substitutions = deletions = insertions = 0
    for tag, src_start, src_end, dst_start, dst_end in Levenshtein.opcodes(reference, hypothesis):
        ref_len = src_end - src_start
        hyp_len = dst_end - dst_start
        common = min(ref_len, hyp_len)
        if tag == "replace":
            substitutions += common
            deletions += ref_len - common
            insertions += hyp_len - common
        elif tag == "delete":
            deletions += ref_len
        elif tag == "insert":
            insertions += hyp_len
    return EditCounts(substitutions, deletions, insertions, len(reference))


def audio_duration(path: Path) -> float | None:
    try:
        import wave

        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate() or 1
            return handle.getnframes() / float(rate)
    except Exception:
        return None


def read_rttm(path: Path) -> list[dict]:
    turns: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 8 or parts[0].upper() != "SPEAKER":
            continue
        try:
            start = float(parts[3])
            duration = float(parts[4])
        except ValueError:
            continue
        turns.append({"start": start, "end": start + duration, "speaker": parts[7]})
    return turns


def read_speaker_turns(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    turns = payload.get("turns") or payload.get("speakers") or []
    return [
        {"start": float(turn["start"]), "end": float(turn["end"]), "speaker": str(turn["speaker"])}
        for turn in turns
        if turn.get("end", 0) > turn.get("start", 0)
    ]


def _masks(turns: list[dict], labels: list[str], frames: int, step: float) -> dict[str, Any]:
    import numpy as np

    masks = {label: np.zeros(frames, dtype=bool) for label in labels}
    for turn in turns:
        label = str(turn["speaker"])
        if label not in masks:
            continue
        start = max(0, int(round(turn["start"] / step)))
        end = min(frames, int(round(turn["end"] / step)))
        if end > start:
            masks[label][start:end] = True
    return masks


def _map_speakers(reference: list[dict], hypothesis: list[dict]) -> tuple[dict[str, str], Any]:
    import numpy as np

    ref_labels = sorted({str(t["speaker"]) for t in reference})
    hyp_labels = sorted({str(t["speaker"]) for t in hypothesis})
    overlap = np.zeros((len(ref_labels), len(hyp_labels)), dtype=float)
    for ref_turn in reference:
        for hyp_turn in hypothesis:
            shared = min(ref_turn["end"], hyp_turn["end"]) - max(ref_turn["start"], hyp_turn["start"])
            if shared > 0:
                overlap[ref_labels.index(str(ref_turn["speaker"])), hyp_labels.index(str(hyp_turn["speaker"]))] += shared

    mapping: dict[str, str] = {}
    if overlap.size:
        try:
            from scipy.optimize import linear_sum_assignment

            rows, cols = linear_sum_assignment(-overlap)
            mapping = {ref_labels[row]: hyp_labels[col] for row, col in zip(rows, cols)}
        except Exception:
            pairs = sorted(
                (
                    (overlap[i, j], ref_labels[i], hyp_labels[j])
                    for i in range(len(ref_labels))
                    for j in range(len(hyp_labels))
                ),
                reverse=True,
            )
            used_ref: set[str] = set()
            used_hyp: set[str] = set()
            for _, ref_label, hyp_label in pairs:
                if ref_label in used_ref or hyp_label in used_hyp:
                    continue
                mapping[ref_label] = hyp_label
                used_ref.add(ref_label)
                used_hyp.add(hyp_label)
    return mapping, (ref_labels, hyp_labels)


def diarization_metrics(
    reference: list[dict],
    hypothesis: list[dict],
    step: float = 0.01,
    collar: float = 0.25,
) -> dict:
    import numpy as np

    if not reference or not hypothesis:
        return {"der": None, "jer": None, "speaker_count_error": None, "note": "تعداد نوبت‌های مرجع یا فرضیه صفر است"}

    max_end = max(
        max(t["end"] for t in reference),
        max(t["end"] for t in hypothesis),
    )
    frames = max(1, int(math.ceil(max_end / step)))
    mapping, (ref_labels, hyp_labels) = _map_speakers(reference, hypothesis)
    ref_masks = _masks(reference, ref_labels, frames, step)
    hyp_masks = _masks(hypothesis, hyp_labels, frames, step)

    ignore = np.zeros(frames, dtype=bool)
    for turn in reference:
        for boundary in (turn["start"], turn["end"]):
            start = max(0, int(round((boundary - collar) / step)))
            end = min(frames, int(round((boundary + collar) / step)))
            if end > start:
                ignore[start:end] = True
    scorable = ~ignore

    ref_any = np.zeros(frames, dtype=bool)
    hyp_any = np.zeros(frames, dtype=bool)
    for mask in ref_masks.values():
        ref_any |= mask
    for mask in hyp_masks.values():
        hyp_any |= mask

    matched = np.zeros(frames, dtype=bool)
    for ref_label, hyp_label in mapping.items():
        matched |= ref_masks[ref_label] & hyp_masks[hyp_label]

    miss = ref_any & ~hyp_any
    false_alarm = ~ref_any & hyp_any
    confusion = ref_any & hyp_any & ~matched
    denominator = int((ref_any & scorable).sum())
    der = (
        float(((miss | false_alarm | confusion) & scorable).sum()) / denominator
        if denominator
        else None
    )

    jaccards: list[float] = []
    for ref_label in ref_labels:
        hyp_label = mapping.get(ref_label)
        ref_mask = ref_masks[ref_label] & scorable
        hyp_mask = (hyp_masks[hyp_label] if hyp_label else np.zeros(frames, dtype=bool)) & scorable
        union = int((ref_mask | hyp_mask).sum())
        if union:
            jaccards.append(1.0 - float((ref_mask & hyp_mask).sum()) / union)
    for hyp_label in hyp_labels:
        if hyp_label in mapping.values():
            continue
        hyp_mask = hyp_masks[hyp_label] & scorable
        union = int(hyp_mask.sum())
        if union:
            jaccards.append(1.0)

    return {
        "der": der,
        "jer": (sum(jaccards) / len(jaccards)) if jaccards else None,
        "speaker_count_error": len(hyp_labels) - len(ref_labels),
        "reference_speakers": ref_labels,
        "hypothesis_speakers": hyp_labels,
        "mapping": mapping,
        "scored_seconds": denominator * step,
    }


def extract_raw_text(path: Path) -> str:
    texts: list[str] = []
    pattern = re.compile(r"^\[[^\]]+\]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line.strip())
        if match:
            texts.append(match.group(1))
    return " ".join(texts)


def read_hypothesis_text(work_dir: Path, stem: str) -> tuple[str | None, Path | None]:
    candidates = [
        (work_dir / f"{stem}_transcript.json", "utterances"),
        (work_dir / f"{stem}.segments.json", "segments"),
        (work_dir / "01_raw_transcript.txt", "raw"),
        (work_dir / f"{stem}.txt", "raw"),
    ]
    for path, kind in candidates:
        if not path.exists():
            continue
        if kind == "raw":
            text = extract_raw_text(path)
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            text = " ".join(str(item.get("text", "")).strip() for item in payload.get(kind, []))
        if text.strip():
            return text, path
    return None, None


def read_truth_text(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return text or None


def summarize_events(timestamped_lines: list[tuple[float, str]]) -> tuple[list[dict], dict]:
    events: list[dict] = []
    stages: dict[str, dict] = {}
    summary: dict[str, Any] = {
        "artifactCount": 0,
        "done": None,
        "errors": [],
        "unparseable": 0,
        "stageSeconds": {},
        "artifactPaths": [],
    }
    for elapsed, line in timestamped_lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            summary["unparseable"] += 1
            continue
        event["_t"] = elapsed
        events.append(event)
        kind = event.get("type")
        if kind == "stage":
            stage = event.get("stage") or ""
            status = event.get("status")
            if status == "running" and stage not in stages:
                stages[stage] = {"start": event["_t"], "end": None}
            elif status == "done" and stage:
                if stage not in stages:
                    stages[stage] = {"start": 0.0, "end": None}
                stages[stage]["end"] = event["_t"]
        elif kind == "artifact":
            summary["artifactCount"] += 1
            summary["artifactPaths"].append(event.get("path"))
        elif kind == "done":
            summary["done"] = event
        elif kind == "error":
            summary["errors"].append(event)
    summary["stageSeconds"] = {
        stage: round(bounds["end"] - bounds["start"], 1)
        for stage, bounds in stages.items()
        if bounds["end"] is not None
    }
    return events, summary


def load_saved_engine(hypothesis_dir: Path, stem: str) -> dict:
    path = hypothesis_dir / f"{stem}.events.jsonl"
    if not path.exists():
        return {}
    try:
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError):
        return {}
    stages: dict[str, dict] = {}
    errors: list[dict] = []
    artifacts: list[str] = []
    done: dict | None = None
    last_t = 0.0
    for event in events:
        elapsed = float(event.get("_t") or 0.0)
        last_t = max(last_t, elapsed)
        kind = event.get("type")
        if kind == "stage":
            stage = event.get("stage") or ""
            if event.get("status") == "running" and stage not in stages:
                stages[stage] = {"start": elapsed, "end": None}
            elif event.get("status") == "done" and stage:
                stages.setdefault(stage, {"start": 0.0, "end": None})["end"] = elapsed
        elif kind == "artifact":
            artifacts.append(event.get("path"))
        elif kind == "error":
            errors.append(event)
        elif kind == "done":
            done = event
    stage_seconds = {
        stage: round(bounds["end"] - bounds["start"], 1)
        for stage, bounds in stages.items()
        if bounds["end"] is not None
    }
    return {
        "artifactCount": len(artifacts),
        "artifactPaths": artifacts,
        "done": done,
        "errors": errors,
        "stageSeconds": stage_seconds,
        "wallSeconds": round(last_t, 1) if last_t else None,
        "returnCode": 0 if done and not errors else (1 if errors else None),
        "stderrTail": "",
        "outDir": str(hypothesis_dir),
        "stem": stem,
    }


def run_engine(sample: dict, sample_paths: dict, args: argparse.Namespace, work_dir: Path) -> dict:
    stem = sample.get("stem") or sample["id"]
    out_dir = work_dir / sample["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    stderr_path = out_dir / f"{stem}.stderr.log"
    events_path = out_dir / f"{stem}.events.jsonl"

    job = {
        "jobId": f"bench-{sample['id']}",
        "audioPath": str(sample_paths["audio"].resolve()),
        "outputDirectory": str(out_dir.resolve()),
        "stem": stem,
        "title": sample.get("title") or sample["id"],
        "date": sample.get("date") or date.today().isoformat(),
        "numSpeakers": int(sample.get("speakers") or 0),
        "device": args.device,
        "computeType": args.compute_type,
        "language": sample.get("language") or args.language,
        "speakerMap": sample.get("speakerMap") or {},
        "ffmpegPath": args.ffmpeg,
        "beamSize": args.beam_size,
        "numThreads": args.num_threads,
        "speakerEmbedding": args.speaker_embedding,
    }
    if args.models_dir:
        job["modelsDir"] = args.models_dir

    started = time.monotonic()
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    with stderr_path.open("w", encoding="utf-8") as stderr_file:
        process = subprocess.Popen(
            [sys.executable, "-m", "minutemate", "run", "--job", "-"],
            cwd=str(ENGINE_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        assert process.stdin is not None
        try:
            process.stdin.write(json.dumps(job, ensure_ascii=False))
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        timestamped: list[tuple[float, str]] = []
        timer = threading.Timer(args.timeout, process.kill)
        timer.daemon = True
        timer.start()
        try:
            assert process.stdout is not None
            for line in process.stdout:
                timestamped.append((time.monotonic() - started, line))
            return_code = process.wait(timeout=args.timeout)
        finally:
            timer.cancel()
    wall_seconds = time.monotonic() - started

    events, summary = summarize_events(timestamped)
    events_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + ("\n" if events else ""),
        encoding="utf-8",
    )
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    summary["returnCode"] = return_code
    summary["wallSeconds"] = round(wall_seconds, 1)
    summary["stderrTail"] = "\n".join(stderr_text.splitlines()[-8:])
    summary["outDir"] = str(out_dir)
    summary["stem"] = stem
    return summary


def evaluate_sample(sample: dict, sample_paths: dict, hypothesis_dir: Path, metrics: dict) -> dict:
    stem = sample.get("stem") or sample["id"]
    truth_text = read_truth_text(sample_paths.get("truthText"))
    hyp_text, hyp_text_path = read_hypothesis_text(hypothesis_dir, stem)

    result: dict[str, Any] = {
        "id": sample["id"],
        "title": sample.get("title") or sample["id"],
        "condition": sample.get("condition", "unknown"),
        "truthStatus": sample.get("truthStatus", "missing"),
        "truthSource": sample.get("truthSource"),
        "durationSeconds": sample.get("durationSeconds"),
        "speakersRequested": sample.get("speakers"),
        "hypothesisTextPath": portable_path(hyp_text_path) if hyp_text_path else None,
        "warnings": [],
    }
    if not truth_text:
        result["warnings"].append("متن مرجع موجود نیست؛ WER/CER محاسبه نشد.")
    if not hyp_text:
        result["warnings"].append("متن فرضیه پیدا نشد؛ ابتدا موتور را اجرا کن یا --hyp-dir را درست بده.")
    if result["truthStatus"] == "draft":
        result["warnings"].append("متن مرجع «پیش‌نویس» است (ASR) و برای عدد رسمی باید توسط انسان اصلاح شود.")

    if truth_text and hyp_text:
        word_counts = edit_counts(tokenize(truth_text), tokenize(hyp_text))
        char_counts = edit_counts(list(normalize_chars(truth_text)), list(normalize_chars(hyp_text)))
        result["wordCounts"] = {
            "substitutions": word_counts.substitutions,
            "deletions": word_counts.deletions,
            "insertions": word_counts.insertions,
            "reference": word_counts.reference_length,
        }
        result["characterCounts"] = {
            "substitutions": char_counts.substitutions,
            "deletions": char_counts.deletions,
            "insertions": char_counts.insertions,
            "reference": char_counts.reference_length,
        }
        result["wer"] = word_counts.rate
        result["cer"] = char_counts.rate
        result["hypothesisPreview"] = hyp_text[:280]
        result["truthPreview"] = truth_text[:280]

    rttm_path = sample_paths.get("truthRttm")
    speakers_path = hypothesis_dir / f"{stem}.speakers.json"
    if rttm_path and rttm_path.exists() and speakers_path.exists():
        result["diarization"] = diarization_metrics(
            read_rttm(rttm_path),
            read_speaker_turns(speakers_path),
            step=metrics["step"],
            collar=metrics["collar"],
        )
    else:
        result["warnings"].append("RTTM مرجع یا speakers.json فرضیه موجود نیست؛ DER/JER محاسبه نشد.")

    engine = metrics.get("engine") or {}
    if not engine:
        engine = load_saved_engine(hypothesis_dir, stem)
    result["engine"] = {
        "wallSeconds": engine.get("wallSeconds"),
        "doneSeconds": (engine.get("done") or {}).get("durationSeconds"),
        "stageSeconds": engine.get("stageSeconds"),
        "returnCode": engine.get("returnCode"),
        "errors": engine.get("errors"),
        "stderrTail": engine.get("stderrTail"),
        "outDir": portable_path(engine.get("outDir")),
        "artifactCount": engine.get("artifactCount"),
    }
    duration = result.get("durationSeconds") or audio_duration(sample_paths["audio"])
    elapsed = result["engine"]["doneSeconds"] or result["engine"]["wallSeconds"]
    result["rtf"] = round(elapsed / duration, 3) if elapsed and duration else None
    return result


def _fmt_percent(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _fmt_number(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    meta = report["meta"]
    lines.append("# گزارش ارزیابی MinuteMate")
    lines.append("")
    lines.append(f"- تاریخ: `{meta['generatedAt']}`")
    lines.append(f"- نسخهٔ موتور: `{meta['engineVersion']}`")
    lines.append(f"- کامیت: `{meta['commit']}`")
    lines.append(f"- دستگاه/محاسبه: `{meta['device']}` / `{meta['computeType']}`")
    lines.append(f"- beam/threads: `{meta['beamSize']}` / `{meta['numThreads']}`")
    models = meta.get("models") or {}
    if models.get("whisper") or models.get("speaker"):
        lines.append(
            f"- مدل‌ها: whisper=`{', '.join(models.get('whisper', [])) or '—'}` · "
            f"speaker=`{', '.join(models.get('speaker', [])) or '—'}`"
        )
    lines.append(f"- نمونه‌ها: `{len(report['results'])}` (پیش‌نویس: `{meta['draftCount']}`)")
    lines.append("")
    if meta["draftCount"]:
        lines.append("> هشدار: نمونه‌های با مرجع «draft» عدد رسمی نیستند؛ ابتدا متن/برچسب گوینده را انسانی اصلاح کن.")
        lines.append("")
    lines.append("| نمونه | شرایط | مدت (ث) | مرجع | WER | CER | DER | JER | خطای تعداد گوینده | RTF | زمان (ث) |")
    lines.append("| :--- | :--- | ---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for item in report["results"]:
        diar = item.get("diarization") or {}
        lines.append(
            "| {id} | {condition} | {duration} | {truth} | {wer} | {cer} | {der} | {jer} | {spk} | {rtf} | {time} |".format(
                id=item["id"],
                condition=item.get("condition", "—"),
                duration=_fmt_number(item.get("durationSeconds")),
                truth=item.get("truthStatus", "—"),
                wer=_fmt_percent(item.get("wer")),
                cer=_fmt_percent(item.get("cer")),
                der=_fmt_percent(diar.get("der")),
                jer=_fmt_percent(diar.get("jer")),
                spk="—" if diar.get("speaker_count_error") is None else diar["speaker_count_error"],
                rtf=_fmt_number(item.get("rtf")),
                time=_fmt_number((item.get("engine") or {}).get("wallSeconds")),
            )
        )
    lines.append("")
    for item in report["results"]:
        lines.append(f"## {item['id']} — {item.get('title', '')}")
        lines.append("")
        lines.append(f"- شرایط: `{item.get('condition')}` · وضعیت مرجع: `{item.get('truthStatus')}`")
        if item.get("truthSource"):
            lines.append(f"- منبع مرجع: {item['truthSource']}")
        if item.get("wer") is not None:
            counts = item["wordCounts"]
            lines.append(
                f"- WER: **{_fmt_percent(item['wer'])}** "
                f"(S={counts['substitutions']}, D={counts['deletions']}, I={counts['insertions']}, N={counts['reference']})"
            )
            lines.append(f"- CER: **{_fmt_percent(item.get('cer'))}**")
        diar = item.get("diarization")
        if diar:
            lines.append(
                f"- DER: **{_fmt_percent(diar.get('der'))}** · JER: **{_fmt_percent(diar.get('jer'))}** "
                f"· گویندهٔ مرجع/فرضیه: {len(diar.get('reference_speakers', []))}/{len(diar.get('hypothesis_speakers', []))}"
            )
            lines.append(f"- نگاشت گویندگان: `{json.dumps(diar.get('mapping', {}), ensure_ascii=False)}`")
        engine = item.get("engine") or {}
        if engine.get("stageSeconds"):
            stages = " · ".join(f"{name}: {seconds}s" for name, seconds in engine["stageSeconds"].items())
            lines.append(f"- زمان مراحل: {stages}")
        if item.get("hypothesisPreview"):
            lines.append(f"- فرضیه (برش): {item['hypothesisPreview']}")
        if item.get("truthPreview"):
            lines.append(f"- مرجع (برش): {item['truthPreview']}")
        if engine.get("outDir"):
            lines.append(f"- خروجی: `{engine['outDir']}`")
        if engine.get("returnCode") not in (0, None):
            lines.append(f"- کد خروج موتور: `{engine['returnCode']}`")
        for warning in item.get("warnings", []):
            lines.append(f"- ⚠️ {warning}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _engine_version() -> str:
    try:
        text = (ENGINE_DIR / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        return match.group(1) if match else "unknown"
    except Exception:
        return "unknown"


def discover_models(models_dir: str | None) -> dict:
    base = Path(models_dir) if models_dir else Path(os.environ.get("MINUTEMATE_MODELS_DIR") or ROOT / "models")
    whisper_dir = base / "whisper"
    speaker_dir = base / "speaker"
    return {
        "modelsDir": portable_path(base),
        "whisper": sorted(path.name for path in whisper_dir.glob("*") if path.is_dir()) if whisper_dir.exists() else [],
        "speaker": sorted(path.name for path in speaker_dir.glob("*")) if speaker_dir.exists() else [],
    }


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def resolve_sample_paths(registry_path: Path, sample: dict) -> dict:
    base = registry_path.parent
    return {
        "audio": (base / sample["audio"]).resolve() if sample.get("audio") else None,
        "truthText": (base / sample["truthText"]).resolve() if sample.get("truthText") else None,
        "truthRttm": (base / sample["truthRttm"]).resolve() if sample.get("truthRttm") else None,
    }


def regression_findings(
    report: dict,
    baseline: dict,
    max_wer_delta: float = 0.01,
    max_der_delta: float = 0.01,
) -> list[dict]:
    previous = {item.get("id"): item for item in baseline.get("results", [])}
    findings: list[dict] = []
    for item in report.get("results", []):
        reference = previous.get(item.get("id"))
        if not reference:
            continue
        comparisons = [
            ("WER", item.get("wer"), reference.get("wer"), max_wer_delta),
            (
                "DER",
                (item.get("diarization") or {}).get("der"),
                (reference.get("diarization") or {}).get("der"),
                max_der_delta,
            ),
        ]
        for metric, current, before, limit in comparisons:
            if current is None or before is None:
                continue
            delta = current - before
            if delta > limit + 1e-9:
                findings.append(
                    {
                        "id": item.get("id"),
                        "metric": metric,
                        "baseline": before,
                        "current": current,
                        "delta": delta,
                        "limit": limit,
                    }
                )
    return findings


def render_regressions(findings: list[dict]) -> str:
    lines = ["رگرسیون نسبت به baseline:"]
    for finding in findings:
        lines.append(
            f"  {finding['id']} {finding['metric']}: "
            f"{finding['baseline'] * 100:.1f}% → {finding['current'] * 100:.1f}% "
            f"(+{finding['delta'] * 100:.1f} واحد، سقف {finding['limit'] * 100:.1f})"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--run-all", action="store_true", help="اجرای موتور روی همهٔ نمونه‌ها")
    parser.add_argument("--hyp-dir", type=Path, default=None, help="پوشهٔ خروجی‌های موجود برای ارزیابی بدون اجرا")
    parser.add_argument("--sample", action="append", default=[], help="فقط این شناسه‌ها (قابل تکرار)")
    parser.add_argument("--out", type=Path, default=None, help="مسیر گزارش .md یا .json")
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--device", default="cpu", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--beam-size", type=int, default=1)
    parser.add_argument("--num-threads", type=int, default=6)
    parser.add_argument(
        "--speaker-embedding",
        default="wespeaker",
        choices=["wespeaker", "3dspeaker"],
        help="مدل embedding دیاریزیشن برای A/B (M6.4)",
    )
    parser.add_argument("--language", default="fa")
    parser.add_argument("--models-dir", default=None)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--step", type=float, default=0.01, help="گام فریم برای DER (ثانیه)")
    parser.add_argument("--collar", type=float, default=0.25, help="حاشیهٔ نادیده‌گرفتن مرزها در DER (ثانیه)")
    parser.add_argument("--strict-truth", action="store_true", help="اگر مرجع human نباشد، خطا بده")
    parser.add_argument("--reuse", action="store_true", help="اگر خروجی موجود است، دوباره اجرا نکن")
    parser.add_argument("--baseline", type=Path, default=None, help="گزارش .json قبلی برای دروازهٔ رگرسیون")
    parser.add_argument("--max-wer-delta", type=float, default=0.01, help="حداکثر افت مجاز WER (نسبت، پیش‌فرض ۰٫۰۱)")
    parser.add_argument("--max-der-delta", type=float, default=0.01, help="حداکثر افت مجاز DER (نسبت، پیش‌فرض ۰٫۰۱)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry_path = args.registry.resolve()
    if not registry_path.exists():
        print(f"registry not found: {registry_path}", file=sys.stderr)
        return 2
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    samples = registry.get("samples", [])
    if args.sample:
        wanted = set(args.sample)
        samples = [sample for sample in samples if sample.get("id") in wanted]
    if not samples:
        print("no samples selected", file=sys.stderr)
        return 2
    if args.strict_truth:
        invalid = [sample["id"] for sample in samples if sample.get("truthStatus") != "human"]
        if invalid:
            print(f"strict-truth: samples without human truth: {', '.join(invalid)}", file=sys.stderr)
            return 2

    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    hypothesis_dir = args.hyp_dir.resolve() if args.hyp_dir else work_dir
    results: list[dict] = []

    for sample in samples:
        sample_paths = resolve_sample_paths(registry_path, sample)
        if not sample_paths["audio"] or not sample_paths["audio"].exists():
            results.append({"id": sample.get("id"), "warnings": ["فایل صوتی پیدا نشد"], "engine": {}})
            continue
        engine_summary: dict[str, Any] = {}
        sample_hyp_dir = hypothesis_dir
        try:
            if args.run_all:
                sample_hyp_dir = work_dir / sample["id"]
                stem = sample.get("stem") or sample["id"]
                out_dir = work_dir / sample["id"]
                expected = out_dir / f"{stem}_transcript.json"
                if not (args.reuse and expected.exists()):
                    print(f"running {sample['id']} ...", flush=True)
                    engine_summary = run_engine(sample, sample_paths, args, work_dir)
                else:
                    print(f"reusing {sample['id']}", flush=True)
            result = evaluate_sample(
                sample,
                sample_paths,
                sample_hyp_dir,
                {
                    "step": args.step,
                    "collar": args.collar,
                    "engine": engine_summary,
                },
            )
        except Exception as exc:
            result = {
                "id": sample.get("id"),
                "title": sample.get("title"),
                "condition": sample.get("condition"),
                "truthStatus": sample.get("truthStatus", "missing"),
                "warnings": [f"{type(exc).__name__}: {exc}"],
                "engine": engine_summary,
            }
        results.append(result)

    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")
    meta = {
        "generatedAt": generated_at,
        "engineVersion": _engine_version(),
        "commit": _git_commit(),
        "device": args.device,
        "computeType": args.compute_type,
        "beamSize": args.beam_size,
        "numThreads": args.num_threads,
        "draftCount": sum(1 for sample in samples if sample.get("truthStatus") == "draft"),
        "models": discover_models(args.models_dir),
    }
    report = {"meta": meta, "results": results}

    out_path = args.out
    if out_path is None:
        DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DEFAULT_REPORT_DIR / f"{date.today().isoformat()}-{args.device}-{args.compute_type}.md"
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path = out_path.with_suffix(".md") if out_path.suffix.lower() == ".json" else out_path
    json_path = out_path.with_suffix(".json")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"report: {markdown_path}")
    print(f"json:   {json_path}")
    for item in results:
        print(
            f"{item['id']}: WER={_fmt_percent(item.get('wer'))} "
            f"CER={_fmt_percent(item.get('cer'))} "
            f"DER={_fmt_percent((item.get('diarization') or {}).get('der'))} "
            f"RTF={_fmt_number(item.get('rtf'))}"
        )

    failed = [item for item in results if (item.get("engine") or {}).get("returnCode") not in (0, None)]
    if failed:
        return 1

    if args.baseline:
        baseline_path = args.baseline.resolve()
        if not baseline_path.exists():
            print(f"baseline not found: {baseline_path}", file=sys.stderr)
            return 2
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        findings = regression_findings(report, baseline, args.max_wer_delta, args.max_der_delta)
        if findings:
            print(render_regressions(findings), file=sys.stderr)
            return 3
        print("regression gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
