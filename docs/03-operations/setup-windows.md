# راه‌اندازی روی ویندوز

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| فعال | 1405-07-27 | Ops |

## ۱. پیش‌نیازها

| مورد | نسخه | بررسی | نصب |
| :--- | :--- | :--- | :--- |
| Python | 3.10+ (تست‌شده 3.14) | `python --version` | python.org |
| FFmpeg | 6+ | `ffmpeg -version` | `winget install Gyan.FFmpeg` |
| .NET SDK | 8.0 | `dotnet --version` | `winget install Microsoft.DotNet.SDK.8` |
| Git | هر نسخه | `git --version` | `winget install Git.Git` |
| CUDA (اختیاری) | 12.x | `nvidia-smi` | درایور NVIDIA |

## ۲. نصب موتور

```powershell
# از ریشهٔ پروژه
python -m pip install --upgrade pip
python -m pip install -r engine\requirements.txt          # CPU
python -m pip install -r engine\requirements.txt "nvidia-cublas-cu12" "nvidia-cuda-nvrtc-cu12"   # GPU

# یا نصب بستهٔ موتور (ساخت entry point `minutemate`)
python -m pip install -e engine
python -m pip install -e "engine[gpu]"      # با وابستگی‌های CUDA
```

> در این پروژه اجرای مستقیم `python -m minutemate` از داخل `engine/` کافی است؛ نصب اختیاری است.

## ۳. مدل‌ها

```powershell
python -m minutemate models verify        # چه چیزی موجود است؟
python -m minutemate models download --type all    # دانلود مدل‌های نبوده
```

اگر مدل‌ها جای دیگری هستند، دو راه:

```powershell
# ۱) پوشهٔ کنار پروژه را به مدل‌های موجود وصل کن
New-Item -ItemType Junction -Path "models" -Target "C:\path\to\existing\models"

# ۲) یا متغیر محیطی
$env:MINUTEMATE_MODELS_DIR = "D:\models"
```

جزئیات مدل‌ها: [`models.md`](./models.md).

## ۴. پیش‌بررسی

```powershell
python -m minutemate --version
python -m minutemate preflight
# خروجی JSON: engineVersion, modelsDir, modelsReady, missingModels, ffmpeg, device, computeType, gpuCount, cudaAvailable
```

اگر `modelsReady=false` است، فهرست `missingModels` را ببین؛ اگر `ffmpeg=null` است، FFmpeg روی `PATH` نیست (یا با `--ffmpeg <path>` مسیر بده). اگر نسخهٔ موتور با دسکتاپ (`desktop/Directory.Build.props` → `Version`) در major/minor یکی نباشد، UI هشدار می‌دهد.

## ۵. اولین اجرا

```powershell
python -m minutemate run .\sample.mp3 --out-dir output --stem sample --num-speakers 2 --device cpu --compute-type int8
```

سپس خروجی‌ها را در `output\` ببین (فهرست کامل: [`../02-contracts/artifacts.md`](../02-contracts/artifacts.md)).

## ۶. اپ دسکتاپ

```powershell
dotnet build desktop\MinuteMate.Desktop.sln
dotnet test  desktop\MinuteMate.Desktop.sln
powershell -ExecutionPolicy Bypass -File desktop\scripts\run.ps1
```

| تنظیم | فایل | نکته |
| :--- | :--- | :--- |
| مسیر پایتون/موتور | `desktop\src\MinuteMate.App\appsettings.json` یا صفحهٔ تنظیمات | `Engine.PythonPath`, `Engine.ExecutablePath`, `Engine.PythonModule` |
| پوشهٔ جلسه‌ها/مدل‌ها | صفحهٔ تنظیمات (ذخیره در `settings.json`) | `Storage.SessionsRoot`, `Storage.ModelsDirectory` |
| پیش‌فرض‌های اجرا | صفحهٔ تنظیمات | تعداد گویندگان، دستگاه، نوع محاسبه، فعال‌بودن صورت‌جلسه |
| ریشهٔ دادهٔ اپ | `MINUTEMATE_DATA_DIR` | پیش‌فرض `%LOCALAPPDATA%\MinuteMate` |

`settings.json` در `%LOCALAPPDATA%\MinuteMate\settings.json` ذخیره می‌شود و بر `appsettings.json` مقدم است؛ مقادیر خالی آن، مقدار `appsettings.json` را پاک نمی‌کنند.

## ۷. متغیرهای محیطی

| متغیر | مصرف‌کننده | معنا |
| :--- | :--- | :--- |
| `MINUTEMATE_MODELS_DIR` | موتور | مسیر پوشهٔ مدل‌ها |
| `MINUTEMATE_LLM_API_KEY` | موتور (مرحلهٔ `minutes`) | کلید سرویس LLM؛ نام قابل‌تغییر با `minutes.apiKeyEnv`. کلید هرگز در job/لاگ نیست |
| `MINUTEMATE_DATA_DIR` | دسکتاپ | ریشهٔ دادهٔ اپ (models/projects/logs/output/settings.json) |
| `MINUTEMATE_SMOKE` | هوک‌های توسعه | `0` = خاموش‌کردن تست دود خودکار |
| `MINUTEMATE_DOTNET` | هوک‌های توسعه | `0` = خاموش‌کردن بیلد خودکار C# |

## ۸. چک‌لیست سلامت نصب

- [ ] `python -m minutemate preflight` با `modelsReady=true` و `ffmpeg` غیر‌null
- [ ] `python -m pytest -q` در `engine/` سبز
- [ ] `python scripts\smoke_job.py <audio> --num-speakers 2` کد خروج ۰ و رویداد `done`
- [ ] `dotnet build desktop\MinuteMate.Desktop.sln` بدون خطا
- [ ] اپ دسکتاپ وضعیت «موتور آماده است» نشان می‌دهد

## ۹. دام‌های رایج ویندوز

1. **کدگذاری کنسول:** موتور خودش `stdin/stdout/stderr` را UTF-8 می‌کند؛ اگر خروجی در ترمینال مخدوش دیدی، `chcp 65001` بزن.
2. **مسیرهای طولانی:** پروژه‌ها را در مسیر کوتاه بگذار (مثلاً `C:\mm`) تا از سقف ۲۶۰ کاراکتر فرار کنی.
3. **CUDA/cuDNN:** نبود `cublas64_12.dll` ⇒ موتور با `cuda_unavailable` برمی‌گردد؛ روی `--device cpu` اجرا کن یا DLLها را نصب کن.
4. **Execution Policy:** برای اسکریپت‌های `desktop\scripts\*.ps1` از `-ExecutionPolicy Bypass` استفاده کن.
5. **آنتی‌ویروس:** پوشهٔ `models/` و `scratch/` را از اسکن زنده مستثنا کن (سرعت دیسک).
