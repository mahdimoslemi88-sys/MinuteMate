---
name: diarization-speaker-mapper
description: Use when the user wants to identify who said what in a MinuteMate diarized transcript (02_diarized_cleaned_transcript.md, *.segments.json, "گوینده ۱ کیست؟", speaker_map.json). Analyzes mention patterns, introductions and topic ownership to map anonymous speakers to real people and emit speaker_map.json.
---

# مهارت تطبیق و بازشناسی گویندگان (Speaker Mapper)

هویت گویندگان ناشناس (`گوینده ۱`، `گوینده ۲`، …) را از روی سرنخ‌های گفتگو کشف کن و `speaker_map.json` استاندارد تولید کن.

---

## ۱. سرنخ‌های کشف هویت

1. **خطاب مستقیم:** «مهدی جان نظر تو در مورد دیتابیس چیه؟» ⟹ گوینده‌ای که پاسخ می‌دهد با احتمال بالا «مهدی» است.
2. **معرفی و احوال‌پرسی:** «سلام من رضایی هستم از تیم فرانت‌اند…» ⟹ گویندهٔ فعلی، آقای رضایی، توسعه‌دهندهٔ فرانت‌اند.
3. **مالکیت موضوعی:** بحث مداوم دربارهٔ سرور، داکر و پایپ‌لاین ⟹ احتمالاً سرپرست فنی.
4. **ارجاع سوم‌شخص:** «همان‌طور که سجاد در چت نوشت…» ⟹ تطبیق زمان صحبت.
5. **الگوهای تکرارشده در `*.speakers.json`:** تعداد نوبت‌ها و طول مکالمه در تصمیم‌گیری کمک می‌کند.

---

## ۲. گردش کار

1. `02_diarized_cleaned_transcript.md` و در صورت نیاز `*.segments.json` را کامل اسکن کن.
2. جدول فرضی گویندگان را با **شواهد نقل‌قولی** بساز.
3. `speaker_map.json` را با این ساختار در ریشهٔ پوشهٔ خروجی ذخیره کن:

```json
{
  "0": {
    "name": "نام شخص",
    "role": "عنوان شغلی / نقش در جلسه",
    "confidence": "high",
    "evidence": "در ۰۰:۰۴:۱۲ گوینده ۲ او را با نام خطاب کرد."
  },
  "1": {
    "name": "نام شخص ۲",
    "role": "عنوان شغلی",
    "confidence": "medium",
    "evidence": "تنها کسی که گزارش سرورها را ارائه داد."
  }
}
```

> موتور فقط `name` و `role` را می‌خواند؛ `confidence` و `evidence` برای بازبینی انسانی است و نادیده گرفته می‌شود.

4. اعمال روی اجرا:
   - CLI: `python -m minutemate run <audio> --out-dir output --stem <session> --speaker-map speaker_map.json`
   - حالت ماشین/دسکتاپ: کلید `speakerMap` در job JSON (کلیدهای عددی به‌صورت رشته).
5. اگر کاربر نخواهد پایپ‌لاین دوباره اجرا شود، می‌توانی فقط متن `02_diarized_cleaned_transcript.md` را با نام‌های واقعی بازنویسی کنی.
6. موارد `confidence: low` را حتماً به‌عنوان «نیازمند تأیید کاربر» علامت بزن.
