# MinuteMate

**موتور هوش مصنوعی فارسی برای رونویسی جلسات، تفکیک گویندگان و تولید صورت‌جلسهٔ مدیریتی** — به‌همراه یک اپلیکیشن دسکتاپ ویندوز که موتور را به‌صورت sidecar اجرا می‌کند.

```
صدا/ویدیوی جلسه ──▶ FFmpeg ──▶ تفکیک گویندگان ──▶ رونویسی Whisper ──▶ ادغام ──▶ خروجی‌ها
                  16kHz mono   (PyAnnote 3.0)     (large-v3-turbo)              (متن + صورت‌جلسه)
```

---

## ۱. وضعیت پروژه

| مؤلفه | وضعیت | توضیح |
| :--- | :---: | :--- |
| موتور پایتونی (`engine/`) | ✅ آماده | ۶ مرحله (تا صورت‌جلسه)، تست‌شده روی CPU (`int8`) |
| پروتکل ماشین (job JSON + NDJSON) | ✅ آماده | stdout فقط رویداد، stderr فقط لاگ |
| مدل‌ها | ✅ آماده | از پوشهٔ `models/` (junction به مدل‌های موجود) خوانده می‌شوند |
| لایهٔ داده و جلسه‌ها | ✅ آماده | `raw/work/out` + `session.json` + `data list/prune/archive/adopt` |
| دسکتاپ (`desktop/`) | ✅ MVP | اجرا/لغو/پیشرفت، تاریخچه و جست‌وجو، تنظیمات، پیش‌بررسی، باز کردن خروجی |
| تولید صورت‌جلسه با LLM | ✅ M3a | مرحلهٔ موتور + مهارت‌های `.agents/skills/` |
| بسته‌بندی و نصب‌کننده | ✅ آماده | `dist\MinuteMate-Setup-0.1.0.exe` (~۳۲۲ MB؛ بدون مدل/CUDA، per-user، انتخاب و دانلود مدل در صفحهٔ نصب، همراه `.env` خام) |

نقشه‌راه کامل و راهنمای انتقال کار: [`ROADMAP.md`](./ROADMAP.md) · گزارش مستقل برای مشورت: [`docs/REVIEW-ROADMAP.md`](./docs/REVIEW-ROADMAP.md) · مستندات: [`docs/`](./docs/README.md)

---

## ۲. قابلیت‌ها

- **پیش‌پردازش صوتی:** تبدیل به 16kHz mono با فیلتر `highpass=f=60` (بدون تغییر بلندی)، با نمایش پیشرفت واقعی و امکان لغو.
- **تفکیک گویندگان (Diarization):** PyAnnote segmentation 3.0 + امبدینگ WeSpeaker / 3D-Speaker روی ONNX Runtime، با تخمین خودکار تعداد گویندگان.
- **رونویسی فارسی (ASR):** `faster-whisper-large-v3-turbo` با word-level timestamps؛ حالت اختیاری «دقت بالا» با مدل فارسی `large-v3-persian-ct2-int8` (`--asr-model fa`).
- **رونویسی ابری (اختیاری):** پرووایدر Groq (`--asr-provider`/`asrProvider=groq`) با چانک‌بندی ۳۰ ثانیه‌ای و چند کلید؛ مناسب صداهای کم‌باند که مدل محلی روی آن‌ها ضعیف است.
- **ادغام هوشمند:** تخصیص گوینده به هر جمله بر اساس بیشترین هم‌پوشانی زمانی واژه‌ها.
- **پالایش متن فارسی:** نیم‌فاصله، اصلاح واژگان تخصصی از واژه‌نامهٔ قابل‌ویرایش، حذف حشوها.
- **خروجی‌های آمادهٔ استفاده:** رونویسی خام، رونویسی گوینده‌محور (txt/md)، زیرنویس SRT و JSON ماشین‌خوان.
- **نگاشت گویندگان:** تبدیل «گوینده ۱» به نام و سمت واقعی از طریق `speaker_map.json`.
- **حالت ماشین (Machine mode):** پروتکل خط‌محور NDJSON برای مصرف اپ دسکتاپ یا هر ابزار دیگر.
- **اجرای مقاوم:** پیش‌بررسی مدل‌ها/FFmpeg/دستگاه، خطاهای تایپ‌دار با کد و راهنما، لغو ایمن، و ادغام دوبارهٔ امن (idempotent).

---

## ۳. پیش‌نیازها

| مورد | نسخهٔ پیشنهادی | چرا |
| :--- | :--- | :--- |
| Python | 3.10+ (تست‌شده روی 3.14) | موتور |
| FFmpeg | 6+ روی `PATH` | پیش‌پردازش و پروب صدا |
| .NET SDK | 8.0 | اپ دسکتاپ |
| GPU (اختیاری) | CUDA 12 + cuDNN | سرعت رونویسی؛ روی CPU هم کار می‌کند |
| فضای دیسک | ~2 GB | مدل‌ها (`models/`) |

---

## ۴. شروع سریع

### ۴.۱ موتور

```powershell
# ۱) نصب وابستگی‌ها (یک‌بار)
python -m pip install -r engine\requirements.txt

# ۲) بررسی پیش‌نیازها (مدل‌ها، FFmpeg، دستگاه)
python -m minutemate preflight --device auto

# ۳) اجرا (از پوشهٔ engine)
python -m minutemate run ..\meeting.mp3 --out-dir output --stem session1 --num-speakers 4

# اجرای روی CPU (بدون GPU)
python -m minutemate run ..\meeting.mp3 --out-dir output --stem session1 --device cpu --compute-type int8

# حالت جلسه‌محور (M2): ساخت data/sessions/<date>-<slug>/{raw,work,out} + session.json
python -m minutemate run ..\meeting.mp3 --sessions-root ..\data\sessions --num-speakers 4
python -m minutemate data list
```

> اگر بسته را نصب می‌کنی: `pip install -e engine` و سپس فقط `minutemate run …` (شورتکات `run` اختیاری است).

### ۴.۲ دسکتاپ

```powershell
dotnet build desktop\MinuteMate.Desktop.sln
dotnet run --project desktop\src\MinuteMate.App\MinuteMate.App.csproj
```

اگر موتور شناسایی نشد، از صفحهٔ تنظیمات (یا `desktop\src\MinuteMate.App\appsettings.json`) مقدار `Engine.PythonPath` یا `Engine.PythonModule` (پیش‌فرض `minutemate`) را تنظیم کن. تنظیمات در `%LOCALAPPDATA%\MinuteMate\settings.json` ذخیره می‌شود.

اپ: فرم عنوان/ تاریخ/گویندگان/دستگاه، «بررسی آمادگی» (preflight)، دانلود خودکار مدل در اولین اجرا، کارت «جلسات اخیر» با جست‌وجو، «نمایش/پوشه/اجرای مجدد» و دکمهٔ «باز کردن خروجی».

ساخت نسخهٔ توزیع:

```powershell
pwsh -NoProfile -File scripts\build_engine.ps1 -Clean   # sidecar (PyInstaller)
pwsh -NoProfile -File scripts\build_installer.ps1 -SkipEngine  # publish + Inno → dist\MinuteMate-Setup-0.1.0.exe
```

نصاب بدون مدل ساخته می‌شود (مدل در اولین اجرا دانلود می‌شود) و فایل `.env` خام و بدون کلید کنار برنامه نصب می‌گردد؛ با به‌روزرسانی یا حذف برنامه پاک نمی‌شود. برای افزودن دستی پرووایدر، `GROQ_API_KEY=...` را در همان `.env` بگذار.

جزئیات: `docs/03-operations/packaging.md` و `docs/06-product/install-guide.md`.

---

## ۵. مرجع CLI

```text
minutemate run [audio] [گزینه‌ها]      اجرای خط لوله
minutemate models list|verify|download  مدیریت مدل‌ها
minutemate preflight                    بررسی پیش‌نیازها (خروجی JSON)
minutemate data list|index|prune|archive|adopt  مدیریت جلسه‌ها و داده (M2)
```

| گزینه (`run`) | پیش‌فرض | توضیح |
| :--- | :--- | :--- |
| `--out-dir` | `output` | پوشهٔ خروجی (حالت مسطح) |
| `--session-dir` | — | پوشهٔ صریح جلسه؛ `work/` و `out/` جدا و `session.json` ساخته می‌شود |
| `--sessions-root` | — | ریشهٔ جلسه‌ها؛ شناسهٔ `<date>-<slug>` خودکار |
| `--stem` | `meeting` | پیشوند نام فایل‌های خروجی |
| `--title` | `جلسه <stem>` | عنوان در سرصفحهٔ گزارش‌ها |
| `--date` | تاریخ امروز | تاریخ گزارش (ISO) |
| `--num-speakers` | `4` | تعداد گویندگان (`0` = تخمین خودکار) |
| `--speaker-map` | — | مسیر `speaker_map.json` |
| `--device` | `auto` | `auto` \| `cuda` \| `cpu` |
| `--compute-type` | `auto` | `auto`→`float16` روی CUDA و `int8` روی CPU |
| `--language` | `fa` | زبان رونویسی |
| `--models-dir` | — | مسیر مدل‌ها (بر `MINUTEMATE_MODELS_DIR` و `models/` اولویت دارد) |
| `--ffmpeg` | `ffmpeg` | مسیر یا نام فایل اجرایی FFmpeg |
| `--beam-size` | `1` | اندازهٔ beam در Whisper (سرعت ↔ دقت) |
| `--batch-size` | `0` | batch رونویسی روی GPU؛ `0` خاموش |
| `--chunk-seconds` | `1800` | طول چانک ASR برای جلسات طولانی؛ `0` خاموش |
| `--chunk-overlap` | `5` | هم‌پوشانی چانک‌های ASR (ثانیه) |
| `--parallel-stages` | `auto` | موازی‌سازی دیاریزیشن/رونویسی (`auto` = فقط CUDA) |
| `--speaker-embedding` | `wespeaker` | مدل embedding گوینده (`wespeaker` \| `3dspeaker`) |
| `--asr-model` | `turbo` | مدل رونویسی: `turbo` (سریع) \| `fa` (مدل فارسی، دقت بالا، فقط در همین حالت دانلود می‌شود) |
| `--asr-provider` | `local` | `local` (faster-whisper) \| `groq` (ابری؛ نیازمند `GROQ_API_KEY`) |
| `--groq-model` | `whisper-large-v3-turbo` | مدل Groq هنگام `--asr-provider groq` |
| `--num-threads` | `6` | تعداد ریسه برای ONNX |
| `--log-level` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `--job` | — | `-` = خواندن job از stdin (حالت ماشین) |

---

## ۶. حالت ماشین (قرارداد دسکتاپ ↔ موتور)

```powershell
python -m minutemate run --job -
```

job JSON روی **stdin**، رویدادهای NDJSON روی **stdout**، لاگ‌ها روی **stderr**.

```json
{
  "jobId": "8f1c…",
  "audioPath": "C:\\meetings\\session.mp3",
  "outputDirectory": "C:\\meetings\\out",
  "stem": "session",
  "title": "جلسهٔ هفتگی",
  "date": "2026-10-19",
  "numSpeakers": 4,
  "device": "auto",
  "computeType": "auto",
  "language": "fa",
  "speakerMap": { "0": { "name": "مهدی", "role": "سرپرست" } },
  "minutes": {
    "enabled": false,
    "provider": "none",
    "baseUrl": "https://api.example.com/v1",
    "model": "example-model",
    "apiKeyEnv": "MINUTEMATE_LLM_API_KEY"
  }
}
```

```jsonl
{"type":"started","message":"session.mp3 · cuda (float16)"}
{"type":"stage","stage":"transcription","status":"running","progress":0.42,"etaSeconds":310.0}
{"type":"artifact","kind":"02_diarized_cleaned_transcript.md","path":"C:\\meetings\\out\\02_diarized_cleaned_transcript.md"}
{"type":"done","message":"128 utterance · C:\\meetings\\out","durationSeconds":742.5}
```

جزئیات کامل: [`docs/02-contracts/job-json.md`](./docs/02-contracts/job-json.md) و [`docs/02-contracts/ndjson-events.md`](./docs/02-contracts/ndjson-events.md).

مرحلهٔ صورت‌جلسه (`minutes`) اختیاری است: با `provider=none` (یا `enabled=false`) رد می‌شود و هیچ تماس شبکه‌ای انجام نمی‌شود. کلید سرویس **هرگز** داخل job نمی‌آید؛ فقط نام متغیر محیطی در `apiKeyEnv` داده می‌شود. قرارداد کامل در [`docs/02-contracts/minutes.md`](./docs/02-contracts/minutes.md).

---

## ۷. خروجی‌ها

| فایل | توضیح |
| :--- | :--- |
| `<stem>_16k_mono.wav` | صدای پیش‌پردازش‌شده (ورودی مراحل بعد) |
| `<stem>.segments.json` / `.jsonl` | قطعه‌های Whisper با واژه‌ها و زمان‌ها |
| `<stem>.txt` / `.srt` | رونویسی ساده و زیرنویس |
| `<stem>.speakers.json` / `.speakers.txt` | نتیجهٔ تفکیک گویندگان |
| `<stem>_transcript.json` | نتیجهٔ ادغام متن و گویندگان (utterance‌ها) |
| `01_raw_transcript.txt` | رونویسی خام با تایم‌استمپ |
| `02_diarized_cleaned_transcript.txt` | متن گوینده‌محور، پالایش‌شده |
| `02_diarized_cleaned_transcript.md` | همان متن با Markdown (ورودی مهارت صورت‌جلسه) |
| `03_official_meeting_minutes.md` | صورت‌جلسهٔ رسمی — مرحلهٔ `minutes` (یا مهارت `persian-meeting-minutes`) |
| `04_action_items.md` | کارت‌های اکشن‌آیتم و RACI — مرحلهٔ `minutes` (یا مهارت `meeting-action-tracker`) |
| `<stem>.minutes.json` | صورت‌جلسهٔ ساختاریافته (منبع حقیقت رندر؛ تغییر نام گوینده بدون فراخوانی دوبارهٔ LLM) |
| `session.json` | manifest جلسه در حالت `--session-dir`/`--sessions-root` (منبع `data list`/`index`) |

در حالت جلسه‌محور (M2): فایل‌های میانی (`_16k_mono.wav`, `.segments.*`, `.speakers.*`, `_transcript.json`) در `work/` و تحویل‌دادنی‌ها (`01_`…`04_`, `*.minutes.json`) در `out/` قرار می‌گیرند. جزئیات: [`docs/04-data/sessions.md`](./docs/04-data/sessions.md).

---

## ۸. مدل‌ها

| گروه | فایل | حجم | منبع |
| :--- | :--- | :--- | :--- |
| ASR | `whisper/faster-whisper-large-v3-turbo/*` | ~1.6 GB | HuggingFace (`deepdml`) |
| ASR فارسی (اختیاری) | `whisper/faster-whisper-large-v3-persian-ct2-int8/*` | ~1.5 GB | HuggingFace (`AmirMohseni`) — فقط با `--asr-model fa` لازم است |
| Diarization | `speaker/sherpa-onnx-pyannote-segmentation-3-0/model.onnx` | ~6 MB | GitHub releases (`k2-fsa/sherpa-onnx`) |
| Embedding | `speaker/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx` | ~28 MB | همان |
| Embedding | `speaker/wespeaker_en_voxceleb_resnet34_LM.onnx` | ~25 MB | همان |

مسیر جست‌وجو: `--models-dir` → `MINUTEMATE_MODELS_DIR` → `<repo>/models` (می‌تواند junction/سمبولیک‌لینک باشد).

```powershell
python -m minutemate models verify     # گزارش فایل‌های موجود/ناقص
python -m minutemate models download --type whisper
```

---

## ۹. ساختار پوشه‌ها

```
Minute-mate/
├── engine/                 موتور پایتونی (بستهٔ minutemate + tests)
├── desktop/                اپ WPF (.NET 8): App / Core / EngineClient / tests
├── models/                 مدل‌ها (junction؛ در git نیست)
├── data/                   دادهٔ جلسات، بنچمارک‌ها و خروجی‌ها (رجوع به docs/04-data)
├── scripts/smoke_job.py    تست دود انتها-به-انتها در حالت NDJSON
├── scripts/evaluate.py     ارزیابی WER/CER/DER/JER + RTF روی مجموعهٔ طلایی
├── docs/                   مستندات پروژه
├── .agents/skills/         مهارت‌های عامل (صورت‌جلسه، گوینده‌یاب، اکشن‌آیتم)
├── .opencode/plugins/      هوک‌های تضمین کیفیت
├── ROADMAP.md              نقشهٔ راه
└── AGENTS.md               راهنمای عامل‌های کدنویس
```

### متغیرهای محیطی

| متغیر | مصرف | توضیح |
| :--- | :--- | :--- |
| `MINUTEMATE_MODELS_DIR` | موتور | مسیر مدل‌ها |
| `GROQ_API_KEY` | موتور | کلید(های) Groq برای `asrProvider=groq`؛ چند کلید را با کاما جدا کنید (round-robin). از `.env` هم خوانده می‌شود |
| `MINUTEMATE_DATA_DIR` | دسکتاپ | ریشهٔ دادهٔ اپ (`%LOCALAPPDATA%\MinuteMate` به‌صورت پیش‌فرض) |

---

## ۱۰. تست و کیفیت

```powershell
python -m pytest -q                                     # از engine/ → تست‌های واحد
python scripts\smoke_job.py scratch\sample30.wav         # از ریشه → اجرای واقعی NDJSON
python scripts\evaluate.py --registry data\benchmarks\registry.json --run-all
dotnet test desktop\MinuteMate.Desktop.sln               # تست‌های قرارداد C#
```

> ارزیابی فعلی روی نمونهٔ `mm19-0062` با مرجع **draft** است؛ عدد WER/DER آن برای مقایسهٔ نسبی است، نه پذیرش. جزئیات: [`data/benchmarks/README.md`](./data/benchmarks/README.md).
>
> دروازهٔ رگرسیون: `python scripts\evaluate.py ... --baseline <report.json>` (افت بیش از ۱ واحد WER/DER ⇒ خروجی ۳).
> CI: `.github/workflows/ci.yml` روی ویندوز — ۱۱۳ pytest + ۳۱ تست دسکتاپ + build بدون warning.

پروژه با هوک‌های `.opencode/plugins/` محافظت می‌شود: ساخت خودکار سولوشن پس از ویرایش C#، اجرای تست دود پس از ویرایش موتور، هشدار ناهم‌خوانی قرارداد موتور/دسکتاپ و قفل پوشهٔ مرجع.

---

## ۱۱. مشارکت و توسعه

قبل از هر تغییر، [`AGENTS.md`](./AGENTS.md) را بخوان (قراردادها، قواعد UTF-8، مدل‌ها، هوک‌ها). خلاصهٔ قواعد:

1. هر تغییر رفتاری موتور ⇐ تست واحد یا پوشش در `scripts/smoke_job.py`.
2. تغییر `events.py`/`config.py` ⇐ هم‌زمان به‌روزرسانی `desktop/src/MinuteMate.Core/Contracts/`.
3. فایل‌های حجیم (`models/`, `data/`) هرگز کامیت نشوند.
4. همهٔ فایل‌های متنی با `.gitattributes` به LF نرمال می‌شوند؛ ویرایشگر را روی LF بگذار تا diff تمیز بماند.
5. تغییر رفتار ⇐ به‌روزرسانی سند مربوطه در `docs/` و در صورت نیاز `ROADMAP.md`.

---

## ۱۲. لایسنس

MIT — نگاه کن به [`LICENSE`](./LICENSE).

مدل‌ها لایسنس خودشان را دارند: `faster-whisper-large-v3-turbo` و مدل‌های `sherpa-onnx` (PyAnnote 3.0 / WeSpeaker / 3D-Speaker).


