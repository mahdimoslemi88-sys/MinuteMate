---
name: meeting-action-tracker
description: Use when the user asks for اکشن‌آیتم / action items / پیگیری وظایف / RACI / Jira or Linear or Trello task cards extracted from a MinuteMate meeting transcript or minutes. Produces SMART tasks with owners, deadlines, acceptance criteria and a RACI matrix.
---

# مهارت استخراج و پیگیری اقدامات اجرایی (Meeting Action Tracker)

گفتگوی جلسه را به **وظایف قابل اجرا**، ماتریس پاسخگویی (RACI) و کارت‌های آمادهٔ Jira / Linear / Trello تبدیل کن.

---

## ۱. اصل SMART

هر اقدام باید: **Specific** (چه کاری) · **Measurable** (خروجی ملموس: کد/سند/تست/گزارش) · **Assignable** (فقط یک مسئول پاسخگو) · **Realistic** · **Time-bound** (تاریخ مشخص).

اگر گفتگو معیارها را ندارد، آن را به‌عنوان «ورودی ناقص» علامت بزن — وظیفهٔ مبهم نساز.

---

## ۲. ماتریس RACI

* **R (Responsible):** مجری مستقیم.
* **A (Accountable):** پاسخگوی نهایی (مدیر پروژه / معمار سیستم).
* **C (Consulted):** صاحب‌نظرانی که پیش از انجام باید مشورت شوند.
* **I (Informed):** افرادی که پس از اتمام در جریان قرار می‌گیرند.

---

## ۳. قالب کارت تسک

```markdown
### 📌 عنوان تسک: [عنوان کوتاه و اکشن‌پذیر]
- **دسته‌بندی:** [Frontend / Backend / AI / DevOps / Product / Marketing]
- **مسئول مستقیم (Assignee):** [نام شخص]
- **مهلت انجام (Due Date):** [تاریخ دقیق]
- **اولویت:** [بحرانی (P0) / بالا (P1) / متوسط (P2)]
- **شرح اقدام (Description):**
  [مرحله‌به‌مرحله]
- **معیار پذیرش (Acceptance Criteria):**
  - [ ] معیار ۱
  - [ ] معیار ۲
- **وابستگی‌ها (Dependencies):** [تسک‌های پیش‌نیاز]
- **نقل‌قول از جلسه (Source Quote):** *"[نقل قول با تایم‌استمپ]"*
```

---

## ۴. گردش کار و خروجی

1. منبع را از `output/` بردار: `02_diarized_cleaned_transcript.md` و اگر موجود است `03_official_meeting_minutes.md`.
2. نام‌ها را از `speaker_map.json` بگیر؛ اگر نیست، برچسب `گوینده N` را استفاده کن.
3. دو خروجی بده:
   - جدول خلاصه (ردیف/اقدام/مسئول/مهلت/خروجی/وضعیت) برای درج در صورت‌جلسه.
   - کارت‌های تسک بر اساس قالب بخش ۳، در فایل `04_action_items.md` در همان پوشهٔ خروجی.
4. برای هر اقدام، تایم‌استمپ منبع را ذکر کن تا قابل راستی‌آزمایی باشد.
5. در پایان، اقدامات بدون مسئول یا بدون ددلاین را در بخش «نیازمند تعیین» فهرست کن.
