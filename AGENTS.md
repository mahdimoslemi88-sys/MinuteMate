# MinuteMate — راهنمای عامل‌ها (AGENTS.md)

موتور هوش مصنوعی فارسی برای رونویسی جلسات، تفکیک گویندگان و تولید صورت‌جلسه؛ به‌همراه یک اپ دسکتاپ WPF که موتور را به‌صورت sidecar اجرا می‌کند.

> ریپوی خواهر `../meeting-text` فقط **مرجع خواندنی** است (پایپ‌لاین قدیمی + مدل‌ها + نمونه صدا). هیچ تغییری داخل آن نده.

---

## ۱. ساختار پروژه

```
Minute-mate/
├── engine/                          # موتور پایتونی (بستهٔ minutemate)
│   ├── minutemate/                  # errors, events, config, job, pipeline, cli
│   │   ├── audio/                   # ffmpeg + wav
│   │   ├── asr/whisper.py           # faster-whisper
│   │   ├── diarization/             # segmenter / embedder / cluster
│   │   ├── merge/align.py           # ادغام واژه‌ها و گویندگان
│   │   ├── models/                  # registry + downloader
│   │   └── text/                    # normalize + renderers
│   ├── tests/                       # pytest
│   └── pyproject.toml               # entry point: `minutemate`
├── desktop/                         # WPF (.NET 8) — UI + sidecar runner
│   └── src/MinuteMate.{App,Core,EngineClient}
├── models/                          # junction → ../meeting-text/models (git ندارد)
├── data/                            # دادهٔ جلسات/بنچمارک/خروجی (محتوای حجیم در git نیست)
├── docs/                            # مستندات پروژه (منبع حقیقت)
│   ├── 01-architecture/ … 06-product/
│   └── README.md                    # فهرست مستندات + قواعد نوشتن
├── scripts/smoke_job.py             # تست دود انتها-به-انتها در حالت NDJSON
├── README.md                        # شروع سریع و مرجع CLI
├── ROADMAP.md                       # نقشهٔ راه مرحله‌به‌مرحله
├── .agents/skills/                  # مهارت‌های عامل‌ها
├── .opencode/plugins/               # هوک‌های opencode
└── opencode.json                    # کانفیگ opencode (skills/permission/instructions)
```

---

## ۲. دستورات کلیدی

```powershell
# موتور (از پوشه engine یا با PYTHONPATH)
python -m minutemate models verify                       # مدل‌های موجود و مسیرشان
python -m minutemate preflight --device cpu --compute-type int8
python -m minutemate run .\audio.mp3 --out-dir output --stem session --num-speakers 4 `
       --speaker-map speaker_map.json --device cuda --compute-type float16
python -m minutemate run --job -                          # حالت ماشین: job JSON روی stdin، رویداد NDJSON روی stdout

# تست
python -m pytest -q                                      # از پوشه engine
python scripts\smoke_job.py scratch\sample30.wav --num-speakers 2 --speaker "0=مهدی:سرپرست"

# دسکتاپ
dotnet build desktop\MinuteMate.Desktop.sln
dotnet test  desktop\MinuteMate.Desktop.sln
```

مدل‌ها به این ترتیب پیدا می‌شوند: `--models-dir` → `MINUTEMATE_MODELS_DIR` → `models/` کنار پروژه (junction به مدل‌های ریپوی قدیمی). **مدل جدید دانلود نکن.**

---

## ۳. قرارداد موتور ↔ دسکتاپ

- ورودی: یک job JSON (کلیدها camelCase): `audioPath, outputDirectory, stem, title, date, numSpeakers, device, computeType, language, speakerMap, ffmpegPath, modelsDir`.
- خروجی: NDJSON روی **stdout** (`started | stage | log | artifact | error | done`)، همهٔ لاگ‌ها روی **stderr**.
- تغییر `engine/minutemate/events.py` یا `config.py` ⟹ هم‌زمان `desktop/src/MinuteMate.Core/Contracts/*.cs` را به‌روز کن (و برعکس).
- خروجی‌های نهایی: `01_raw_transcript.txt`، `02_diarized_cleaned_transcript.{txt,md}`، به‌علاوه `*.segments.json`، `*.speakers.json`، `*.srt`.
- UTF-8 در ويندوز اجباری است (stdin/stdout/stderr و همهٔ فایل‌ها).

---

## ۴. مهارت‌ها (`.agents/skills/`)

| مهارت | چه زمانی |
| :--- | :--- |
| `persian-meeting-minutes` | «صورت‌جلسه بنویس» — تبدیل `02_diarized_cleaned_transcript.md` به صورت‌جلسهٔ رسمی مدیریتی (`03_official_meeting_minutes.md`). |
| `diarization-speaker-mapper` | «گوینده‌ها را پیدا کن» — استخراج سرنخ‌ها و ساخت `speaker_map.json`. |
| `meeting-action-tracker` | «اکشن‌آیتم‌ها / RACI / کارت Jira» — استخراج اقدامات SMART و ماتریس مسئولیت. |

## ۵. هوک‌ها (`.opencode/plugins/`)

| هوک | کار |
| :--- | :--- |
| `guard-legacy.js` | جلوی edit/write و دستورهای مخرب روی `../meeting-text` را می‌گیرد (خواندن آزاد است). |
| `contract-sync.js` | با تغییر فایل‌های قرارداد موتور یا C#، هشدار سینک می‌دهد. |
| `smoke-gate.js` | بعد از ویرایش ماژول‌های موتور، `scripts/smoke_job.py` را در پس‌زمینه اجرا و نتیجه را اعلام می‌کند (`MINUTEMATE_SMOKE=0` خاموشش می‌کند). |
| `dotnet-after-edit.js` | بعد از ویرایش هر `*.cs`، سولوشن را build می‌کند و خطاهای کامپایل را به نتیجهٔ ابزار می‌چسباند (`MINUTEMATE_DOTNET=0` خاموشش می‌کند). |

---

## ۶. قواعد کار

1. همهٔ تغییرات داخل `Minute-mate`؛ ریپوی `meeting-text` مرجع خواندنی است.
2. قبل از اعلام پایان کار: `python -m pytest -q` + یک اجرای کوتاه `scripts/smoke_job.py` + `dotnet build` (اگر C# دست خورده).
3. فایل‌های حجیم (`models/`, `data/`, `scratch/`, `output/`, صدا/ویدیو) هرگز کامیت نشوند.
4. کد پایتون بدون کامنت اضافه؛ نام‌گذاری موجود موتور را نگه دار.
5. هر تغییر رفتاری موتور باید یا تست واحد داشته باشد یا در `scripts/smoke_job.py` دیده شود.
6. **هر تغییر رفتاری، سند خودش را هم به‌روز می‌کند:** قراردادها ⇒ `docs/02-contracts/`، عملیات ⇒ `docs/03-operations/`، داده ⇒ `docs/04-data/`، و اگر قابلیتی اضافه/تمام شد ⇒ `README.md` + `ROADMAP.md` + `docs/06-product/features.md`.
