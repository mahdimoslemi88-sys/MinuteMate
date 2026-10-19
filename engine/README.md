# MinuteMate Engine

Python engine for Persian speech recognition, speaker diarization and meeting minutes generation.

## Run

```bash
python -m minutemate preflight
python -m minutemate run path/to/meeting.mp3 --out-dir output --stem meeting --num-speakers 4
```

## Machine mode (used by the desktop UI)

```bash
python -m minutemate run --job -      # job JSON on stdin, NDJSON events on stdout
python -m minutemate models verify
```

Models are resolved from `--models-dir`, then `MINUTEMATE_MODELS_DIR`, then `<repo>/models`.
