# قرارداد ورودی: Job JSON

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال (نسخهٔ ۱) | 1405-07-27 | Contracts |

job را موتور در حالت ماشین (`run --job -`) از **stdin** با کدگذاری UTF-8 می‌خواند. کلیدها camelCase هستند؛ نام‌های snake_case نیز برای سازگاری پذیرفته می‌شوند.

## ۱. نمونهٔ کامل

```json
{
  "jobId": "8f1c4b0e5d7a4c2f",
  "audioPath": "C:\\meetings\\1405-07-27\\session.mp3",
  "outputDirectory": "C:\\meetings\\out",
  "stem": "session",
  "title": "جلسهٔ هفتگی تیم فنی",
  "date": "2026-10-19",
  "numSpeakers": 4,
  "device": "auto",
  "computeType": "auto",
  "language": "fa",
  "ffmpegPath": "C:\\tools\\ffmpeg\\bin\\ffmpeg.exe",
  "modelsDir": "C:\\models",
  "beamSize": 1,
  "numThreads": 6,
  "speakerMap": {
    "0": { "name": "مهدی", "role": "سرپرست فنی" },
    "1": { "name": "سارا", "role": "تحلیل‌گر" }
  }
}
```

## ۲. فیلدها

| کلید | نوع | الزامی | پیش‌فرض | توضیح |
| :--- | :--- | :---: | :--- | :--- |
| `jobId` | string | — | — | شناسهٔ اجرا؛ فقط برای رهگیری در UI استفاده می‌شود |
| `audioPath` | string | ✅ | — | مسیر فایل صوتی/ویدیویی (وجود فایل بررسی می‌شود) |
| `outputDirectory` | string | ✅ | — | پوشهٔ خروجی؛ اگر نباشد خطای `input_error` |
| `stem` | string | — | `meeting` | پیشوند نام فایل‌های خروجی |
| `title` | string | — | `جلسه <stem>` | عنوان در سرصفحهٔ گزارش‌ها |
| `date` | string (ISO) | — | تاریخ امروز | تاریخ روی گزارش‌ها |
| `numSpeakers` | int | — | `4` | `0` = تخمین خودکار تعداد گویندگان |
| `device` | `auto`\|`cuda`\|`cpu` | — | `auto` | `auto` = CUDA اگر موجود باشد، وگرنه CPU |
| `computeType` | string | — | `auto` | `auto` ⇒ `float16` روی CUDA و `int8` روی CPU؛ مقادیر صریح: `float16`, `int8`, `float32` |
| `language` | string | — | `fa` | زبان Whisper |
| `ffmpegPath` | string | — | `ffmpeg` | مسیر/نام FFmpeg |
| `modelsDir` | string | — | حل خودکار | اولویت بر `MINUTEMATE_MODELS_DIR` و `models/` |
| `beamSize` | int | — | `1` | بزرگ‌تر = دقیق‌تر و کندتر |
| `numThreads` | int | — | `6` | ریسه‌های ONNX برای دیاریزیشن |
| `speakerMap` | object | — | `{}` | کلید = شناسهٔ عددی گوینده (رشته)، مقدار = `{name, role, …}` |

## ۳. اعتبارسنجی و خطاها

| شرط | رفتار |
| :--- | :--- |
| نبود `audioPath` یا `outputDirectory` | رویداد `error` با `code=input_error` و `hint`؛ کد خروج ۲ |
| نبود فایل صوتی | `error` با `code=input_error` |
| مقدار نامعتبر `device` | `error` با `code=input_error` (`مقادیر مجاز: auto, cuda, cpu`) |
| `numSpeakers` منفی | `error` با `code=input_error` |
| نبود/ناقص بودن مدل‌ها | `error` با `code=model_missing` و فهرست کوتاه در `hint` |
| نبود cuda هنگام `device=cuda` | `error` با `code=cuda_unavailable` |
| نبود FFmpeg | `error` با `code=ffmpeg_missing` |
| JSON نامعتبر روی stdin | `error` با `code=input_error` و جزئیات پارس در `hint`؛ کد خروج ۲ |

## ۴. قواعد سمت فراخوان

1. job را یک‌بار بنویس و stdin را ببند (موتور منتظر EOF نمی‌ماند؛ پس از خواندن کامل، ادامه می‌دهد).
2. `jobId` یکتا بفرست تا رویدادها قابل رهگیری باشند (پیشنهاد: `Guid.NewGuid().ToString("N")`).
3. مقادیر مسیر را مطلق و بدون کوته‌نویسی بفرست؛ کاراکترهای یونیکد در مسیر مجاز است (UTF-8).
4. برای لغو، پروسه را kill کن (در حالت `cuda` نابودی درخت پروسه لازم است).
5. `speakerMap` را فقط برای شناسه‌هایی بفرست که واقعاً می‌شناسی؛ شناسه‌های ناموجود در خروجی مشکلی ایجاد نمی‌کنند.

## ۵. نگاشت به فیلدهای دسکتاپ

| job | C# |
| :--- | :--- |
| `jobId` | `EngineJobRequest.JobId` |
| `speakerMap` | `EngineJobRequest.SpeakerMap : Dictionary<int, SpeakerProfile>` |
| `device` | `EngineJobRequest.Device : ComputeDevice` (رشته‌ای: `auto`/`cuda`/`cpu`) |
| `date` | `EngineJobRequest.Date : DateOnly?` |

تهی‌سازی JSON در `MinuteMate.Core.Infrastructure.JsonDefaults.Engine`: camelCase + enumها به‌صورت رشتهٔ camelCase.
