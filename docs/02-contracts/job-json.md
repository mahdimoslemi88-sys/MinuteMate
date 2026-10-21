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
  "metricsDirectory": "C:\\meetings\\metrics",
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
  "batchSize": 0,
  "asrChunkSeconds": 1800,
  "asrChunkOverlapSeconds": 5,
  "parallelStages": "auto",
  "speakerEmbedding": "wespeaker",
  "asrModel": "turbo",
  "asrProvider": "local",
  "groqModel": "whisper-large-v3-turbo",
  "autoDownloadModels": false,
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
| `outputDirectory` | string | ✅* | — | پوشهٔ خروجی؛ اگر نباشد خطای `input_error`. (*) اگر `sessionDirectory`/`sessionsRoot` داده شود، اختیاری است |
| `sessionDirectory` | string | — | — | پوشهٔ صریح جلسه (`.../<id>/{raw,work,out}` + `session.json`) ✅ M2 |
| `sessionsRoot` | string | — | — | ریشهٔ جلسه‌ها؛ شناسه از `<date>-<slug>` ساخته می‌شود ✅ M2 |
| `metricsDirectory` | string | — | `<data>/metrics` | محل `device_speed.json` برای ETA بر پایهٔ تاریخچه ✅ M6.3 |
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
| `batchSize` | int | — | `0` | `0` = خاموش؛ `۴–۱۶` روی GPU سریع‌تر (استفاده از `BatchedInferencePipeline`) ✅ M6.2 |
| `asrChunkSeconds` | number | — | `1800` | طول چانک رونویسی برای جلسات طولانی؛ `۰` = بدون بخش‌بندی ✅ M6.1 |
| `asrChunkOverlapSeconds` | number | — | `5` | هم‌پوشانی چانک‌ها؛ باید کمتر از `asrChunkSeconds` باشد ✅ M6.1 |
| `parallelStages` | `auto`\|`on`\|`off` | — | `auto` | اجرای موازی دیاریزیشن و رونویسی؛ `auto` یعنی فقط روی CUDA ✅ M6.5 |
| `speakerEmbedding` | string | — | `wespeaker` | `wespeaker`\|`3dspeaker` یا مسیر `.onnx` برای A/B دیاریزیشن ✅ M6.4 |
| `asrModel` | `turbo`\|`fa`\|`persian` | — | `turbo` | مدل محلی رونویسی: `turbo` = `faster-whisper-large-v3-turbo`؛ `fa` = مدل فارسی `faster-whisper-large-v3-persian-ct2-int8` (فقط برای همین مدل اجباری است و در `models verify` اختیاری گزارش می‌شود) |
| `asrProvider` | `local`\|`groq` | — | `local` | منبع رونویسی: `local` = faster-whisper؛ `groq` = Groq Cloud (whisper-large-v3-turbo، نیازمند `GROQ_API_KEY`) |
| `groqModel` | string | — | `whisper-large-v3-turbo` | مدل Groq هنگام `asrProvider=groq` (`whisper-large-v3` هم پذیرفته می‌شود) |
| `autoDownloadModels` | bool | — | `false` | دانلود خودکار مدل‌های ناقص با رویداد `stage: models`؛ دسکتاپ `true` می‌فرستد ✅ M5.2 |
| `numThreads` | int | — | `6` | ریسه‌های CPU (Whisper روی CPU) و ONNX برای دیاریزیشن |
| `speakerMap` | object | — | `{}` | کلید = شناسهٔ عددی گوینده (رشته)، مقدار = `{name, role, …}` |
| `minutes` | object | — | `{}` | پیکربندی مرحلهٔ صورت‌جلسه؛ قرارداد کامل در [`minutes.md`](./minutes.md) ✅ M3a |

## ۳. اعتبارسنجی و خطاها

| شرط | رفتار |
| :--- | :--- |
| نبود `audioPath` یا `outputDirectory` | رویداد `error` با `code=input_error` و `hint`؛ کد خروج ۲ (اگر `sessionDirectory`/`sessionsRoot` باشد، فقط `audioPath` لازم است) |
| نبود فایل صوتی | `error` با `code=input_error` |
| مقدار نامعتبر `device` | `error` با `code=input_error` (`مقادیر مجاز: auto, cuda, cpu`) |
| `numSpeakers` منفی | `error` با `code=input_error` |
| نبود/ناقص بودن مدل‌ها | `error` با `code=model_missing` و فهرست کوتاه در `hint`؛ فقط مدل‌های لازم برای `asrModel` انتخاب‌شده بررسی می‌شوند (مدل فارسی برای حالت `turbo` اجباری نیست) |
| نبود cuda هنگام `device=cuda` | `error` با `code=cuda_unavailable` |
| نبود FFmpeg | `error` با `code=ffmpeg_missing` |
| JSON نامعتبر روی stdin | `error` با `code=input_error` و جزئیات پارس در `hint`؛ کد خروج ۲ |
| وجود کلید `apiKey`/`api_key` در `minutes` | `error` با `code=input_error` (کلید فقط از `apiKeyEnv`) |
| `provider` نامعتبر یا `baseUrl` ناامن در `minutes` | `error` با `code=input_error` |

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
| `asrModel` | `EngineJobRequest.AsrModel : string` (`turbo`/`fa`) |

تهی‌سازی JSON در `MinuteMate.Core.Infrastructure.JsonDefaults.Engine`: camelCase + enumها به‌صورت رشتهٔ camelCase.
