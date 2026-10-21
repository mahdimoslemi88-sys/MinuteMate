# مستندات MinuteMate

این پوشه منبع حقیقت پروژه است: معماری، قراردادها، عملیات، داده، کیفیت و محصول. هر تغییر رفتاری باید مستند آن را هم به‌روز کند.

**نقطهٔ شروع برای هر کسی که تازه به پروژه اضافه می‌شود:**

| اگر می‌خواهی… | اول این را بخوان |
| :--- | :--- |
| محصول را بشناسی و نقشهٔ کار را ببینی | [`../README.md`](../README.md) → [`../ROADMAP.md`](../ROADMAP.md) |
| دربارهٔ مسیر پروژه مشورت بدهی (بدون دانش فنی) | [`REVIEW-ROADMAP.md`](./REVIEW-ROADMAP.md) — مستقل و خودبسنده |
| کد را تغییر بدهی | [`../AGENTS.md`](../AGENTS.md) → [`01-architecture/overview.md`](./01-architecture/overview.md) |
| موتور را اجرا/نصب کنی | [`03-operations/setup-windows.md`](./03-operations/setup-windows.md) |
| قرارداد موتور↔دسکتاپ را عوض کنی | [`02-contracts/job-json.md`](./02-contracts/job-json.md) و [`02-contracts/ndjson-events.md`](./02-contracts/ndjson-events.md) |

---

## فهرست

| پوشه | سند | موضوع |
| :--- | :--- | :--- |
| ریشهٔ مستندات | [REVIEW-ROADMAP.md](./REVIEW-ROADMAP.md) | گزارش مستقل نقشهٔ راه برای مشورت و تصمیم |
| `01-architecture` | [overview.md](./01-architecture/overview.md) | نمای کلان، اجزا، مرزها |
| | [engine.md](./01-architecture/engine.md) | ساختار داخلی موتور و ماژول‌ها |
| | [desktop.md](./01-architecture/desktop.md) | اپ WPF و لایه‌ها |
| | [data-flow.md](./01-architecture/data-flow.md) | مسیر داده از صدا تا صورت‌جلسه |
| `02-contracts` | [job-json.md](./02-contracts/job-json.md) | قرارداد ورودی (job) |
| | [ndjson-events.md](./02-contracts/ndjson-events.md) | قرارداد خروجی (رویدادها) |
| | [artifacts.md](./02-contracts/artifacts.md) | فایل‌های تولیدی و مسیرها |
| | [minutes.md](./02-contracts/minutes.md) | قرارداد مرحلهٔ صورت‌جلسه (M3a) |
| | [engine-process-runner.md](./02-contracts/engine-process-runner.md) | رفتار اجراکنندهٔ موتور و لغو/لاگ (M1a) |
| `03-operations` | [setup-windows.md](./03-operations/setup-windows.md) | نصب و راه‌اندازی |
| | [models.md](./03-operations/models.md) | مدل‌ها، مسیرها، لایسنس |
| | [performance.md](./03-operations/performance.md) | تنظیم سرعت و GPU |
| | [troubleshooting.md](./03-operations/troubleshooting.md) | خطاهای رایج و راه‌حل |
| | [packaging.md](./03-operations/packaging.md) | ساخت sidecar، نصاب و انتشار |
| | [privacy.md](./03-operations/privacy.md) | لاگ‌ها، رضایت ضبط و مجوز مدل‌ها |
| `04-data` | [`../../data/README.md`](../../data/README.md) | چیدمان داده و چرخهٔ عمر (سند در خود پوشهٔ `data/` است) |
| | [sessions.md](./04-data/sessions.md) | ساختار جلسه و manifest |
| | [benchmarks.md](./04-data/benchmarks.md) | مجموعهٔ ارزیابی |
| | [retention.md](./04-data/retention.md) | نگهداشت، آرشیو، حریم خصوصی |
| `05-quality` | [testing.md](./05-quality/testing.md) | تست‌ها و CI |
| | [evaluation.md](./05-quality/evaluation.md) | سنجش WER/DER و پذیرش |
| `06-product` | [features.md](./06-product/features.md) | فهرست قابلیت‌ها و وضعیت |
| | [workflows.md](./06-product/workflows.md) | جریان‌های کاربری |
| | [install-guide.md](./06-product/install-guide.md) | نصب تا اولین صورت‌جلسه |
| | [faq.md](./06-product/faq.md) | پرسش‌های متداول |
| سرمایهٔ تصویری/دیاگرام | `assets/` | تصاویر و دیاگرام‌ها |

سایر منابع: [`README.md`](../README.md) (شروع سریع) · [`ROADMAP.md`](../ROADMAP.md) (نقشهٔ راه و انتقال کار) · [`AGENTS.md`](../AGENTS.md) (راهنمای عامل‌های کدنویس).

---

## قواعد نوشتن سند

1. **زبان:** فارسی روان؛ اصطلاحات فنی با معادل انگلیسی در پرانتز.
2. **قالب:** Markdown، عنوان‌های شماره‌دار، جدول برای داده‌های ساختاریافته، و کدبلوک با برچسب زبان.
3. **سرصفحهٔ وضعیت:** هر سند با این جدول شروع می‌شود:

   ```markdown
   | وضعیت | آخرین به‌روزرسانی | مالک |
   | :--- | :--- | :--- |
   | فعال | 1405-07-27 | Engine |
   ```

4. **صداقت با واقعیت کد:** هر سند باید وضعیت «اکنون» را توصیف کند؛ آینده در `ROADMAP.md` جای دارد و در سند با برچسب `⏳ M2` مشخص می‌شود.
5. **بدون راز:** هیچ کلید API، مسیر شخصی یا توکن در مستندات نوشته نشود.
6. **تغییر قرارداد:** تغییر در `02-contracts` ⇐ هم‌زمان به‌روزرسانی `engine/minutemate/{events,config}.py` و `desktop/src/MinuteMate.Core/Contracts/`.
7. **هر ادعای عددی، منبع دارد:** عدد کارایی/کیفیت باید یا از اجرای واقعی آمده باشد یا صریحاً «هدف» علامت بخورد.

---

## افزودن سند جدید

1. پوشهٔ مناسب را انتخاب کن (یا در صورت نیاز پوشهٔ شماره‌دار جدید بساز).
2. نام فایل را با حروف کوچک و خط تیره بگذار (`data-flow.md`).
3. سرصفحهٔ وضعیت را اضافه کن و سند را در جدول بالا ثبت کن.
4. اگر سند قرارداد است، ارجاعش را در `README.md` و `AGENTS.md` هم اضافه کن.
5. اگر سند برای مخاطب بیرونی/مشورتی است، آن را کامل خودبسنده بنویس (بدون نیاز به سند دیگر) مثل `REVIEW-ROADMAP.md`.
