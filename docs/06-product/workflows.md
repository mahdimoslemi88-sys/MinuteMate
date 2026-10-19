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

## ۳. «صورت‌جلسهٔ رسمی و مصوبات» (مدیر جلسه) ⏳ M3

```
۱. اجرای موتور تا مرحلهٔ export
۲. مهارت persian-meeting-minutes روی 02_…md
۳. تولید 03_official_meeting_minutes.md (شناسنامه، حاضرین، مصوبات، ریسک‌ها)
۴. مهارت meeting-action-tracker ⇒ 04_action_items.md (SMART + RACI)
۵. بازبینی انسانی: چک‌لیست docs/05-quality/evaluation.md
۶. ذخیرهٔ نسخهٔ نهایی در data/sessions/<id>/out/ و exports/
```

موفقیت = صورت‌جلسه‌ای که بدون بازنویسی بتوان به سازمان فرستاد.

---

## ۴. «باید کیفیت را اندازه بگیرم» (توسعه‌دهنده) ⏳ M4

```powershell
python -m pytest -q
python scripts\smoke_job.py scratch\sample30.wav --num-speakers 2
python scripts\evaluate.py --registry data\benchmarks\registry.json --out data\benchmarks\reports\new.md
dotnet test desktop\MinuteMate.Desktop.sln
```

موفقیت = عدد WER/DER و RTF قابل مقایسه با گزارش قبلی، بدون افت.

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
