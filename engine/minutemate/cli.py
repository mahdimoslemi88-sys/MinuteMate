"""Command line interface for the MinuteMate engine."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from datetime import date
from pathlib import Path

from minutemate import __version__, pipeline, session
from minutemate.config import EngineConfig
from minutemate.errors import EngineError, InputError, StageError
from minutemate.events import EventType, JsonEventSink, TextEventSink
from minutemate.job import JobContext
from minutemate.logging_setup import configure_logging
from minutemate.models import registry
from minutemate.models.downloader import download_groups, format_progress
from minutemate.paths import resolve_data_dir, resolve_models_dir

def _load_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    candidates: list[Path] = []
    override = os.environ.get("MINUTEMATE_ENV_FILE")
    if override:
        candidates.append(Path(override))

    exe_dir = Path(sys.executable).resolve().parent
    candidates.append(exe_dir / ".env")
    candidates.append(exe_dir.parent / ".env")
    candidates.append(Path.cwd() / ".env")

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "MinuteMate" / ".env")

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            if candidate.is_file():
                load_dotenv(candidate, override=False)
        except OSError:
            pass


_load_env_files()


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("audio", nargs="?", help="مسیر فایل صوتی یا ویدیویی ورودی")
    parser.add_argument("--job", help="فایل job JSON یا - برای خواندن از stdin (حالت ماشین)")
    parser.add_argument("--out-dir", dest="out_dir", default="output")
    parser.add_argument("--session-dir", dest="session_dir", default=None)
    parser.add_argument("--sessions-root", dest="sessions_root", default=None)
    parser.add_argument("--stem", default="meeting")
    parser.add_argument("--title", default=None)
    parser.add_argument("--date", default=None)
    parser.add_argument("--speaker-map", dest="speaker_map", default=None)
    parser.add_argument("--num-speakers", dest="num_speakers", type=int, default=4)
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--compute-type", dest="compute_type", default="auto")
    parser.add_argument("--language", default="fa")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--models-dir", dest="models_dir", default=None)
    parser.add_argument("--beam-size", dest="beam_size", type=int, default=1)
    parser.add_argument("--batch-size", dest="batch_size", type=int, default=0,
                        help="batch رونویسی روی GPU (۰ = خاموش، پیشنهاد ۴ تا ۱۶)")
    parser.add_argument("--num-threads", dest="num_threads", type=int, default=6)
    parser.add_argument("--chunk-seconds", dest="chunk_seconds", type=float, default=1800.0,
                        help="طول چانک رونویسی برای جلسات طولانی (۰ = بدون بخش‌بندی)")
    parser.add_argument("--chunk-overlap", dest="chunk_overlap", type=float, default=5.0,
                        help="هم‌پوشانی چانک‌های رونویسی به ثانیه")
    parser.add_argument("--speaker-embedding", dest="speaker_embedding", default="wespeaker",
                        help="مدل embedding گوینده: wespeaker | 3dspeaker | مسیر .onnx")
    parser.add_argument("--asr-model", dest="asr_model", default="turbo",
                        choices=["turbo", "fa", "persian"], help="مدل رونویسی: turbo (سریع) | fa (دقت بالا، فارسی)")
    parser.add_argument("--asr-provider", dest="asr_provider", default="local",
                        choices=["local", "groq"], help="منبع رونویسی: local (faster-whisper) | groq (ابری)")
    parser.add_argument("--groq-model", dest="groq_model", default="whisper-large-v3-turbo",
                        help="مدل Groq هنگام --asr-provider groq")
    parser.add_argument("--parallel-stages", dest="parallel_stages", default="auto",
                        choices=["auto", "on", "off"], help="اجرای موازی دیاریزیشن و رونویسی")
    parser.add_argument("--log-level", dest="log_level", default="INFO")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="minutemate",
        description="موتور MinuteMate: رونویسی فارسی، تفکیک گویندگان و صورت‌جلسه.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="اجرای خط لوله روی یک فایل صوتی")
    _add_run_arguments(run_parser)

    models_parser = sub.add_parser("models", help="مدیریت مدل‌ها")
    models_sub = models_parser.add_subparsers(dest="models_command")
    models_sub.add_parser("list", help="نمایش مدل‌های تعریف‌شده")
    verify_parser = models_sub.add_parser("verify", help="بررسی وجود و صحت مدل‌ها")
    verify_parser.add_argument("--models-dir", dest="models_dir", default=None)
    download_parser = models_sub.add_parser("download", help="دانلود مدل‌ها")
    download_parser.add_argument("--models-dir", dest="models_dir", default=None)
    download_parser.add_argument("--group", "--type", dest="group", default="all",
                                 choices=["all", "diarization", "whisper", "whisper-fa"])
    download_parser.add_argument("--force", action="store_true")

    preflight_parser = sub.add_parser("preflight", help="بررسی پیش‌نیازها")
    preflight_parser.add_argument("--models-dir", dest="models_dir", default=None)
    preflight_parser.add_argument("--ffmpeg", default="ffmpeg")
    preflight_parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    preflight_parser.add_argument("--compute-type", dest="compute_type", default="auto")

    data_parser = sub.add_parser("data", help="مدیریت داده و جلسه‌ها")
    data_sub = data_parser.add_subparsers(dest="data_command")

    data_list = data_sub.add_parser("list", help="فهرست جلسه‌ها و بازسازی index")
    data_list.add_argument("--root", default=None, help="ریشهٔ داده (پیش‌فرض: data/)")

    data_index = data_sub.add_parser("index", help="ساخت/بازسازی data/index.json")
    data_index.add_argument("--root", default=None)

    data_prune = data_sub.add_parser("prune", help="حذف فایل‌های میانی قدیمی")
    data_prune.add_argument("--older-than", dest="older_than", default="90d")
    data_prune.add_argument("--target", default="work", choices=["work"])
    data_prune.add_argument("--keep-transcripts", dest="keep_transcripts", action="store_true")
    data_prune.add_argument("--root", default=None)
    data_prune.add_argument("--dry-run", dest="dry_run", action="store_true")

    data_archive = data_sub.add_parser("archive", help="فشرده‌سازی work/ یک جلسه")
    data_archive.add_argument("--session", dest="session_id", required=True)
    data_archive.add_argument("--delete", action="store_true")
    data_archive.add_argument("--root", default=None)

    data_adopt = data_sub.add_parser("adopt", help="مهاجرت خروجی مسطح به ساختار جلسه")
    data_adopt.add_argument("source", help="پوشهٔ خروجی مسطح")
    data_adopt.add_argument("--id", dest="session_id", required=True)
    data_adopt.add_argument("--title", default=None)
    data_adopt.add_argument("--date", default=None)
    data_adopt.add_argument("--root", default=None)
    data_adopt.add_argument("--keep", action="store_true", help="کپی به‌جای انتقال")

    return parser


def _load_speaker_map(path: str | None) -> dict[int, dict]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        raise InputError(f"فایل نگاشت گویندگان پیدا نشد: {path}")
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return {int(key): value for key, value in payload.items()}


def _config_from_args(args: argparse.Namespace) -> EngineConfig:
    if not args.audio:
        raise InputError("مسیر فایل ورودی مشخص نشده است.")
    return EngineConfig(
        audio_path=args.audio,
        output_dir=args.out_dir,
        stem=args.stem,
        title=args.title,
        date=args.date,
        num_speakers=args.num_speakers,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        ffmpeg_bin=args.ffmpeg,
        models_dir=args.models_dir,
        beam_size=args.beam_size,
        batch_size=args.batch_size,
        asr_chunk_seconds=args.chunk_seconds,
        asr_chunk_overlap_seconds=args.chunk_overlap,
        speaker_embedding=args.speaker_embedding,
        asr_model=args.asr_model,
        asr_provider=args.asr_provider,
        groq_model=args.groq_model,
        parallel_stages=args.parallel_stages,
        num_threads=args.num_threads,
        speaker_map=_load_speaker_map(args.speaker_map),
        session_dir=args.session_dir,
        sessions_root=args.sessions_root,
    )


def _read_job(path: str) -> dict:
    if path == "-":
        buffer = getattr(sys.stdin, "buffer", None)
        raw = (
            buffer.read().decode("utf-8", errors="replace")
            if buffer is not None
            else sys.stdin.read()
        )
    else:
        job_path = Path(path)
        if not job_path.exists():
            raise InputError(f"فایل job پیدا نشد: {path}")
        raw = job_path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InputError("job JSON نامعتبر است.", hint=str(exc)) from exc


def _run_machine(args: argparse.Namespace) -> int:
    real_stdout = sys.stdout
    sys.stdout = sys.stderr
    configure_logging(args.log_level)
    sink = JsonEventSink(real_stdout)

    try:
        config = EngineConfig.from_payload(_read_job(args.job))
    except EngineError as error:
        sink.emit(_error_event(error))
        return 2

    ctx = JobContext(config, sink)
    _install_signal_handlers(ctx)
    try:
        pipeline.run(config, ctx)
        return 0
    except EngineError as error:
        ctx.fail(error)
        return 2 if error.code == "input_error" else 1
    except KeyboardInterrupt:
        ctx.cancel()
        return 130
    except Exception as error:
        ctx.fail(StageError(f"خطای پیش‌بینی‌نشده در موتور: {error}"))
        return 1


def _error_event(error: EngineError):
    from minutemate.errors import to_payload
    from minutemate.events import EngineEvent

    payload = to_payload(error)
    return EngineEvent(
        type=EventType.ERROR,
        code=payload["code"],
        message=payload["message"],
        hint=payload.get("hint"),
    )


def _run_human(args: argparse.Namespace) -> int:
    configure_logging(args.log_level)
    sink = TextEventSink()
    config = _config_from_args(args)
    ctx = JobContext(config, sink)
    _install_signal_handlers(ctx)
    try:
        result = pipeline.run(config, ctx)
        sys.stderr.write(f"خروجی در: {result['outputDir']}\n")
        return 0
    except EngineError as error:
        ctx.fail(error)
        return 1
    except KeyboardInterrupt:
        ctx.cancel()
        return 130


def _install_signal_handlers(ctx: JobContext) -> None:
    def handler(signum, frame):
        ctx.cancel()

    try:
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
    except (ValueError, AttributeError):
        pass


def _models_command(args: argparse.Namespace) -> int:
    if args.models_command == "list":
        for group in registry.GROUPS:
            print(f"{group.id} ({group.size_hint}): {group.title}")
            for model_file in group.files:
                print(f"  - {model_file.rel_path}")
        return 0

    if args.models_command == "verify":
        models_dir = resolve_models_dir(args.models_dir)
        required = registry.required_group_ids("turbo")
        missing = registry.verify(args.models_dir, required)
        optional = registry.verify(args.models_dir, [registry.WHISPER_FA.id])
        print(f"models dir: {models_dir}")
        if missing:
            print(f"missing: {len(missing)}")
            for item in missing:
                print(f"  - {item}")
            return 1
        print("required models present (turbo + diarization)")
        if optional:
            print(f"optional persian model missing: {len(optional)} file(s) — فقط برای حالت «دقت بالا» لازم است")
        return 0

    if args.models_command == "download":
        group_ids = None if args.group == "all" else [args.group]

        def on_progress(rel_path: str, downloaded: int, total: int) -> None:
            sys.stderr.write("\r" + format_progress(rel_path, downloaded, total))
            sys.stderr.flush()

        download_groups(
            group_ids=group_ids,
            models_dir=args.models_dir,
            force=args.force,
            progress=on_progress,
            log=lambda message: sys.stderr.write(message + "\n"),
        )
        sys.stderr.write("\n")
        return 0

    _build_parser().print_help()
    return 2


def _data_command(args: argparse.Namespace) -> int:
    data_dir = resolve_data_dir(args.root)
    root = session.sessions_root(data_dir)

    if args.data_command == "list":
        entries = session.scan_sessions(root)
        session.write_index(data_dir, root)
        if not entries:
            print(f"هیچ جلسه‌ای در {root} یافت نشد.")
            return 0
        for entry in entries:
            flag = "" if entry["valid"] else "  (بدون session.json)"
            duration = entry["durationSeconds"] or 0
            print(
                f"{entry['date'] or '-':10}  {entry['id']:30}  {entry['status']:11}  "
                f"{int(duration) // 60:>4}د  {entry['numSpeakers']} گوینده  {flag}"
            )
        print(f"{len(entries)} جلسه در {root}")
        return 0

    if args.data_command == "index":
        path = session.write_index(data_dir, root)
        print(f"index: {path}")
        return 0

    if args.data_command == "prune":
        if args.target != "work":
            raise InputError("فقط --target work پشتیبانی می‌شود.")
        older_than = session.parse_age(args.older_than)
        removed = session.prune_work(
            root,
            older_than,
            keep_transcripts=args.keep_transcripts,
            dry_run=args.dry_run,
        )
        verb = "قابل حذف" if args.dry_run else "حذف شد"
        for path in removed:
            print(f"{verb}: {path}")
        print(f"{len(removed)} فایل {verb}.")
        return 0

    if args.data_command == "archive":
        path = session.archive_session(root, args.session_id, delete=args.delete)
        print(f"آرشیو: {path}")
        return 0

    if args.data_command == "adopt":
        destination = session.adopt_flat_output(
            args.source,
            session_dir=root / args.session_id,
            session_id=args.session_id,
            title=args.title or args.session_id,
            date_str=args.date or date.today().isoformat(),
            keep=args.keep,
        )
        print(f"جلسه ساخته شد: {destination}")
        return 0

    _build_parser().print_help()
    return 2


def _configure_console() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            continue


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and not argv[0].startswith("-") and argv[0] not in {"run", "models", "preflight", "data"}:
        argv = ["run"] + argv

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "models":
        return _models_command(args)

    if args.command == "data":
        return _data_command(args)

    if args.command == "preflight":
        configure_logging("INFO")
        config = EngineConfig(
            audio_path=".",
            output_dir=".",
            ffmpeg_bin=args.ffmpeg,
            device=args.device,
            compute_type=args.compute_type,
            models_dir=args.models_dir,
        )
        report = pipeline.preflight(config)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["modelsReady"] and report["ffmpeg"] else 1

    if args.command == "run":
        if args.job:
            return _run_machine(args)
        return _run_human(args)

    parser.print_help()
    return 2
