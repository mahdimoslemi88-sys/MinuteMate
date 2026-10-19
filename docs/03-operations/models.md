# مدل‌ها

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال | 1405-07-27 | Ops |

منبع حقیقت: `engine/minutemate/models/registry.py` — هر مدل جدید فقط از این‌جا اضافه می‌شود.

## ۱. فهرست

| گروه | فایل نسبی | حجم تقریبی | حداقل حجم قابل‌قبول | منبع | لایسنس/نکته |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `whisper` | `whisper/faster-whisper-large-v3-turbo/model.bin` | ~1.5 GB | 100 MB | HuggingFace `deepdml/faster-whisper-large-v3-turbo` | باید لایسنس مدل مرجع (Whisper: MIT) و بازتوزیع `deepdml` بررسی شود |
| `whisper` | `whisper/faster-whisper-large-v3-turbo/{config,tokenizer,vocabulary}.json` | ~چند MB | 1 KB | همان | — |
| `diarization` | `speaker/sherpa-onnx-pyannote-segmentation-3-0/model.onnx` | ~6 MB | 1 MB | GitHub releases `k2-fsa/sherpa-onnx` (آرشیو `tar.bz2`) | مدل PyAnnote 3.0 (MIT) |
| `diarization` | `speaker/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx` | ~28 MB | 1 MB | همان | 3D-Speaker (Apache-2.0) |
| `diarization` | `speaker/wespeaker_en_voxceleb_resnet34_LM.onnx` | ~25 MB | 1 MB | همان | WeSpeaker (Apache-2.0) |

> تست‌های بازبینی، وجود **و** حداقل حجم را بررسی می‌کنند؛ فایل ناقص به‌عنوان «missing» گزارش می‌شود.

## ۲. ترتیب حل مسیر

```
--models-dir / job.modelsDir
      ↓ اگر نبود
MINUTEMATE_MODELS_DIR
      ↓ اگر نبود
<project_root>/models        # ریشه با جست‌وجوی pyproject.toml به بالا پیدا می‌شود
```

`models/` می‌تواند پوشهٔ واقعی، **junction** یا symbolic link باشد:

```powershell
New-Item -ItemType Junction -Path "models" -Target "C:\existing\models"
```

## ۳. فرمان‌ها

```powershell
python -m minutemate models list                    # تعریف‌شده‌ها + مسیر نسبی
python -m minutemate models verify                  # وضعیت موجود/ناقص (کد خروج ۱ اگر ناقص)
python -m minutemate models download --type whisper --models-dir D:\models
python -m minutemate models download --type all --force
```

## ۴. ساختار پوشهٔ مدل‌ها

```
models/
├── whisper/
│   └── faster-whisper-large-v3-turbo/
│       ├── config.json
│       ├── tokenizer.json
│       ├── vocabulary.json
│       └── model.bin
└── speaker/
    ├── sherpa-onnx-pyannote-segmentation-3-0/
    │   └── model.onnx
    ├── 3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx
    └── wespeaker_en_voxceleb_resnet34_LM.onnx
```

## ۵. افزودن مدل جدید

1. یک `ModelFile(rel_path, url, min_bytes, sha256=None, archive=False)` به گروه مناسب در `registry.py` اضافه کن.
2. اگر آرشیو قابل‌استخراج است، `archive=True` بگذار (استخراج `tar.bz2` پشتیبانی می‌شود).
3. کد مصرف‌کننده را در `registry.resolve()` و در مرحلهٔ مربوطه به‌روز کن.
4. مستندات این صفحه را کامل کن (جدول + لایسنس).
5. `python -m minutemate models verify` و یک اجرای `smoke_job` بگیر.

## ۶. استفادهٔ مجدد از مدل‌های موجود

برای پرهیز از دانلود دوبارهٔ ۱.۶GB، `models/` این پروژه به پوشهٔ مدل‌های پروژهٔ خواهر وصل شده است. هیچ فایلی کپی نشده و حذف این پوشه در ریپوی خواهر، این پروژه را نمی‌شکند (فقط دوباره باید مسیر داده شود).

## ۷. به‌روزرسانی مدل‌ها

- **Whisper:** مسیر `WHISPER_DIR` را تغییر بده و فایل‌ها را دانلود کن؛ `--beam-size` را در بنچمارک بررسی کن (`docs/05-quality/evaluation.md`).
- **Diarization:** مدل‌های جدید segmentation/embedding را به همان گروه اضافه کن و A/B روی بنچمارک بگیر؛ DER را قبل/بعد ثبت کن.
