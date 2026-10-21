# رفع اشکال

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال | 1405-07-27 | Ops |

## ۱. جدول علائم ⇒ راه‌حل

| علامت | علت احتمالی | راه‌حل |
| :--- | :--- | :--- |
| `error: model_missing` | مدل نبود/ناقص یا مسیر اشتباه | `python -m minutemate models verify` سپس `models download`؛ یا `--models-dir` / `MINUTEMATE_MODELS_DIR` |
| `error: ffmpeg_missing` | FFmpeg روی `PATH` نیست | `winget install Gyan.FFmpeg` یا `--ffmpeg "C:\tools\ffmpeg\bin\ffmpeg.exe"` |
| `error: cuda_unavailable` | نبود CUDA/cuDNN یا درایور | `--device cpu`، یا نصب CUDA 12 + بسته‌های `nvidia-*` |
| `error: input_error` (فایل ورودی) | فایل وجود ندارد یا مسیر اشتباه | مسیر مطلق، بدون علامت نقل‌قول اضافه |
| `error: input_error` (job JSON) | JSON نامعتبر روی stdin | اعتبار JSON را بررسی کن؛ BOM نگذار؛ فقط یک شیء |
| خروجی متن خالی/بی‌معنا | صدای بی‌کیفیت، تداخل، یا زبان اشتباه | `--language fa`، نسخهٔ بهتر صدا، `--beam-size 5` |
| همه در «گوینده ۱» | دیاریزیشن تعداد گویندهٔ اشتباه یا صدای مشابه | `--num-speakers 0` (تخمین خودکار) یا عدد درست؛ امبدینگ مناسب بسنج |
| گوینده‌ها جابه‌جا | گفتار هم‌زمان یا قطعهٔ کوتاه | خروجی را بازبینی و با `speaker_map` اصلاح کن؛ ادغام `overlap` در M6 |
| متن فارسی چسبیده (بدون نیم‌فاصله) | واژه‌نامه ناکافی | `engine/minutemate/resources/glossary_fa.json` را کامل کن |
| کرش/Crash در بارگذاری مدل | RAM/VRAM ناکافی | `--compute-type int8`، بستن برنامه‌های سنگین، جلسه را تکه‌تکه کن |
| در ترمینال متن «?» نمایش می‌یابد | کدگذاری کنسول | `chcp 65001`؛ (داخل موتور UTF-8 تضمین شده است) |
| خروجی‌ها بازنویسی می‌شوند | `stem` ثابت | `--stem "<تاریخ>-<نام>"` یا ساختار جلسهٔ M2 |
| `error: llm_auth_missing` | متغیر کلید LLM تنظیم نشده/رد شد | `$env:MINUTEMATE_LLM_API_KEY="…"` (یا نام `minutes.apiKeyEnv`) |
| `error: llm_unavailable`/`llm_timeout` | شبکه/سرویس LLM یا مهلت کم | `baseUrl` را بررسی کن؛ `minutes.timeoutSeconds` را بالا ببر |
| `error: llm_bad_response` | مدل JSON معتبر نداد | مدل قوی‌تر یا `provider=ollama` با مدل بزرگ‌تر؛ retry خودکار یک‌بار انجام می‌شود |
| `error: minutes_parse_error` | رونویسی خالی/ناقص است | خروجی‌های `01_`/`02_` و `_transcript.json` را بررسی کن |
| صورت‌جلسه تولید نشد اما اجرا سبز بود | `minutes.enabled=false` یا `provider=none` | مرحله را در job فعال کن؛ رویداد `stage(minutes)` با پیام «غیرفعال» رد می‌شود |
| `dotnet build` قفل فایل | اجرای هم‌زمان اپ | اپ را ببند یا `dotnet build-server shutdown` |
| `error: cuda_unavailable` | GPU/CUDA ناقص است | موتور یک بار خودکار روی CPU/int8 تلاش می‌کند (لاگ `warning`)؛ اگر باز هم خطا داد DLLهای CUDA را نصب یا `--device cpu` بده |
| اپ: «موتور آماده نیست» | پایتون/موتور پیدا نشد | `Engine.PythonPath` یا `Engine.ExecutablePath` را در `appsettings.json` ست کن |
| اپ: هشدار «نسخهٔ موتور … هم‌خوان نیست» | نسخهٔ major/minor موتور و دسکتاپ یکی نیست | `python -m minutemate --version` و `<Version>` در `desktop/Directory.Build.props` را یکی کن؛ قرارداد job ممکن است تغییر کرده باشد |

## ۲. تشخیص گام‌به‌گام

```powershell
# ۱) پیش‌نیازها
python -m minutemate preflight

# ۲) مدل‌ها
python -m minutemate models verify

# ۳) اجرای پرحرف (لاگ DEBUG روی stderr)
python -m minutemate run .\a.mp3 --out-dir out --stem t --log-level DEBUG

# ۴) حالت ماشین و دیدن رویدادها
python -m minutemate run --job - < job.json
```

## ۳. خواندن لاگ‌ها

| جریان | محتوا | مصرف‌کننده |
| :--- | :--- | :--- |
| `stdout` (حالت ماشین) | فقط NDJSON | برنامه‌ها |
| `stderr` | لاگ انسانی + پیشرفت + traceback | انسان |

پس اگر «هیچ چیز در stdout نیست» یعنی موتور یا کرش کرده (traceback را در stderr ببین) یا job نامعتبر بوده.

## ۴. بازتولید امن

```powershell
# اجرای مجدد فقط با حدف فایل‌های میانی (خروجی نهایی حفظ می‌شود)
Remove-Item out\t_16k_mono.wav, out\t.segments.*, out\t.speakers.* -Force -ErrorAction SilentlyContinue
python -m minutemate run .\a.mp3 --out-dir out --stem t
```

## ۵. تست دود به‌عنوان نقطهٔ مرجع

اگر تغییری دادی و مطمئن نیستی، اول این را اجرا کن:

```powershell
python scripts\smoke_job.py scratch\sample30.wav --num-speakers 2
```

خروجی مطلوب: `exit code: 0`، رویدادهای `started/stage/artifact/done` و `unparseable stdout lines: 0`.

## ۶. گزارش مشکل

هنگام گزارش، این‌ها را بفرست: خروجی `preflight`، اولین خط `error` (با `code` و `hint`)، خروجی `python -m minutemate models verify`، نسخهٔ پایتون/FFmpeg/درایور و اگر ممکن است ۱۰ ثانیه نمونهٔ صدا.
