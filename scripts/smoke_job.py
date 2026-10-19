"""End-to-end smoke test for the engine machine (NDJSON) mode.

Mirrors what the WPF app does: writes a job JSON document to the engine's
stdin and parses newline-delimited JSON events from stdout.

    python scripts/smoke_job.py path/to/audio.wav --num-speakers 2
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, help="path to a wav/mp3/m4a file")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--num-speakers", type=int, default=2)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "scratch" / "smoke")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument(
        "--speaker",
        action="append",
        default=[],
        metavar="ID=NAME[:ROLE]",
        help="assign a display name (and optional role) to a speaker id",
    )
    args = parser.parse_args()

    speaker_map: dict[str, dict[str, str]] = {}
    for entry in args.speaker:
        speaker_id, _, remainder = entry.partition("=")
        name, _, role = remainder.partition(":")
        profile: dict[str, str] = {"name": name}
        if role:
            profile["role"] = role
        speaker_map[speaker_id.strip()] = profile

    audio = args.audio.resolve()
    if not audio.exists():
        print(f"audio not found: {audio}", file=sys.stderr)
        return 2

    job = {
        "jobId": "smoke",
        "audioPath": str(audio),
        "outputDirectory": str(args.out_dir.resolve()),
        "stem": audio.stem,
        "title": "smoke test",
        "date": "2026-10-19",
        "numSpeakers": args.num_speakers,
        "device": args.device,
        "computeType": args.compute_type,
        "language": "fa",
        "speakerMap": speaker_map,
    }

    process = subprocess.Popen(
        [sys.executable, "-m", "minutemate", "run", "--job", "-"],
        cwd=str(ROOT / "engine"),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout, stderr = process.communicate(json.dumps(job, ensure_ascii=False), timeout=args.timeout)

    counts: dict[str, int] = {}
    artifacts: list[tuple[str, str]] = []
    failures = 0
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            failures += 1
            print(f"unparseable stdout line: {line[:160]}")
            continue
        counts[event["type"]] = counts.get(event["type"], 0) + 1
        if event["type"] == "artifact":
            artifacts.append((event.get("kind", ""), event.get("path", "")))

    print(f"exit code: {process.returncode}")
    print(f"events: {counts}")
    print(f"unparseable stdout lines: {failures}")
    for kind, path in artifacts:
        print(f"artifact {kind}: {path}")

    if process.returncode != 0 or failures or "done" not in counts:
        print("stderr tail:")
        print("\n".join(stderr.splitlines()[-15:]))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
