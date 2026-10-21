# تست و CI

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال (واحد + CI) | 1405-07-28 | Quality |

## ۱. هرم تست

| سطح | ابزار | محل | چه چیزی را تضمین می‌کند |
| :--- | :--- | :--- | :--- |
| واحد (پایتون) | `pytest` | `engine/tests/` | قرارداد رویداد، منطق ادغام، پالایش فارسی، رجیستری مدل |
| قرارداد (C#) | `xunit` | `desktop/tests/MinuteMate.Core.Tests/` | نگاشت JSON/enum بین C# و قرارداد |
| رفتار اجراکننده (C#) | `xunit` + موتور fake | `desktop/tests/MinuteMate.EngineClient.Tests/` | لاگ زندهٔ stderr، لغو، نگاشت کد خروج، UTF-8 |
| وضعیت UI (C#) | `xunit` + runner جعلی | `desktop/tests/MinuteMate.App.Tests/` | نگاشت `stage`/`log`/`error`/`done` به ViewModel |
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
| `engine/tests/test_merge.py` | تخصیص گوینده بر اساس هم‌پوشانی، حالت بدون دیاریزیشن، علامت‌گذاری گفتار هم‌زمان | قلب کیفیت خروجی/M6.6 |
| `engine/tests/test_normalize.py` | نیم‌فاصله (پیشوند/پسوند/جمع)، واژه‌نامه، فاصله‌ها | مُهر هویت فارسی |
| `engine/tests/test_registry.py` | حل مسیر مدل‌ها + گزارش ناقص‌بودن | مانع خطای زمان اجرا |
| `engine/tests/test_evaluate.py` | نرمال‌سازی فارسی، WER/CER، DER/JER، RTTM، گزارش draft، دروازهٔ رگرسیون | نگهبان اعداد M4 |
| `engine/tests/test_minutes_config.py` | پیش‌فرض‌ها، رد `apiKey` در job، اعتبارسنجی provider/baseUrl/model | مرز امنیتی M3a |
| `engine/tests/test_minutes_chunking.py` | شناسه‌گذاری `u####`/`spk#`، تقسیم قطعه‌ها، متن شاهد | ورودی مرحلهٔ صورت‌جلسه |
| `engine/tests/test_minutes_parse.py` | حذف `code fence`، اعتبارسنجی شاهد، `needsReview`، ادغام/شناسه‌گذاری | دقت ساختاریافته |
| `engine/tests/test_minutes_render.py` | بخش‌های Markdown، جدول RACI، مدت انسانی | خروجی نهایی |
| `engine/tests/test_minutes_provider.py` | نگاشت خطای HTTP/timeout/auth، ساخت URL، هدر Bearer | بدون تماس شبکه (transport تزریقی) |
| `engine/tests/test_minutes_stage.py` | رد شدن وقتی غیرفعال، تولید هر سه فایل، retry، انتشار خطا | با provider جعلی |
| `engine/tests/test_session.py` | slug/شناسه، چیدمان `raw/work/out`، رفت‌وبرگشت `session.json`، `scan`/`index`، `parse_age`، `prune` (dry-run/keep)، `archive`، `adopt` | قرارداد M2 |
| `engine/tests/test_speed.py` | نرخ پیش‌فرض، میانه/سقف نمونه‌ها، تحمل JSON خراب، ETA مرحلهٔ رونویسی، ثبت `stageSeconds` | M6.3 |
| `engine/tests/test_chunking.py` | پنجره‌های چانک (کوتاه/۲ ساعته)، ادغام و حذف تکراری ناحیهٔ هم‌پوشانی، آفست زمان‌ها و پاک‌شدن WAVهای موقت | M6.1 |
| `engine/tests/test_prompts.py` | بارگذاری قالب‌های صورت‌جلسه و جای‌گذاری بدون placeholder باقی‌مانده | M3b.3 |
| `engine/tests/test_downloads.py` | دانلود خودکار مدل‌ها و رویداد پیشرفت مرحلهٔ `models` | M5.2 |
| `engine/tests/test_parallel.py` | `parallelStages` (auto/on/off)، تفکیک پیشرفت مراحل، نوشتن اتمی NDJSON در چند ریسه، انتخاب embedding در registry | M6.4/M6.5 |
| `engine/tests/test_failures.py` | صدا/فایل نبود، دستگاه نامعتبر، FFmpeg نبود/صدا خراب، مدل ناقص، خطای CUDA/OOM + بازگشت خودکار به CPU، batch، لغو، `engineVersion` | M4.4/M6.2؛ مجموع ۱۱۸ تست |
| `desktop/tests/…/EngineContractsTests.cs` | پارس نمونهٔ رویداد/ job | جلوگیری از واگرایی دو زبان؛ ۳ تست |
| `desktop/tests/…/SessionCatalogTests.cs` | مرتب‌سازی manifestها، نادیده‌گرفتن JSON خراب، مسیرهای خروجی/صدا، جست‌وجوی عنوان و متن، نرمال‌سازی «ي/ك» | ۴ تست |
| `desktop/tests/…/EngineProcessRunnerTests.cs` | لاگ زندهٔ stderr قبل از خروج، stdout نویزی، کدهای خروج ۰/۱/۲، لغو، UTF-8 فارسی، truncate، `input_pipe_closed` | موتور fake مبتنی بر PowerShell؛ ۹ تست |
| `desktop/tests/…/MainWindowViewModelTests.cs` | نگاشت `stage`/`eta`/`artifact`/`error`/`cancelled`، فرم اجرا و `sessionsRoot`، بارگذاری/جست‌وجوی جلسه‌ها، اجرای مجدد، انتخاب آخرین خروجی، ذخیرهٔ تنظیمات، ارسال/عدم ارسال `minutes`، هشدار ناهم‌خوانی نسخه | ۱۶ تست |
| `desktop/tests/…/ViewLoadTests.cs` | بارگذاری واقعی `SettingsWindow`/`ProviderSettingsView` روی ریسهٔ STA با `Theme.xaml` | جلوگیری از `XamlParseException` و `StaticResource` گم‌شده (باگ واقعی صفحهٔ پرووایدر)؛ ۱ تست |

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

## ۶. CI

فایل واقعی: `.github/workflows/ci.yml` — دو job روی `windows-latest`:

```yaml
engine:  python 3.12 → choco install ffmpeg → pip install -e ".\engine[dev]" → pytest
desktop: dotnet 8 → dotnet build -warnaserror → dotnet test
```

**شرط سبزی CI:** `pytest` سبز + `dotnet test` سبز + بیلد بدون warning. تست دود سنگین (نیازمند مدل ۱.۶GB) در CI اجرا نمی‌شود؛ دروازهٔ رگرسیون بنچمارک (`evaluate.py --baseline`) هم به‌صورت دستی/خارج از CI اجرا می‌شود.

## ۷. تست لغو و خرابی (هدف M4)

| سناریو | انتظار |
| :--- | :--- |
| لغو در میانهٔ `transcription` | رویداد `error` با `code=cancelled`، کد خروج ۱۳۰، بدون فایل نیم‌بند |
| فایل صوتی خراب | `error` با `code=input_error` و پیام روشن، نه traceback |
| مدل نصفه‌کاره (حجم کم) | `error` با `code=model_missing` و نام فایل |
| `device=cuda` بدون GPU | `error` با `code=cuda_unavailable` و پیشنهاد `--device cpu` |
| پوشهٔ خروجی بدون دسترسی نوشتن | `error` روشن با مسیر |




