# قرارداد خروجی: فایل‌ها (Artifacts)

| وضعیت | آخرین‌سازی | مالک |
| :--- | :--- | :--- |
| فعال | 1405-07-27 | Contracts |
هر فایل تولیدی، نام ثابت و وابسته به `stem` دارد؛ در حالت مسطح همه در `--out-dir` و در ساختار هدف (⏳ M2) در `work/` و `out/` نوشته می‌شوند.

## ۱. فهرست کامل

| فایل | مرحلهٔ سازنده | وضعیت | توضیح |
| :--- | :--- | :--- | :--- |
| `<stem>_16k_mono.wav` | `preprocess` | ✅ | صدای ۱۶kHz مونو، پالایش‌شده (ورودی مراحل بعد) |
| `<stem>.segments.json` | `transcription` | ✅ | قطعه‌های Whisper + واژه‌ها + زمان + احتمال |
| `<stem>.segments.jsonl` | `transcription` | ✅ | همان، خط‌محور برای استریم |
| `<stem>.txt` | `transcription` | ✅ | رونویسی ساده (بدون زمان) |
| `<stem>.srt` | `transcription` | ✅ | زیرنویس SRT |
| `<stem>.speakers.json` | `diarization` | ✅ | نوبت‌های گفتار و شناسهٔ گوینده |
| `<stem>.speakers.txt` | `diarization` | ✅ | نمای انسانی نوبت‌ها |
| `<stem>_transcript.json` | `merge` | ✅ | utterance‌ها با گوینده، زمان و متن + `overlap`/`overlapCount` (M6.6) |
| `01_raw_transcript.txt` | `export` | ✅ | رونویسی خام با تایم‌استمپ |
| `02_diarized_cleaned_transcript.txt` | `export` | ✅ | متن پالایش‌شدهٔ گوینده‌محور (متن ساده) |
| `02_diarized_cleaned_transcript.md` | `export` | ✅ | همان با ساختار Markdown (ورودی مهارت صورت‌جلسه) |
| `03_official_meeting_minutes.md` | `minutes` | ✅ M3a | صورت‌جلسهٔ رسمی (قرارداد: `minutes.md`) |
| `04_action_items.md` | `minutes` | ✅ M3a | کارت‌های اکشن‌آیتم + RACI |
| `<stem>.minutes.json` | `minutes` | ✅ M3a | منبع ساختاریافتهٔ صورت‌جلسه (شناسهٔ گوینده/شاهد/نیاز به بازبینی) |
| `session.json` | لایهٔ داده | ⏳ M2 | manifest جلسه |

## ۲. نمونهٔ ساختار `segments.json`

```json
{
  "audio": "session_16k_mono.wav",
  "language": "fa",
  "duration": 1800.4,
  "segments": [
    {
      "id": 0,
      "start": 1.02,
      "end": 3.44,
      "text": "سلام، جلسه را شروع می‌کنیم",
      "words": [
        { "start": 1.02, "end": 1.41, "word": "سلام", "probability": 0.91 }
      ]
    }
  ]
}
```

## ۳. نمونهٔ ساختار `speakers.json`

```json
{
  "audio": "session_16k_mono.wav",
  "turns": [
    { "start": 0.9, "end": 6.4, "speaker": 0 },
    { "start": 6.4, "end": 11.2, "speaker": 1 }
  ]
}
```

## ۴. نمونهٔ ساختار `_transcript.json` (خروجی merge)

```json
{
  "audio": "session_16k_mono.wav",
  "overlapCount": 1,
  "utterances": [
    {
      "speaker": 0,
      "start": 0.9,
      "end": 3.44,
      "text": "سلام، جلسه را شروع می‌کنیم"
    },
    {
      "speaker": 1,
      "start": 12.2,
      "end": 14.0,
      "text": "بله، موافقم",
      "overlap": true
    }
  ]
}
```

## ۵. قواعد نام‌گذاری و پایداری

1. نام فایل‌ها بخشی از قرارداد است؛ تغییر آن = شکستن قرارداد (نیازمند نسخه‌گذاری).
2. `stem` را از نام فایل صوتی و ترجیحاً شامل تاریخ بگیر تا خروجی‌ها بازنویسی نشوند (`1405-07-27-session`).
3. هر فایل با کدگذاری UTF-8 و بدون BOM نوشته می‌شود (به‌جز WAV که دودویی است).
4. فایل‌های میانی (`_16k_mono.wav`, `segments.*`, `speakers.*`) قابل حذف و بازتولید هستند؛ فایل‌های `01_`/`02_`/`03_`/`04_` تحویل نهایی محسوب می‌شوند.
5. رویداد `artifact` برای هر فایل تحویلی منتشر می‌شود تا UI بدون حدس‌زدن مسیر، فایل‌ها را نشان دهد.
