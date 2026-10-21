# جریان‌های کاربری

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال | 1405-07-27 | Product |

## ۱. «فقط می‌خواهم متن جلسه را داشته باشم» (کاربر ارشد)

```powershell
python -m minutemate preflight
python -m minutemate run "C:\meetings\haftegi.mp3" --out-dir output\haftegi --stem haftegi --num-speakers 4 --device auto
```

خروجی مورد استفاده: `02_diarized_cleaned_transcript.md`
موفقیت = متن خوانا با نام گویندگان و تایم‌استمپ.

---

## ۲. «نمی‌دانم کدام گوینده کیست» (بازبینی گویندگان)

```
۱. اجرا با تخمین خودکار:   --num-speakers 0
۲. خواندن 02_diarized_cleaned_transcript.md و یافتن سرنخ‌ها
۳. ساخت speaker_map.json   (مهارت diarization-speaker-mapper)
۴. اجرای مجدد با نگاشت:    --speaker-map speaker_map.json
۵. تأیید چشمی برچسب‌ها در خروجی
```

موفقیت = هیچ «گوینده N» در خروجی نهایی نمانده (یا موارد نامعلوم صریحاً علامت خورده باشند).

---

## ۳. «صورت‌جلسهٔ رسمی و مصوبات» (مدیر جلسه) ✅ M3a

دو مسیر معادل:

**الف) خودکار داخل موتور (M3a):** با تنظیم `minutes.enabled=true` و یک provider، مرحلهٔ `minutes` بعد از `export` اجرا می‌شود.

```
۱. job JSON با minutes: {enabled, provider, baseUrl, model, apiKeyEnv}
۲. اجرای موتور تا مرحلهٔ minutes
۳. تولید 03_official_meeting_minutes.md + 04_action_items.md + <stem>.minutes.json
۴. بازبینی انسانی موارد بخش «نیازمند بازبینی» و ویرایش نام گوینده در minutes.json
```

**ب) نیمه‌دستی با مهارت‌ها:**

```
۱. اجرای موتور تا مرحلهٔ export (provider=none)
۲. مهارت persian-meeting-minutes روی 02_…md
۳. تولید 03_official_meeting_minutes.md (شناسنامه، حاضرین، مصوبات، ریسک‌ها)
۴. مهارت meeting-action-tracker ⇒ 04_action_items.md (SMART + RACI)
۵. بازبینی انسانی: چک‌لیست docs/05-quality/evaluation.md
۶. ذخیرهٔ نسخهٔ نهایی در data/sessions/<id>/out/ و exports/
```

موفقیت = صورت‌جلسه‌ای که بدون بازنویسی بتوان به سازمان فرستاد، و هر مصوبه/اقدام شاهد utterance داشته باشد.

---

## ۴. «باید کیفیت را اندازه بگیرم» (توسعه‌دهنده) ✅ M4a

```powershell
python -m pytest -q
python scripts\smoke_job.py scratch\sample30.wav --num-speakers 2
python scripts\evaluate.py --registry data\benchmarks\registry.json --run-all
dotnet test desktop\MinuteMate.Desktop.sln
```

موفقیت = عدد WER/DER و RTF قابل مقایسه با گزارش قبلی، بدون افت. نمونهٔ فعلی مرجع draft دارد؛ برای عدد رسمی `--strict-truth` پس از اصلاح انسانی.

---

## ۵. «روی سیستم دیگری نصب کنم» (راهبر سیستم)

```
۱. Python 3.10+ ، FFmpeg ، .NET 8 (docs/03-operations/setup-windows.md)
۲. pip install -r engine\requirements.txt
۳. اتصال مدل‌ها: junction یا MINUTEMATE_MODELS_DIR
۴. python -m minutemate preflight  ⇒ modelsReady=true
۵. python scripts\smoke_job.py <یک نمونه صدا>  ⇒ کد خروج ۰
۶. dotnet build desktop\MinuteMate.Desktop.sln
```

موفقیت = همهٔ اقلام چک‌لیست سلامت نصب در `setup-windows.md` سبز.

---

## ۶. «جلسه را چند بار پردازش کرده‌ام و خروجی‌ها قاطی شده»

```
راه‌حل کوتاه‌مدت:  --stem "<تاریخ>-<نام>" --out-dir output\<تاریخ>-<نام>
راه‌حل بلندمدت (M2): هر جلسه یک پوشه با manifest در data/sessions
```

موفقیت = هر اجرا یک پوشهٔ مستقل با `session.json`.

---

## ۷. «همه‌چیز از داخل اپ دسکتاپ» ✅ M1

```
۱. «انتخاب فایل» ⇒ فایل صوتی/تصویری جلسه
۲. فرم اجرا: عنوان، تاریخ، تعداد گویندگان، دستگاه، نوع محاسبه (پیش‌فرض‌ها از settings.json)
۳. «بررسی آمادگی» ⇒ preflight: «آماده/ناقص» + مدل‌های ناقص + دستگاه/FFmpeg
۴. «شروع پردازش» ⇒ job با jobId یکتا و sessionsRoot؛ شناسهٔ `<تاریخ>-<slug>` (تکرار ⇒ `-2`)
۵. کارت «پردازش جلسه»: مرحله + نوار پیشرفت + ETA + لاگ زنده (stdout/stderr موتور)
۶. «لغو» ⇒ لغو نرم موتور؛ تا دریافت رویداد cancelled دکمهٔ لغو غیرفعال می‌ماند
۷. خطا ⇒ بنر قرمز با کد خطا و hint + «باز کردن پوشهٔ لاگ» (<jobId>)
۸. پس از done ⇒ «باز کردن خروجی» (ترجیحاً 03_ یا 02_) + نمایش در «جلسات اخیر»
۹. «جلسات اخیر»: جست‌وجو در عنوان/تاریخ/متن، «نمایش»، «پوشه»، «اجرای مجدد» از کپی raw/
```

موفقیت = کاربر بدون ترمینال به متن تفکیک‌شدهٔ گویندگان و تاریخچهٔ جلسه‌ها برسد و در صورت خرابی، از لاگ و پیام روشن سرنخ بگیرد.
