# تست و CI

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال (واحد) · CI ⏳ M4 | 1405-07-27 | Quality |

## ۱. هرم تست

| سطح | ابزار | محل | چه چیزی را تضمین می‌کند |
| :--- | :--- | :--- | :--- |
| واحد (پایتون) | `pytest` | `engine/tests/` | قرارداد رویداد، منطق ادغام، پالایش فارسی، رجیستری مدل |
| قرارداد (C#) | `xunit` | `desktop/tests/MinuteMate.Core.Tests/` | نگاشت JSON/enum بین C# و قرارداد |
| دود (انتها-به-انتها) | `scripts/smoke_job.py` | ریشهٔ پروژه | اجرای واقعی موتور در حالت NDJSON روی یک فایل صوتی |
| پذیرش (انسانی) | چک‌لیست | [`evaluation.md`](./evaluation.md) | کیفیت صورت‌جلسه و اکشن‌آیتم‌ها |

## ۲. فرمان‌ها

```powershell
# واحد — از پوشهٔ engine
python -m pytest -q

# دود — از ریشهٔ پروژه (به یک فایل صوتی نیاز دارد)
python scripts\smoke_job.py scratch\sample30.wav --num-speakers 2 --speaker "0=مهدی:سرپرست"

# قرارداد C#
dotnet test desktop\MinuteMate.Desktop.sln

# همه با هم (پیشنهاد پیش از اعلام پایان کار)
python -m pytest -q; python scripts\smoke_job.py scratch\sample30.wav; dotnet test desktop\MinuteMate.Desktop.sln
```

## ۳. پوشش تست‌های موجود

| فایل | چه چیزی را می‌سنجد | نکته |
| :--- | :--- | :--- |
| `engine/tests/test_events.py` | camelCase بودن و حذف کلیدهای `null` در `EngineEvent` | نگهبان قرارداد NDJSON |
| `engine/tests/test_merge.py` | تخصیص گوینده بر اساس هم‌پوشانی + حالت بدون نتیجهٔ دیاریزیشن | قلب کیفیت خروجی |
| `engine/tests/test_normalize.py` | نیم‌فاصله (پیشوند/پسوند/جمع)، واژه‌نامه، فاصله‌ها | مُهر هویت فارسی |
| `engine/tests/test_registry.py` | حل مسیر مدل‌ها + گزارش ناقص‌بودن | مانع خطای زمان اجرا |
| `desktop/tests/…/EngineContractsTests.cs` | پارس نمونهٔ رویداد/ job | جلوگیری از واگرایی دو زبان |

## ۴. هوک‌های تضمین کیفیت (خودکار)

| هوک | رفتار |
| :--- | :--- |
| `.opencode/plugins/smoke-gate.js` | پس از ویرایش ماژول‌های موتور، `scripts/smoke_job.py` را در پس‌زمینه اجرا و نتیجه را اعلام می‌کند (`MINUTEMATE_SMOKE=0` خاموش) |
| `.opencode/plugins/dotnet-after-edit.js` | پس از ویرایش هر `*.cs`، سولوشن را build و خطاهای کامپایل را به نتیجهٔ ابزار می‌چسباند (`MINUTEMATE_DOTNET=0` خاموش) |
| `.opencode/plugins/contract-sync.js` | ناهم‌خوانی `events.py`/`config.py` ↔ `Contracts/*.cs` را هشدار می‌دهد |

## ۵. افزودن تست

1. برای هر باگ، ابتدا تست شکست‌خورده بنویس و بعد اصلاح کن.
2. تست‌های موتور بدون نیاز به مدل و شبکه اجرا شوند (fixture در `tmp_path`, `NullEventSink`).
3. نام‌گذاری: `test_<ماژول>.py::test_<رفتار>_<شرط>`.
4. اگر رفتار در حالت ماشین تغییر می‌کند، نمونهٔ رویداد را در تست قرار بده تا شکستن قرارداد سریع دیده شود.

## ۶. CI پیشنهادی (M4)

```yaml
# .github/workflows/ci.yml (طرح)
jobs:
  engine:
    steps:
      - python -m pip install -r engine/requirements.txt pytest
      - python -m pytest -q  (working-directory: engine)
  desktop:
    steps:
      - dotnet build desktop/MinuteMate.Desktop.sln
      - dotnet test  desktop/MinuteMate.Desktop.sln
  contract:
    steps:
      - python -m minutemate preflight || true     # فقط بررسی سلامت مسیرها
```

**شرط سبزی CI:** `pytest` سبز + `dotnet test` سبز + بیلد بدون warning. تست دود سنگین (نیازمند مدل ۱.۶GB) در CI اجرا نمی‌شود؛ به‌جایش یک تست قرارداد روی رویدادهای ذخیره‌شده اجرا می‌گردد.

## ۷. تست لغو و خرابی (هدف M4)

| سناریو | انتظار |
| :--- | :--- |
| لغو در میانهٔ `transcription` | رویداد `error` با `code=cancelled`، کد خروج ۱۳۰، بدون فایل نیم‌بند |
| فایل صوتی خراب | `error` با `code=input_error` و پیام روشن، نه traceback |
| مدل نصفه‌کاره (حجم کم) | `error` با `code=model_missing` و نام فایل |
| `device=cuda` بدون GPU | `error` با `code=cuda_unavailable` و پیشنهاد `--device cpu` |
| پوشهٔ خروجی بدون دسترسی نوشتن | `error` روشن با مسیر |
