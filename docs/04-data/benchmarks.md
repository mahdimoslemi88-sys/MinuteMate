# مجموعهٔ ارزیابی (Benchmarks)

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال (M4a) | 1405-07-28 | Quality |

هدف: عددی‌کردن کیفیت (WER/DER) و زمان، پیش و پس از هر تغییر در موتور یا مدل‌ها.

## ۱. ساختار

```
data/benchmarks/
├── audio/            نمونه‌های صوتی مرجع (16kHz mono توصیه می‌شود؛ در git نیست)
├── truth/            متن مرجع + برچسب گوینده (کامیت می‌شود)
│   ├── mm19-0062.txt       متن مرجع
│   └── mm19-0062.rttm      برچسب گوینده (RTTM)
├── reports/          گزارش‌های .md/.json (کامیت می‌شود)
├── work/             خروجی موتور برای هر نمونه (gitignore)
├── README.md         رویهٔ عملی و وضعیت مرجع‌ها
└── registry.json
```

## ۲. `registry.json`

```json
{
  "schemaVersion": 1,
  "samples": [
    {
      "id": "mm19-0062",
      "stem": "mm19-0062",
      "audio": "audio/mm19-0062.wav",
      "truthText": "truth/mm19-0062.txt",
      "truthRttm": "truth/mm19-0062.rttm",
      "condition": "far-field, single speaker, noisy meeting room",
      "speakers": 1,
      "durationSeconds": 30.02,
      "language": "fa",
      "truthStatus": "draft",
      "truthSource": "ASR draft from beam_size=5; not human-verified"
    }
  ]
}
```

`truthStatus` یکی از `human` | `draft` | `missing` است. `--strict-truth` فقط نمونه‌های `human` را می‌پذیرد.

شرایط (`condition`) پیشنهادی برای پوشش: `clean-studio`, `online-call`, `phone-8k`, `meeting-room-4spk-noise`, `overlap-heavy`.

## ۳. افزودن نمونهٔ جدید

1. صدا را در `audio/<id>.wav` بگذار (اگر ۸k/استریو است، همان را نگه دار تا حالت واقعی سنجیده شود).
2. متن مرجع را در `truth/<id>.txt` بنویس (یک جمله در هر خط).
3. برچسب گوینده را در `truth/<id>.rttm` بگذار (سبک NIST RTTM؛ برای نمونهٔ تک‌نفره هم یک نوبت ساده کافی است).
4. ورودی را در `registry.json` ثبت کن.
5. **رضایت و حریم خصوصی:** فقط صدای دارای اجازهٔ صریح؛ نام‌ها را ناشناس کن (گوینده ۱/۲).

## ۴. اجرای ارزیابی

```powershell
# اجرای موتور روی همهٔ نمونه‌ها + گزارش خودکار
python scripts\evaluate.py --registry data\benchmarks\registry.json --run-all

# فقط یک نمونه
python scripts\evaluate.py --sample mm19-0062 --run-all --device cpu --compute-type int8

# ارزیابی خروجی‌های موجود بدون اجرای موتور
python scripts\evaluate.py --hyp-dir data\benchmarks\work\mm19-0062
```

گزارش پیش‌فرض در `data/benchmarks/reports/<تاریخ>-<device>-<compute>.md` و `.json` است. گزارش باید شامل `engineVersion`، مدل‌های کشف‌شده، دستگاه، `computeType`، `beamSize`، `numThreads`، WER/CER/DER/JER، زمان هر مرحله و RTF باشد. جزئیات: [`data/benchmarks/README.md`](../../data/benchmarks/README.md).

## ۵. اهداف

| شاخص | هدف |
| :--- | :--- |
| WER — صدای تمیز | < ۱۲٪ |
| WER — جلسهٔ نویزی ۴ نفره | < ۲۵٪ (هدف بلندمدت) |
| DER — جلسهٔ ۴ نفره | < ۱۰٪ |
| RTF — GPU | < 0.2 |

> نمونهٔ فعلی `mm19-0062` صدای دور و نویزی است و مرجعش draft؛ هدف WER تمیز روی آن معنا ندارد. اولین عدد معتبر پس از اصلاح انسانی متن/RTTM به دست می‌آید.

## ۶. قواعد سنجش منصفانه

1. یک ثبت (seed/دستگاه/مدل) را ثابت نگه دار و فقط یک متغیر را تغییر بده.
2. متن مرجع را با همان قاعدهٔ پالایش خروجی نرمال کن تا نیم‌فاصله WER را مصنوعی بالا نبرد.
3. هر گزارش باید `engineVersion`، نسخهٔ مدل‌ها، دستگاه و `computeType` را ثبت کند.
4. نتایج را در `reports/` نگه دار؛ حذف گزارش‌های قدیمی ممنوع (تاریخ‌نگار رگرسیون).
5. مرجع `draft` را با `human` اشتباه نگیر؛ در CI از `--strict-truth` استفاده کن.
