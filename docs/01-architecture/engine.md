# معماری موتور (Engine)

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال | 1405-07-27 | Engine |

بستهٔ پایتونی `minutemate` در `engine/`، با نقطهٔ ورود `minutemate.cli:main` (`python -m minutemate`).

## ۱. نقشهٔ ماژول‌ها

| مسیر | مسئولیت |
| :--- | :--- |
| `minutemate/__main__.py` | اجرای `main()` هنگام `python -m minutemate` |
| `minutemate/cli.py` | پارس آرگومان‌ها، حالت انسانی و حالت ماشین، نصب signal handler، `models`/`preflight` |
| `minutemate/config.py` | `EngineConfig` + `from_payload` (نگاشت camelCase) + حل دستگاه/نوع محاسبه |
| `minutemate/job.py` | `JobContext`: لغو، پیشرفت throttle‌شده، رویدادهای stage/artifact/log/done/fail |
| `minutemate/events.py` | مدل `EngineEvent`، ثابت‌های `EventType`/`Stage`/`Status`، `JsonEventSink`/`TextEventSink`/`NullEventSink` |
| `minutemate/errors.py` | خطاهای تایپ‌دار (`InputError`, `ModelMissingError`, `FfmpegError`, `CudaUnavailableError`, `CancelledError`, `StageError`) + `to_payload` |
| `minutemate/pipeline.py` | ارکستریشن `preflight()` و `run()` (پنج مرحله) |
| `minutemate/paths.py` | حل ریشهٔ پروژه/مدل‌ها (`resolve_models_dir`)، ساخت پوشه |
| `minutemate/env.py` | تشخیص تعداد GPU و `setup_windows_cuda()` (افزودن مسیر DLLهای CUDA) |
| `minutemate/logging_setup.py` | لاگ روی stderr (هرگز stdout در حالت ماشین) |
| `audio/ffmpeg.py` | `ensure_ffmpeg`, `probe`, `preprocess` (پیشرفت با `-progress pipe:1`, drain کردن stderr, لغو) |
| `audio/wav.py` | خواندن/نوشتن WAV و کمکی‌های نمونه‌برداری |
| `asr/whisper.py` | `faster-whisper`, word timestamps، نوشتن `segments.json/jsonl/txt/srt`، پیشرفت از روی `end/duration` |
| `diarization/segmenter.py` | پیوند segmentation + embedding + خوشه‌بندی؛ تخمین خودکار K؛ خروجی `speakers.json/txt` |
| `diarization/embedder.py` | استخراج امبدینگ With sherpa-onnx (CPU/GPU) |
| `diarization/cluster.py` | خوشه‌بندی (silhouette برای انتخاب K) |
| `merge/align.py` | تخصیص گوینده به هر واژه/جمله با بیشترین هم‌پوشانی + ادغام جملات پیوستهٔ یک گوینده |
| `text/normalize.py` | نیم‌فاصله، واژه‌نامهٔ تخصصی، حذف حشو |
| `text/renderers.py` | تولید `01_raw_transcript.txt` و `02_diarized_cleaned_transcript.{txt,md}` |
| `text/resources`/`resources/glossary_fa.json` | واژه‌نامهٔ قابل‌ویرایش |
| `models/registry.py` | فهرست مدل‌ها (مسیر نسبی، لینک، حداقل حجم) + `resolve`/`verify` |
| `models/downloader.py` | دانلود با پیشرفت، استخراج آرشیو (tar.bz2)، بازبینی حجم |

## ۲. مراحل اجرا

| مرحله (`stage`) | کاری که انجام می‌دهد | خروجی میانی | لغوپذیر |
| :--- | :--- | :--- | :---: |
| `preprocess` | FFmpeg: `16kHz mono` + `loudnorm` | `<stem>_16k_mono.wav` | ✅ |
| `diarization` | segmentation + embedding + خوشه‌بندی | `<stem>.speakers.json/.txt` | ✅ (بین بلوک‌ها) |
| `transcription` | Whisper با word timestamps | `<stem>.segments.json/.jsonl/.txt/.srt` | ✅ (per segment) |
| `merge` | تخصیص گوینده + چسباندن جملات | حافظه (`utterances`) | — |
| `export` | رندر فارسی و نوشتن گزارش‌ها + رویداد `artifact` | `01_…`, `02_…` | — |
| `minutes` | تولید صورت‌جلسه با LLM | `03_…`, `04_…` | ⏳ M3 |

## ۳. الگوهای پیاده‌سازی

- **لغو (cancellation):** `JobContext.cancelled` (رویداد) در حلقه‌های طولانی بررسی و `CancelledError` پرتاب می‌شود؛ handler سیگنال روی SIGINT/SIGTERM همان را ست می‌کند.
- **پیشرفت:** هر مرحله `stage_progress(stage, fraction, eta=…)` با throttle (کاهش نویز) و امکان `force=True` برای ۰٪ و ۱۰۰٪.
- **خطا:** فقط `EngineError` به رویداد `error` با `code`/`hint` نگاشت می‌شود؛ استثناهای غیرمنتظره به `internal_error` تبدیل و با traceback در stderr لاگ می‌شوند.
- **ادغام دوباره (idempotency):** اگر `_16k_mono.wav` معتبر باشد، مرحلهٔ پیش‌پردازش رد می‌شود.
- **UTF-8:** در `cli._configure_console()` هر سه جریان `stdin/stdout/stderr` روی UTF-8 تنظیم و job از `stdin.buffer` با UTF-8 خوانده می‌شود.

## ۴. پیکربندی و حل مسیر مدل

```
--models-dir  →  MINUTEMATE_MODELS_DIR  →  <project_root>/models
```

`resolve_models_dir` ریشهٔ پروژه را با جست‌وجوی `pyproject.toml` به بالا پیدا می‌کند؛ `models/` می‌تواند junction باشد.

## ۵. وابستگی‌ها

`faster-whisper`, `ctranslate2`, `sherpa-onnx`, `onnxruntime`, `numpy`, `scipy` (+ اختیاری `gpu`: `nvidia-cublas-cu12`, `nvidia-cuda-nvrtc-cu12`). نصب: `pip install -r engine/requirements.txt` یا `pip install -e engine[gpu]`.

## ۶. تست‌ها

`engine/tests/`: `test_events.py` (قرارداد رویداد)، `test_merge.py` (تخصیص گوینده)، `test_normalize.py` (پالایش فارسی)، `test_registry.py` (مسیر/بازبینی مدل). اجرا: `python -m pytest -q` از پوشهٔ `engine`.
