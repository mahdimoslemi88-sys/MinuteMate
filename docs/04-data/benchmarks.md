# مجموعهٔ ارزیابی (Benchmarks)

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| طرح‌ریزی‌شده (M4) | 1405-07-27 | Quality |

هدف: عددی‌کردن کیفیت (WER/DER) و زمان، پیش و پس از هر تغییر در موتور یا مدل‌ها.

## ۱. ساختار

```
data/benchmarks/
├── audio/            نمونه‌های صوتی مرجع (16kHz mono توصیه می‌شود)
├── truth/            متن مرجع + برچسب گوینده
│   ├── s01.txt             متن مرجع (خط‌به‌خط)
│   └── s01.rttm            برچسب گوینده (RTTM)
├── reports/
│   ├── 2026-10-19-cpu-int8.md
│   └── 2026-10-19-cuda-fp16.md
└── registry.json
```

## ۲. `registry.json`

```json
{
  "version": 1,
  "samples": [
    {
      "id": "s01",
      "audio": "audio/s01.wav",
      "truthText": "truth/s01.txt",
      "truthRttm": "truth/s01.rttm",
      "condition": "clean-studio",
      "speakers": 2,
      "durationSeconds": 180,
      "language": "fa",
      "notes": "مصاحبهٔ دونفره، استودیویی"
    },
    {
      "id": "s02",
      "audio": "audio/s02.wav",
      "truthText": "truth/s02.txt",
      "condition": "meeting-room-4spk-noise",
      "speakers": 4,
      "durationSeconds": 900,
      "language": "fa",
      "notes": "جلسهٔ واقعی، نویز تهویه و هم‌پوشانی کلام"
    }
  ]
}
```

شرایط (`condition`) پیشنهادی برای پوشش: `clean-studio`, `online-call`, `phone-8k`, `meeting-room-4spk-noise`, `overlap-heavy`.

## ۳. افزودن نمونهٔ جدید

1. صدا را در `audio/<id>.wav` بگذار (اگر ۸k/استریو است، همان را نگه دار تا حالت واقعی سنجیده شود).
2. متن مرجع را در `truth/<id>.txt` بنویس (یک جمله در هر خط).
3. برچسب گوینده را در `truth/<id>.rttm` بگذار (سبک NIST RTTM؛ برای نمونه‌های تک‌نفره لازم نیست).
4. ورودی را در `registry.json` ثبت کن.
5. **رضایت و حریم خصوصی:** فقط صدای دارای اجازهٔ صریح؛ نام‌ها را ناشناس کن (گوینده ۱/۲).

## ۴. اجرای ارزیابی (هدف M4)

```powershell
python scripts\evaluate.py --registry data\benchmarks\registry.json --device cpu --compute-type int8 `
    --out data\benchmarks\reports\2026-10-19-cpu-int8.md
```

گزارش باید شامل این‌ها باشد:

| معیار | معنا |
| :--- | :--- |
| WER | نرخ خطای واژه (پس از پالایش فارسی، بدون نرمال‌سازی گمراه‌کننده) |
| CER | نرخ خطای کاراکتر (برای متون بدون فاصله‌گذاری کامل) |
| DER / JER | نرخ خطای تفکیک گوینده / خطای قضاوت |
| Speaker count error | خطای تعداد گویندهٔ تشخیص‌داده‌شده |
| RTF | نسبت زمان پردازش به مدت صدا |
| Per-stage time | زمان preprocess / diarization / transcription / merge |

## ۵. اهداف

| شاخص | هدف |
| :--- | :--- |
| WER — صدای تمیز | < ۱۲٪ |
| WER — جلسهٔ نویزی ۴ نفره | < ۲۵٪ (هدف بلندمدت) |
| DER — جلسهٔ ۴ نفره | < ۱۰٪ |
| RTF — GPU | < 0.2 |

## ۶. قواعد سنجش منصفانه

1. یک ثبت (seed/دستگاه/مدل) را ثابت نگه دار و فقط یک متغیر را تغییر بده.
2. متن مرجع را با همان قاعدهٔ پالایش خروجی نرمال کن تا نیم‌فاصله WER را مصنوعی بالا نبرد (یا هر دو حالت را گزارش کن).
3. هر گزارش باید `engineVersion`، نسخهٔ مدل‌ها، دستگاه و `computeType` را ثبت کند.
4. نتایج را در `reports/` نگه دار؛ حذف گزارش‌های قدیمی ممنوع (تاریخ‌نگار رگرسیون).
