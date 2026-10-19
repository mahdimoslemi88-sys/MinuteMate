# قرارداد خروجی: رویدادهای NDJSON

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال (نسخهٔ ۱) | 1405-07-27 | Contracts |

در حالت ماشین، موتور **فقط** رویدادهای JSON خط‌محور روی **stdout** می‌نویسد؛ هر خط یک شیء کامل JSON است (`ensure_ascii=false`، یونیکد خام، جداکنندهٔ خط `\n`). همهٔ لاگ‌ها به **stderr** می‌روند.

## ۱. قواعد سخت

| قاعده | دلیل |
| :--- | :--- |
| stdout = فقط NDJSON | پارس خط‌به‌خط در سمت مصرف‌کنندهٔ ساده |
| stderr = لاگ، پیشرفت انسانی، traceback | جداسازی ماشین از انسان |
| هر خط یک JSON کامل، بدون چندخطی | خواندن بدون بافر پیچیده |
| نیامدن کلیدهای `null` | پیام کوچک‌تر |
| فیلدها camelCase | هم‌راستا با C# |

## ۲. پوشش رویداد

| کلید | نوع | توضیح |
| :--- | :--- | :--- |
| `type` | string | `started` \| `stage` \| `log` \| `artifact` \| `error` \| `done` |
| `stage` | string? | `preprocess` \| `diarization` \| `transcription` \| `merge` \| `export` \| `minutes` |
| `status` | string? | `pending` \| `running` \| `done` \| `failed` |
| `progress` | number? | ۰ تا ۱ برای مرحلهٔ جاری |
| `etaSeconds` | number? | تخمین زمان باقی‌ماندهٔ مرحله |
| `level` | string? | برای `log`: `debug` \| `info` \| `warning` \| `error` |
| `message` | string? | متن انسانی (فارسی) |
| `code` | string? | برای `error`: شناسهٔ ماشین‌خوان |
| `hint` | string? | برای `error`: راهنمای رفع |
| `kind` | string? | برای `artifact`: نام فایل خروجی |
| `path` | string? | برای `artifact`: مسیر مطلق |
| `durationSeconds` | number? | برای `done`: مدت کل |

## ۳. ترتیب و تضمین‌ها

```
started
  stage(preprocess, running, 0) … stage(preprocess, done, 1)
  stage(diarization, running, 0) … stage(…, done, 1)
  stage(transcription, running, 0) … stage(…, done, 1)
  stage(merge, …) 
  stage(export, …) → artifact × N
done
```

- در پایان موفق همیشه یک `done` می‌آید (و `artifact`ها پیش از آن).
- در پایان ناموفق همیشه یک `error` می‌آید و هیچ `done`.
- `log` ممکن است در هر نقطه ظاهر شود؛ ترتیب نسبی‌اش با مراحل تضمین نمی‌شود.
- پیشرفت هر مرحله با ۰ شروع (بجز مراحل رد‌شده) و با ۱ `status=done` پایان می‌یابد.
- رویدادهای `stage` با throttle ارسال می‌شوند (حداکثر ~۲ در ثانیه برای هر مرحله).

## ۴. نمونه (واقعی)

```jsonl
{"type":"started","message":"session.mp3 · cpu (int8)"}
{"type":"stage","stage":"preprocess","status":"running","progress":0,"message":"نرمال‌سازی و تبدیل صدا"}
{"type":"stage","stage":"preprocess","status":"running","progress":0.53}
{"type":"stage","stage":"preprocess","status":"done","progress":1}
{"type":"stage","stage":"transcription","status":"running","progress":0.42,"etaSeconds":310}
{"type":"log","level":"info","message":"بارگذاری مدل Whisper از C:\\…\\faster-whisper-large-v3-turbo روی CPU (int8)"}
{"type":"artifact","kind":"01_raw_transcript.txt","path":"C:\\meetings\\out\\01_raw_transcript.txt"}
{"type":"artifact","kind":"02_diarized_cleaned_transcript.md","path":"C:\\meetings\\out\\02_diarized_cleaned_transcript.md"}
{"type":"done","message":"9 utterance · C:\\meetings\\out","durationSeconds":742.5}
```

```jsonl
{"type":"error","code":"model_missing","message":"۴ فایل مدل پیدا نشد یا ناقص است.","hint":"whisper/…/model.bin (missing)"}
```

## ۵. کدهای خروج پروسه

| کد | معنا |
| :---: | :--- |
| `0` | موفق (`done` منتشر شده) |
| `1` | خطای موتور (`error` منتشر شده) |
| `2` | خطای ورودی/job (پیش از شروع خط لوله یا آرگومان نامعتبر) |
| `130` | لغو با `Ctrl+C`/SIGINT |

## ۶. کدهای خطا (`code`)

| کد | معنا | راهنمای سریع |
| :--- | :--- | :--- |
| `input_error` | ورودی نامعتبر | `audioPath`/`outputDirectory`/`device` را بررسی کن |
| `model_missing` | مدل نبود/ناقص | `minutemate models verify` و سپس `download` |
| `ffmpeg_missing` | FFmpeg پیدا نشد | نصب یا `--ffmpeg <path>` |
| `cuda_unavailable` | CUDA نبود | `--device cpu` یا نصب CUDA 12 |
| `cancelled` | لغو توسط کاربر | — |
| `stage_error` | خطای مرحلهٔ داخلی | `--log-level DEBUG` و پیام `hint` |
| `internal_error` | خطای پیش‌بینی‌نشده | traceback در stderr |

## ۷. نسخه‌گذاری قرارداد

- افزودن فیلد اختیاری = سازگار.
- تغییر نوع/نام فیلد موجود یا حذف آن = **شکستن قرارداد** و نیازمند به‌روزرسانی هم‌زمان `documents/…`, `engine/minutemate/events.py` و `desktop/src/MinuteMate.Core/Contracts/EngineEvent.cs`.
- فیلدهای ناشناس در سمت C# نادیده گرفته می‌شوند (`JsonSerializerOptions` پیش‌فرض) و در سمت پایتون اضافی مجاز است.
