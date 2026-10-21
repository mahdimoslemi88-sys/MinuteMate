# ساختار جلسه و Manifest

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| پیاده‌سازی‌شده (M2، م2.1–م2.4) | 1405-07-28 | Data |

## ۱. ساختار پوشه

```
data/sessions/2026-10-19-haftegi/
├── raw/
│   └── haftegi.mp3                 # فایل اصلی، تغییرناپذیر
├── work/
│   ├── haftegi_16k_mono.wav        # پیش‌پردازش‌شده
│   ├── haftegi.segments.json/.jsonl
│   ├── haftegi.speakers.json/.txt
│   └── haftegi_transcript.json     # خروجی merge
├── out/
│   ├── 01_raw_transcript.txt
│   ├── 02_diarized_cleaned_transcript.txt
│   ├── 02_diarized_cleaned_transcript.md
│   ├── 03_official_meeting_minutes.md      # ✅ M3a
│   ├── 04_action_items.md                  # ✅ M3a
│   └── haftegi.minutes.json                # ✅ M3a (منبع حقیقت رندر)
├── speaker_map.json                # اختیاری، نتیجهٔ مهارت گوینده‌یاب
└── session.json                    # manifest
```

## ۲. `session.json`

```json
{
  "schemaVersion": 1,
  "id": "2026-10-19-haftegi",
  "title": "جلسهٔ هفتگی تیم فنی",
  "date": "2026-10-19",
  "createdAt": "2026-10-19T18:04:22+03:30",
  "source": {
    "fileName": "haftegi.mp3",
    "sizeBytes": 48219766,
    "sha256": "3f1c…",
    "durationSeconds": 1820.4,
    "sampleRate": 16000,
    "channels": 1
  },
  "run": {
    "device": "cuda",
    "computeType": "float16",
    "language": "fa",
    "numSpeakersRequested": 4,
    "numSpeakersDetected": 4,
    "engineVersion": "0.1.0",
    "models": {
      "whisper": "faster-whisper-large-v3-turbo",
      "segmentation": "sherpa-onnx-pyannote-segmentation-3-0",
      "embedding": "wespeaker_en_voxceleb_resnet34_LM"
    },
    "durationSeconds": 168.7,
    "stageSeconds": {
      "preprocess": 0.7,
      "diarization": 3.4,
      "transcription": 58.2,
      "merge": 0.1,
      "export": 0.2
    },
    "overlapCount": 2
  },
  "speakers": [
    { "id": 0, "name": "مهدی", "role": "سرپرست فنی", "confidence": "high" },
    { "id": 1, "name": null, "role": null, "confidence": "unknown" }
  ],
  "artifacts": [
    { "kind": "02_diarized_cleaned_transcript.md", "path": "out/02_diarized_cleaned_transcript.md", "bytes": 18244 }
  ],
  "tags": ["هفتگی", "فنی"],
  "status": "transcribed",
  "notes": ""
}
```

| فیلد | معنا |
| :--- | :--- |
| `schemaVersion` | نسخهٔ قرارداد manifest؛ افزایش با هر تغییر شکستنده |
| `status` | `raw` → `transcribed` → `minutes` → `final` |
| `speakers[].confidence` | خروجی مهارت گوینده‌یاب (`high`/`medium`/`low`/`unknown`) |
| `artifacts[]` | مسیرها **نسبی** به پوشهٔ جلسه |
| `run.models` | نسخهٔ دقیق مدل‌ها برای بازتولیدپذیری |
| `run.stageSeconds` | زمان هر مرحله؛ ورودی تاریخچهٔ سرعت برای ETA (M6.3) |
| `run.overlapCount` | تعداد utteranceهای گفتار هم‌زمان (M6.6) |

`<data>/metrics/device_speed.json` (یا `metricsDirectory` در job) میانهٔ آخرین ۵ اجرا برای هر `device:computeType` را نگه می‌دارد؛ ETA از همین تاریخچه محاسبه می‌شود.

## ۳. چرخهٔ عمر یک جلسه

```
raw/ (کپی فایل اصلی)
  → work/ (پیش‌پردازش + دیاریزیشن + ASR + merge)
  → out/ (01_, 02_)
  → [مهارت گوینده‌یاب] speaker_map.json → اجرای مجدد برای اعمال نام‌ها
  → out/ (03_, 04_, *.minutes.json) [M3a]
  → status = final  →  آرشیو (فشرده‌سازی work/)
```

| گذار | کار | تأیید |
| :--- | :--- | :--- |
| raw → work | `preprocess`, `diarization`, `transcription`, `merge` | وجود `work/*_transcript.json` |
| work → out | `export` | وجود `01_` و `02_` |
| out → نام‌گذاری | اعمال `speaker_map.json` | برچسب گوینده‌ها = نام واقعی |
| out → minutes | مرحلهٔ `minutes` [M3a] | وجود `03_`، `04_` و `*.minutes.json` |
| نهایی → آرشیو | فشرده‌سازی `work/`، حفظ `raw/` و `out/` | کاهش حجم ≥ ۵۰٪ |

## ۴. کار با جلسه

```powershell
# M2
python -m minutemate run .\raw\haftegi.mp3 --session-dir data\sessions\2026-10-19-haftegi --num-speakers 4
python -m minutemate run .\raw\haftegi.mp3 --sessions-root data\sessions --num-speakers 4   # شناسه خودکار
python -m minutemate data list
python -m minutemate data index
python -m minutemate data prune --older-than 90d --target work --keep-transcripts
python -m minutemate data archive --session 2026-10-19-haftegi --delete
python -m minutemate data adopt .\output --id 2026-10-19-haftegi --title "جلسهٔ هفتگی"
```

حالت مسطح (سازگاری قدیمی، بدون `session.json`):

```powershell
python -m minutemate run .\haftegi.mp3 --out-dir data\sessions\2026-10-19-haftegi\work --stem haftegi --num-speakers 4
```

### ۴.۱ در اپ دسکتاپ (M1b)

- هر اجرا با `sessionsRoot` ارسال می‌شود و شناسهٔ `<تاریخ>-<slug>` خودکار ساخته می‌شود؛ اجرای دوم با همان عنوان/تاریخ پسوند `-2` می‌گیرد.
- کارت «جلسات اخیر» مستقیماً `session.json`ها را می‌خواند (`SessionCatalog`): وضعیت، تاریخ، مدت و تعداد گوینده.
- جست‌وجو روی عنوان/شناسه/وضعیت/تاریخ و متن `out/02_diarized_cleaned_transcript.md` (که «ي/ك» و ارقام فارسی نرمال می‌شوند).
- «نمایش» فایل `03_` (یا `02_`) را باز می‌کند، «پوشه» پوشهٔ جلسه و «اجرای مجدد» فایل `raw/` را به‌عنوان ورودی برمی‌گرداند.

## ۵. قواعد یکپارچگی

1. `raw/` پس از ایجاد **هرگز** تغییر نمی‌کند (مرجع بازتولید).
2. `work/` قابل حذف است؛ حذف آن فقط زمان بازتولید را زیاد می‌کند.
3. نام فایل‌های `out/` بخشی از قرارداد است و تغییر نمی‌کند.
4. ویرایش انسانی صورت‌جلسه در `out/03_…` مجاز است؛ نسخهٔ خودکار در `out/03_….generated.md` نگه داشته می‌شود تا تفاوت‌ها قابل مشاهده باشد.
5. هر جلسه باید `session.json` معتبر داشته باشد؛ نبود آن ⇒ هشدار در UI و در `data list`.
