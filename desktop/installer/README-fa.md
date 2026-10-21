# MinuteMate — راهنمای نصب و مدل‌های هوش مصنوعی

نسخهٔ ۰.۱.۰ · ویندوز ۱۰/۱۱ (۶۴ بیتی) · بدون نیاز به پایتون یا .NET

این برنامه **بدون مدل و بدون کتابخانه‌های سنگین GPU** توزیع می‌شود (نصاب ≈ ۳۲۲ MB) تا دانلود آن برای همه ممکن باشد. مدل‌ها را می‌توانید همان لحظهٔ نصب با تیک زدن دانلود کنید؛ بعد از آن همه‌چیز **کاملاً محلی و آفلاین** اجرا می‌شود (به‌جز حالت ابری اختیاری Groq).

---

## ۱. شروع سریع

1. `MinuteMate-Setup-0.1.0.exe` را اجرا و مسیر نصب را تأیید کنید (پیش‌فرض: `%LOCALAPPDATA%\Programs\MinuteMate`).
2. در صفحهٔ **AI models** مدل‌های لازم را تیک بزنید؛ نصاب آن‌ها را همان‌جا دانلود می‌کند (پنجرهٔ کنسول درصد پیشرفت را نشان می‌دهد). لینک دانلود دستی هر مدل هم روی همان صفحه قابل کلیک است.
3. میان‌بر **MinuteMate** را از منوی شروع باز کنید.
4. اگر FFmpeg ندارید: `winget install Gyan.FFmpeg` (یا از <https://www.gyan.dev/ffmpeg/builds/> دانلود و مسیر `ffmpeg.exe` را در تنظیمات بدهید).
5. در برنامه: فایل صوتی ← تعداد گویندگان ← «بررسی آمادگی» ← «شروع رونویسی».

> اگر در صفحهٔ مدل‌ها هیچ‌کدام را تیک نزنید، برنامه نصب می‌شود ولی تا دانلود مدل‌ها رونویسی انجام نمی‌شود. دانلود بعدی از «Models guide» در منوی شروع یا در اولین اجرای رونویسی انجام می‌شود.
>
> فایل `.env` کنار `MinuteMate.exe` برای تنظیمات دستی است (پرووایدر، کلید API، مسیر مدل). با به‌روزرسانی یا حذف برنامه پاک نمی‌شود.

---

## ۲. مدل‌های هوش مصنوعی

حجم نصاب ≈ ۳۲۲ MB است: برنامهٔ دسکتاپ ۱۶۱ MB و موتور ۶۷۹ MB (بدون CUDA). مدل‌ها جداگانه دانلود می‌شوند:

| # | مدل | کاربرد | حجم | الزامی؟ |
| :---: | :--- | :--- | :---: | :--- |
| ۱ | **Whisper Large-v3-Turbo** (CTranslate2) | رونویسی گفتار (ASR) فارسی/انگلیسی | ~۱٫۶ GB | ✅ بله |
| ۲ | **PyAnnote Segmentation 3.0** | تفکیک مرزهای گفتار برای دیاریزیشن | ~۶ MB | ✅ بله |
| ۳ | **WeSpeaker ResNet34 (VoxCeleb)** | امبدینگ صدای گوینده (پیش‌فرض) | ~۲۵ MB | ✅ بله |
| ۴ | **3D-Speaker CAM++ (VoxCeleb)** | امبدینگ گوینده (جایگزین) | ~۲۸ MB | ✅ بله |
| ۵ | **Whisper Large-v3 Persian (int8)** | حالت «دقت بالا» برای فارسی | ~۱٫۵ GB | ⬜ اختیاری |

### ۲.۱. دانلود خودکار (توصیه‌شده)

در اولین «شروع رونویسی» یا با زدن «بررسی آمادگی»، برنامه مدل‌های الزامی را خودش دانلود می‌کند. مدل فارسی اختیاری است و فقط وقتی در تنظیمات حالت «دقت بالا / Persian» را انتخاب کنید لازم می‌شود.

### ۲.۲. دانلود دستی (لینک مستقیم)

**۱) Whisper Large-v3-Turbo** — صفحه: <https://huggingface.co/deepdml/faster-whisper-large-v3-turbo/tree/main>

| فایل | لینک دانلود |
| :--- | :--- |
| `config.json` | <https://huggingface.co/deepdml/faster-whisper-large-v3-turbo/resolve/main/config.json> |
| `tokenizer.json` | <https://huggingface.co/deepdml/faster-whisper-large-v3-turbo/resolve/main/tokenizer.json> |
| `vocabulary.json` | <https://huggingface.co/deepdml/faster-whisper-large-v3-turbo/resolve/main/vocabulary.json> |
| `model.bin` | <https://huggingface.co/deepdml/faster-whisper-large-v3-turbo/resolve/main/model.bin> |

**۲) Whisper Large-v3 Persian int8** (اختیاری) — صفحه: <https://huggingface.co/AmirMohseni/whisper-large-v3-persian-ct2-int8/tree/main>

| فایل | لینک دانلود |
| :--- | :--- |
| `config.json` | <https://huggingface.co/AmirMohseni/whisper-large-v3-persian-ct2-int8/resolve/main/config.json> |
| `tokenizer.json` | <https://huggingface.co/AmirMohseni/whisper-large-v3-persian-ct2-int8/resolve/main/tokenizer.json> |
| `vocabulary.json` | <https://huggingface.co/AmirMohseni/whisper-large-v3-persian-ct2-int8/resolve/main/vocabulary.json> |
| `model.bin` | <https://huggingface.co/AmirMohseni/whisper-large-v3-persian-ct2-int8/resolve/main/model.bin> |

**۳) دیاریزیشن (Sherpa-ONNX)** — صفحهٔ انتشار: <https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models>

| فایل | لینک دانلود |
| :--- | :--- |
| `sherpa-onnx-pyannote-segmentation-3-0.tar.bz2` | <https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2> |
| `wespeaker_en_voxceleb_resnet34_LM.onnx` | <https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx> |
| `3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx` | <https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx> |

### ۲.۳. دانلود با ابزار Hugging Face

```powershell
pip install -U huggingface_hub
hf download deepdml/faster-whisper-large-v3-turbo --local-dir D:\mm-models\whisper\faster-whisper-large-v3-turbo
hf download AmirMohseni/whisper-large-v3-persian-ct2-int8 --local-dir D:\mm-models\whisper\faster-whisper-large-v3-persian-ct2-int8
```

### ۲.۴. محل قرار دادن مدل‌ها

پوشهٔ پیش‌فرض در نسخهٔ نصبی: `<پوشهٔ نصب>\engine\models` (معمولاً `%LOCALAPPDATA%\Programs\MinuteMate\engine\models`).

ساختار دقیق (نام پوشه‌ها را تغییر ندهید):

```text
engine\models\
├─ whisper\
│  ├─ faster-whisper-large-v3-turbo\
│  │  ├─ config.json
│  │  ├─ tokenizer.json
│  │  ├─ vocabulary.json
│  │  └─ model.bin
│  └─ faster-whisper-large-v3-persian-ct2-int8\
│     ├─ config.json
│     ├─ tokenizer.json
│     ├─ vocabulary.json
│     └─ model.bin
└─ speaker\
   ├─ sherpa-onnx-pyannote-segmentation-3-0\
   │  └─ model.onnx          ← از حالت tar.bz2 استخراج شود
   ├─ wespeaker_en_voxceleb_resnet34_LM.onnx
   └─ 3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx
```

اگر مدل‌ها را جای دیگری گذاشتید، یکی از این دو کار را بکنید:

- در `.env`: `MINUTEMATE_MODELS_DIR=D:\mm-models`
- یا در برنامه: تنظیمات ← «پوشهٔ مدل‌ها»

### ۲.۵. بررسی صحت مدل‌ها

```powershell
& "$env:LOCALAPPDATA\Programs\MinuteMate\engine\minutemate-engine.exe" models list
& "$env:LOCALAPPDATA\Programs\MinuteMate\engine\minutemate-engine.exe" models verify
```

اگر همه‌چیز درست باشد: `required models present (turbo + diarization)`. دانلود دستی/آفلاین هم با همین exe ممکن است:

```powershell
& "...\engine\minutemate-engine.exe" models download --models-dir D:\mm-models
& "...\engine\minutemate-engine.exe" models download --group whisper --models-dir D:\mm-models
& "...\engine\minutemate-engine.exe" models download --group diarization --models-dir D:\mm-models
& "...\engine\minutemate-engine.exe" models download --group whisper-fa --models-dir D:\mm-models
```

فایل‌های موجود و سالم دوباره دانلود نمی‌شوند.

### ۲.۶. پشتیبانی GPU (اختیاری)

نصاب **کتابخانه‌های CUDA را همراه ندارد** (حدود ۱ GB صرفه‌جویی). بدون آن‌ها برنامه خودکار روی **CPU** اجرا می‌شود و کامل کار می‌کند. برای استفاده از کارت گرافیک NVIDIA، کتابخانه‌های cuBLAS و cuDNN 9 را در پوشهٔ `engine` نصب کنید:

```powershell
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 --target "$env:LOCALAPPDATA\Programs\MinuteMate\engine"
```

اگر پایتون ندارید: از <https://pypi.org/project/nvidia-cublas-cu12/#files> و <https://pypi.org/project/nvidia-cudnn-cu12/#files> فایل wheel ویندوز (`win_amd64`) را دانلود و با 7-Zip باز کنید؛ پوشهٔ `nvidia` داخل آن را به `<نصب>\engine\nvidia` کپی کنید (ساختار `engine\nvidia\cublas\bin` و `engine\nvidia\cudnn\bin`).

بررسی:

```powershell
& "...\engine\minutemate-engine.exe" preflight --device auto
```

اگر `"cudaAvailable": true` بود و `gpuCount` بزرگ‌تر از صفر، GPU فعال است. در غیر این صورت برنامه بی‌صدا روی CPU می‌ماند (بدون خطا). برای انتخاب دستی: `--device cuda --compute-type float16`.

---

## ۳. تنظیمات پیشنهادی

| موقعیت | دستگاه | Compute | تعداد گوینده | مدل ASR | توضیح |
| :--- | :--- | :--- | :---: | :--- | :--- |
| کارت گرافیک NVIDIA با ۶ GB+ حافظه | `cuda` (یا `auto`) | `float16` | دقیق (مثلاً ۴) | `turbo` | نیازمند نصب اختیاری CUDA (بخش ۲.۶) |
| کارت NVIDIA قدیمی / ۴ GB | `cuda` | `int8_float16` | دقیق | `turbo` | در صورت خطای حافظه به `cpu` برگردد |
| فقط CPU | `cpu` | `int8` | دقیق | `turbo` | حدود ۰٫۳–۰٫۶ برابر سرعت واقعی |
| جلسهٔ فارسی حساس به دقت | `cuda` | `float16` | دقیق | `fa` (دقت بالا) | کندتر؛ نیازمند مدل اختیاری فارسی |
| صدای کم‌باند / تلفنی | — | — | دقیق | Groq ابری | مدل محلی روی این صداها ضعیف است |

**نکات مهم:**

- **تعداد گویندگان** را اگر می‌دانید دقیق بدهید؛ تخمین خودکار (۰) روی جلسات شلوغ خطا دارد.
- **گفتار هم‌پوشان** و صدای سالن، کیفیت دیاریزیشن را کم می‌کند؛ میکروفن نزدیک‌تر بهتر از میکروفن دور است.
- **ضبط با کیفیت**: از OBS Studio (WASAPI loopback برای صدای سیستم) یا Audacity استفاده کنید؛ ضبط با کارت صوتی قدیمی/تلفنی (باند زیر ۱ kHz) نتیجهٔ Whisper را به‌شدت خراب می‌کند.
- **حافظه**: مدل turbo در حالت `float16` حدود ۳ GB VRAM می‌خواهد؛ اگر خطای CUDA out of memory دیدید `int8_float16` یا `cpu/int8` را امتحان کنید.
- **حذف سکوت/نویز**: برنامه خودش تبدیل به 16 kHz mono و فیلتر `highpass=f=60` را انجام می‌دهد؛ پیش‌پردازش دستی لازم نیست.

### ۳.۱. پرووایدر ابری Groq (اختیاری)

برای جلساتی که ضبطشان کیفیت پایین دارد، Groq نتیجهٔ به‌مراتب بهتری می‌دهد.

1. کلید رایگان بگیرید: <https://console.groq.com/keys>
2. در فایل `.env` کنار `MinuteMate.exe` بنویسید (چند کلید را با کاما جدا کنید؛ به‌صورت چرخشی استفاده می‌شوند):

```ini
GROQ_API_KEY=gsk_key1,gsk_key2
```

3. در تنظیمات برنامه، پرووایدر Groq را فعال/انتخاب کنید.

مدل‌ها: `whisper-large-v3-turbo` (پیش‌فرض، سریع) و `whisper-large-v3` (دقیق‌تر).
محدودیت رایگان (۲۰۲۶): حدود ۲٬۰۰۰ درخواست در روز، ۲۸٬۸۰۰ ثانیه صدا در روز، ۲۰ درخواست در دقیقه.
هشدار حریم خصوصی: در این حالت فایل صوتی به سرور Groq ارسال می‌شود؛ برای جلسات محرمانه از حالت محلی استفاده کنید.

---

## ۴. عیب‌یابی

| نشانه | علت / راه‌حل |
| :--- | :--- |
| «موتور پیدا نشد» | `engine\minutemate-engine.exe` باید کنار فایل‌های برنامه باشد؛ دوباره نصب کنید. |
| `model_missing` یا «مدل ناقص» | `models verify` را اجرا کنید؛ فایل ناقص (مثلاً `model.bin` کوچک‌تر از ۱۰۰ MB) را پاک و دوباره دانلود کنید. |
| `ffmpeg_missing` | FFmpeg را نصب یا مسیر کامل آن را در تنظیمات بدهید. |
| خطای CUDA / out of memory | `compute-type` را `int8_float16` یا دستگاه را `cpu` بگذارید. |
| GPU هست ولی از آن استفاده نمی‌شود | کتابخانه‌های CUDA نصب نیستند (بخش ۲.۶)؛ `preflight` را ببینید. |
| رونویسی خیلی کند | مدل `turbo` + `int8` روی CPU؛ یا Groq برای جلسات طولانی. |
| متن پرت یا ناقص | کیفیت ضبط را بررسی کنید؛ حالت «دقت بالا» (`fa`) یا Groq را امتحان کنید. |
| گوینده‌ها جابه‌جا شده‌اند | تعداد گویندگان را دقیق بدهید و در پایان از «نگاشت گویندگان» برای نام‌گذاری استفاده کنید. |
| برنامه باز نمی‌شود | لاگ: `%LOCALAPPDATA%\MinuteMate\logs\` (جدیدترین `minutemate-*.log` یا `crash-*.log`). |

---

## ۵. حریم خصوصی

- در حالت محلی، هیچ داده‌ای از دستگاه خارج نمی‌شود؛ مدل‌ها فقط یک‌بار دانلود می‌شوند.
- جلسات و خروجی‌ها در پوشهٔ جلسات (پیش‌فرض `%LOCALAPPDATA%\MinuteMate`) می‌مانند و با حذف برنامه پاک نمی‌شوند.
- حالت Groq اختیاری است و فقط صدا را به سرور Groq می‌فرستد.
- کلیدهای API فقط در `.env` یا تنظیمات محلی ذخیره می‌شوند.

---

## ۶. مرجع سریع فایل‌ها

| مسیر | محتوا |
| :--- | :--- |
| `<نصب>\MinuteMate.exe` | برنامهٔ دسکتاپ |
| `<نصب>\.env` | تنظیمات محیطی و کلیدهای API (دست‌نخورده با به‌روزرسانی) |
| `<نصب>\engine\` | موتور پایتونی بسته‌بندی‌شده + `models\` |
| `%LOCALAPPDATA%\MinuteMate\logs\` | لاگ برنامه |
| `%LOCALAPPDATA%\MinuteMate\settings.json` | تنظیمات UI |
| `%LOCALAPPDATA%\MinuteMate\` (یا مسیر انتخابی) | جلسات و خروجی‌ها |
