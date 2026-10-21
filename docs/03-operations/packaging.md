# بسته‌بندی و انتشار

## ۱. ساخت sidecar موتور

```powershell
python -m pip install pyinstaller
pwsh -NoProfile -File scripts\build_engine.ps1 -Clean
```

خروجی: `engine/dist/minutemate-engine/minutemate-engine.exe` (onedir). این فایل بدون نصب پایتون اجرا می‌شود؛ مدل‌ها همراه آن نیستند.

- PyInstaller طبق `engine/minutemate-engine.spec` همهٔ بسته‌های بومی (CTranslate2، ONNX Runtime، sherpa-onnx، SciPy، NumPy) و DLLهای `nvidia-cublas`/`nvidia-cuda-nvrtc` را جمع می‌کند.
- بررسی سریع:

```powershell
engine\dist\minutemate-engine\minutemate-engine.exe --version
$env:MINUTEMATE_MODELS_DIR = (Resolve-Path models).Path
engine\dist\minutemate-engine\minutemate-engine.exe preflight --device cpu --compute-type int8
```

## ۲. ساخت نصاب

```powershell
pwsh -NoProfile -File scripts\build_installer.ps1 -SkipEngine
```

این دستور:

1. اپ WPF را self-contained برای `win-x64` منتشر می‌کند.
2. پوشهٔ `engine/dist/minutemate-engine` را در `<publish>\engine` کپی می‌کند تا `EngineLocator` خودکار پیدا کند.
3. اگر Inno Setup 6 نصب باشد (`iscc.exe`)، `desktop\installer\MinuteMate.iss` را کامپایل و `dist\MinuteMate-Setup-0.1.0.exe` را می‌سازد.

نصب‌کننده در حالت per-user کار می‌کند (نیاز به ادمین ندارد)؛ حذف، فقط پوشهٔ برنامه را پاک می‌کند و جلسات در `%LOCALAPPDATA%\MinuteMate` باقی می‌مانند.

### راهنمای مدل‌ها در بسته

نصاب فایل `desktop\installer\README-fa.md` را به‌عنوان `<app>\README-Models.md` نصب می‌کند (میان‌بر «Models guide» در منوی شروع). محتوای آن: معرفی مدل‌ها، حجم، لینک مستقیم دانلود، ساختار پوشهٔ `engine\models`، تنظیمات پیشنهادی GPU/CPU، حالت Groq و عیب‌یابی. نسخهٔ مشابه برای اشتراک‌گذاری در `dist\README-Models.md` هم کپی می‌شود (اسکریپت آن را می‌سازد یا دستی کپی کنید).

### فایل `.env` خام در بسته

نصاب فایل `desktop\installer\env.sample` را به‌عنوان `<app>\.env` نصب می‌کند (بدون کلید؛ فقط قالب و کامنت). این فایل با `onlyifdoesntexist uninsneveruninstall` نصب می‌شود، پس ویرایش کاربر در به‌روزرسانی/حذف برنامه حفظ می‌شود.

ترتیب خواندن `.env` توسط موتور (`minutemate.cli._load_env_files`):

1. مسیر `MINUTEMATE_ENV_FILE`
2. `<app>\engine\.env`
3. `<app>\.env`
4. پوشهٔ جاری
5. `%LOCALAPPDATA%\MinuteMate\.env`

مقدارهای سیستم‌عامل همیشه بر فایل اولویت دارند (بدون override). برای افزودن دستی پرووایدر کافی است `GROQ_API_KEY=...` را در همین فایل پر کنید؛ صفحهٔ «پرووایدرها و مدل‌ها» در تنظیمات هم برای مدیریت از داخل برنامه است.

> اندازهٔ نصاب: بدون مدل‌ها و بدون کتابخانه‌های GPU ساخته می‌شود (≈۳۲۲ MB). کتابخانه‌های CUDA (`nvidia.cublas`/`nvidia.cuda_nvrtc`) و providerهای CUDA/DirectML/TensorRT در `onnxruntime` از `engine/minutemate-engine.spec` حذف شده‌اند؛ کاربر برای GPU اختیاری آن‌ها را در `<app>\engine\nvidia` نصب می‌کند و `env.cuda_device_count()` فقط وقتی CUDA را واقعاً قابل استفاده ببیند `auto` را به cuda می‌برد (وگرنه بی‌صدا cpu).

## ۳. مدل‌ها در نسخهٔ نصب‌شده

- مدل‌ها به‌صورت پیش‌فرض در `<app>\engine\models` یا `MINUTEMATE_MODELS_DIR` جست‌وجو می‌شوند.
- دسکتاپ در اولین اجرا `autoDownloadModels=true` می‌فرستد؛ اگر مدلی ناقص باشد، مرحلهٔ `models` با درصد پیشرفت اجرا و پس از آن جلسه ادامه می‌یابد. دکمهٔ «توقف» همین دانلود را هم لغو می‌کند.
- برای نصب آفلاین، پوشهٔ `models/` را کنار exe کپی یا `MINUTEMATE_MODELS_DIR` را ست کنید.

## ۴. چک‌لیست انتشار

- [x] `python -m pytest -q` سبز (۱۲۷ تست)
- [x] `dotnet test desktop\MinuteMate.Desktop.sln` سبز (۳۴ تست)
- [x] `scripts\smoke_job.py` روی نمونهٔ ۳۰ ثانیه‌ای با sidecar بسته‌بندی‌شده (`--engine`) سبز
- [ ] اجرای sidecar با `--version` و `preflight`
- [x] نصب سایلنت در مسیر آزمایشی + اجرای برنامه + حذف (بدون پایتون) — اجرای جلسهٔ کامل هنوز روی ماشین بدون پایتون آزموده نشده
