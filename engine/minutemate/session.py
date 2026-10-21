"""Session folder layout, manifest and data maintenance helpers."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from minutemate import __version__
from minutemate.errors import InputError

SCHEMA_VERSION = 1
_AGE = re.compile(r"^(\d+)\s*([hdwm])$")
_SLUG = re.compile(r"[^\w]+", re.UNICODE)
_AGE_UNITS = {"h": 3600, "d": 86400, "w": 604800, "m": 2592000}

INTERMEDIATE_SUFFIXES = (".wav", ".jsonl", ".srt")
INTERMEDIATE_MARKERS = ("_16k_mono", ".segments.", ".speakers.", "_transcript.json")
DELIVERABLE_PREFIXES = ("01_", "02_", "03_", "04_")
DELIVERABLE_SUFFIXES = (".minutes.json",)


@dataclass(frozen=True)
class SessionLayout:
    root: Path
    raw_dir: Path
    work_dir: Path
    out_dir: Path
    is_session: bool


def slugify(text: str, fallback: str = "session") -> str:
    value = _SLUG.sub("-", str(text or "").strip().lower()).strip("-")
    value = re.sub(r"-{2,}", "-", value)
    return value[:60] or fallback


def build_session_id(date_str: str, name: str) -> str:
    return f"{date_str}-{slugify(name)}"


def resolve_layout(
    *,
    session_dir: str | Path | None,
    sessions_root: str | Path | None,
    output_dir: str | Path | None,
    stem: str,
    title: str,
    date_str: str,
) -> SessionLayout:
    if session_dir:
        root = Path(session_dir).expanduser().resolve()
        return _session_layout(root)

    if sessions_root:
        base = Path(sessions_root).expanduser().resolve()
        session_id = build_session_id(date_str, title or stem)
        candidate = session_id
        suffix = 2
        while (base / candidate).exists():
            candidate = f"{session_id}-{suffix}"
            suffix += 1
        return _session_layout(base / candidate)

    base = Path(output_dir or "output").expanduser().resolve()
    return SessionLayout(root=base, raw_dir=base, work_dir=base, out_dir=base, is_session=False)


def _session_layout(root: Path) -> SessionLayout:
    return SessionLayout(
        root=root,
        raw_dir=root / "raw",
        work_dir=root / "work",
        out_dir=root / "out",
        is_session=True,
    )


def ensure_layout(layout: SessionLayout) -> SessionLayout:
    for directory in {layout.raw_dir, layout.work_dir, layout.out_dir}:
        directory.mkdir(parents=True, exist_ok=True)
    return layout


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(
    *,
    session_id: str,
    title: str,
    date_str: str,
    created_at: str | None = None,
    source: dict | None = None,
    run: dict | None = None,
    speakers: list | None = None,
    artifacts: list | None = None,
    tags: list | None = None,
    status: str = "raw",
    notes: str = "",
) -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "id": session_id,
        "title": title,
        "date": date_str,
        "createdAt": created_at or datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": source or {},
        "run": run or {},
        "speakers": speakers or [],
        "artifacts": artifacts or [],
        "tags": tags or [],
        "status": status,
        "notes": notes,
    }


def write_manifest(path: str | Path, manifest: dict) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)
    return target


def read_manifest(path: str | Path) -> dict | None:
    target = Path(path)
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise InputError(f"فایل manifest نامعتبر است: {target}", hint=str(error)) from error


def collect_artifacts(session_root: Path, paths: list[Path]) -> list[dict]:
    artifacts: list[dict] = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        try:
            rel = path.relative_to(session_root).as_posix()
        except ValueError:
            rel = path.name
        artifacts.append({"kind": path.name, "path": rel, "bytes": path.stat().st_size})
    return artifacts


def default_data_dir() -> Path:
    from minutemate.paths import resolve_data_dir

    return resolve_data_dir()


def sessions_root(data_dir: str | Path | None = None) -> Path:
    base = Path(data_dir).expanduser().resolve() if data_dir else default_data_dir()
    return base / "sessions"


def scan_sessions(root: str | Path) -> list[dict]:
    base = Path(root)
    if not base.exists():
        return []

    entries: list[dict] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        manifest = read_manifest(child / "session.json")
        if manifest:
            entries.append(
                {
                    "id": manifest.get("id") or child.name,
                    "title": manifest.get("title") or child.name,
                    "date": manifest.get("date") or "",
                    "status": manifest.get("status") or "unknown",
                    "durationSeconds": (manifest.get("source") or {}).get("durationSeconds"),
                    "numSpeakers": len(manifest.get("speakers") or []),
                    "artifacts": len(manifest.get("artifacts") or []),
                    "path": child.as_posix(),
                    "valid": True,
                }
            )
        else:
            entries.append(
                {
                    "id": child.name,
                    "title": child.name,
                    "date": "",
                    "status": "unknown",
                    "durationSeconds": None,
                    "numSpeakers": 0,
                    "artifacts": 0,
                    "path": child.as_posix(),
                    "valid": False,
                }
            )

    entries.sort(key=lambda item: (item["date"], item["id"]), reverse=True)
    return entries


def build_index(root: str | Path, sessions_root_path: str | Path) -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sessionsRoot": str(Path(sessions_root_path)),
        "sessions": scan_sessions(sessions_root_path),
    }


def write_index(data_dir: str | Path, sessions_root_path: str | Path) -> Path:
    index = build_index(data_dir, sessions_root_path)
    return write_manifest(Path(data_dir) / "index.json", index)


def parse_age(value: str) -> timedelta:
    match = _AGE.match(str(value or "").strip().lower())
    if not match:
        raise InputError("بازهٔ زمانی نامعتبر است.", hint="مثال: 30d, 12h, 8w, 2m")
    amount = int(match.group(1))
    return timedelta(seconds=amount * _AGE_UNITS[match.group(2)])


def prune_work(
    root: str | Path,
    older_than: timedelta,
    *,
    keep_transcripts: bool = False,
    dry_run: bool = False,
    now: datetime | None = None,
) -> list[Path]:
    base = Path(root)
    if not base.exists():
        return []

    cutoff = (now or datetime.now().astimezone()) - older_than
    targets: list[Path] = []

    for session_dir in sorted(base.iterdir()):
        work_dir = session_dir / "work"
        if not work_dir.is_dir():
            continue
        for file_path in sorted(work_dir.rglob("*")):
            if not file_path.is_file():
                continue
            if keep_transcripts and file_path.name.endswith("_transcript.json"):
                continue
            modified = datetime.fromtimestamp(file_path.stat().st_mtime, tz=cutoff.tzinfo)
            if modified < cutoff:
                targets.append(file_path)

    if not dry_run:
        for target in targets:
            target.unlink(missing_ok=True)

    return targets


def archive_session(root: str | Path, session_id: str, *, delete: bool = False) -> Path:
    base = Path(root)
    session_dir = base / session_id
    work_dir = session_dir / "work"
    if not work_dir.is_dir():
        raise InputError(f"پوشهٔ work برای جلسه پیدا نشد: {session_id}")

    files = [path for path in work_dir.rglob("*") if path.is_file()]
    if not files:
        raise InputError(f"جلسهٔ {session_id} فایل میانی برای فشرده‌سازی ندارد.")

    archive_path = session_dir / "work.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, path_relative(work_dir, file_path))

    if delete:
        shutil.rmtree(work_dir)

    return archive_path


def path_relative(base: Path, path: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.name


def classify_artifact(name: str) -> str:
    if name.startswith(DELIVERABLE_PREFIXES) or name.endswith(DELIVERABLE_SUFFIXES):
        return "out"
    if name.endswith(INTERMEDIATE_SUFFIXES) or any(marker in name for marker in INTERMEDIATE_MARKERS):
        return "work"
    return "out"


def adopt_flat_output(
    source_dir: str | Path,
    *,
    session_dir: str | Path,
    session_id: str,
    title: str,
    date_str: str,
    keep: bool = False,
) -> Path:
    source = Path(source_dir).expanduser().resolve()
    if not source.is_dir():
        raise InputError(f"پوشهٔ خروجی پیدا نشد: {source_dir}")

    layout = ensure_layout(_session_layout(Path(session_dir).expanduser().resolve()))

    for item in sorted(source.iterdir()):
        if not item.is_file():
            continue
        bucket = layout.work_dir if classify_artifact(item.name) == "work" else layout.out_dir
        destination = bucket / item.name
        if destination.exists():
            destination.unlink()
        if keep:
            shutil.copy2(item, destination)
        else:
            shutil.move(str(item), str(destination))

    artifacts = collect_artifacts(layout.root, sorted(layout.out_dir.glob("*")))
    manifest = build_manifest(
        session_id=session_id,
        title=title,
        date_str=date_str,
        artifacts=artifacts,
        status="minutes" if (layout.out_dir / "03_official_meeting_minutes.md").exists() else "transcribed",
        notes="مهاجرت‌شده از خروجی مسطح.",
    )
    write_manifest(layout.root / "session.json", manifest)
    return layout.root


def engine_version() -> str:
    return __version__
