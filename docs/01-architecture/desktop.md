# معماری اپ دسکتاپ (Desktop)

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| در جریان (M1 ✅، نصب‌کننده M5) | 1405-07-28 | Desktop |

اپ WPF روی .NET 8 با الگوی MVVM (`CommunityToolkit.Mvvm`) که موتور را به‌صورت sidecar اجرا می‌کند.

## ۱. پروژه‌ها

| پروژه | نقش | وابستگی‌ها |
| :--- | :--- | :--- |
| `MinuteMate.Core` | قراردادها، انتزاع‌ها، زیرساخت (مسیرها، تهی‌سازی JSON، ذخیرهٔ تنظیمات) | هیچ (خالص) |
| `MinuteMate.EngineClient` | `IEngineLocator` (پیدا کردن موتور) و `IEngineRunner` (اجرای پروسه و پارس رویداد) | Core |
| `MinuteMate.App` | UI + ViewModel + دیالوگ فایل + تم | Core, EngineClient |
| `MinuteMate.Core.Tests` | تست‌های قرارداد (نگاشت JSON/رویداد) | Core |

## ۲. لایه‌بندی

```
View (XAML)  ──binding──▶  ViewModel (MVVM Toolkit)  ──▶  IEngineRunner / ISettingsStore / IFileDialogService
                                                                   │
                                                          EngineProcessRunner ──▶ پروسهٔ پایتون
                                                                   │
                                                            JsonDefaults.Engine (camelCase + enum رشته‌ای)
```

| فایل | مسئولیت |
| :--- | :--- |
| `MinuteMate.Core/Contracts/*` | `EngineJobRequest`, `EngineEvent`, `EngineEventType`, `EngineStage`, `ComputeDevice`, `SpeakerProfile`, `EngineClientOptions`, `EngineLaunchSpec` |
| `MinuteMate.Core/Abstractions/*` | `IEngineLocator`, `IEngineRunner`, `ISettingsStore` |
| `MinuteMate.Core/Infrastructure/AppPaths.cs` | ریشهٔ دادهٔ اپ: `%LOCALAPPDATA%\MinuteMate` یا `MINUTEMATE_DATA_DIR`؛ زیرپوشه‌های `models/projects/logs/output` و `settings.json` |
| `MinuteMate.Core/Infrastructure/JsonDefaults.cs` | سیاست نام‌گذاری camelCase + `JsonStringEnumConverter` (Web defaults) |
| `MinuteMate.Core/Infrastructure/JsonSettingsStore.cs` | خواندن/نوشتن `settings.json` |
| `MinuteMate.Core/Infrastructure/SessionCatalog.cs` | خواندن `session.json`ها، مرتب‌سازی، جست‌وجوی عنوان/شناسه/تاریخ/متن (M1b) |
| `MinuteMate.Core/Infrastructure/SettingsMapper.cs` | نگاشت `AppSettings` به `EngineClientOptions`/`StorageOptions`/`MinutesOptions` |
| `MinuteMate.EngineClient/EngineLocator.cs` | ترتیب جست‌وجو: `ExecutablePath` → `engine/minutemate-engine(.exe)` کنار برنامه → `python` (از `PythonPath` یا `PATH`) با ماژول `PythonModule`؛ حل پوشهٔ کاری با یافتن `engine/pyproject.toml` |
| `MinuteMate.EngineClient/EngineProcessRunner.cs` | `ProcessStartInfo` با stdin/stdout/stderr UTF-8، ارسال job، خواندن NDJSON خط‌به‌خط، `Kill(entireProcessTree)` روی لغو، تبدیل stderr به رویداد `log` |
| `MinuteMate.EngineClient/EnginePreflight.cs` | اجرای `preflight` (مستقیم یا `python -m minutemate`) و پارس JSON برای «آماده/ناقص» + `engineVersion` |
| `MinuteMate.App/ViewModels/MainWindowViewModel.cs` | وضعیت موتور، انتخاب فایل، فرم اجرا، تاریخچه/جست‌وجو، اجرای مجدد، پیش‌بررسی، تنظیمات |
| `MinuteMate.App/ViewModels/SettingsViewModel.cs` + `SettingsWindow.xaml` | صفحهٔ تنظیمات و ذخیرهٔ پایدار |
| `MinuteMate.App/Services/FileDialogService.cs` | انتخاب فایل صوتی، فایل اجرایی و پوشه |
| `MinuteMate.App/App.xaml.cs` | ساخت `IHost`، تزریق وابستگی‌ها، بارگذاری `appsettings.json` |

## ۳. ترتیب راه‌اندازی

1. `App.OnStartup` ⇒ `Host` ساخته می‌شود، `appsettings.json` بارگذاری و به گزینه‌ها نگاشت می‌شود.
2. `MainWindow` در `Loaded` تابع `InitializeAsync` را صدا می‌زند: `settings.json` خوانده و روی گزینه‌ها اعمال می‌شود، تاریخچه و وضعیت موتور به‌روز می‌شوند.
3. `EngineLocator.Locate` تلاش می‌کند یک `EngineLaunchSpec` بسازد (`run --job -`).
4. `MainWindowViewModel` وضعیت «آماده/ناقص» را نشان می‌دهد (`IsEngineReady`) و دکمهٔ «بررسی آمادگی» خروجی `preflight` را نمایش می‌دهد.
5. هنگام اجرا: `EngineProcessRunner.RunAsync` job را می‌فرستد و رویدادها را به‌ترتیب `IAsyncEnumerable` بیرون می‌دهد؛ در پایان لیست جلسه‌ها بازخوانی می‌شود.

## ۴. پیکربندی

`appsettings.json` (کنار فایل اجرایی):

```json
{
  "Engine": {
    "ExecutablePath": "",
    "PythonPath": "",
    "PythonModule": "minutemate",
    "WorkingDirectory": ""
  },
  "Storage": {
    "OutputDirectory": "",
    "SessionsRoot": "",
    "ModelsDirectory": ""
  }
}
```

| کلید | معنا |
| :--- | :--- |
| `ExecutablePath` | مسیر sidecar ساخته‌شده (`minutemate-engine.exe`) ⏳ M5 |
| `PythonPath` | مسیر مفسر پایتون (خالی = جست‌وجو در `PATH`) |
| `PythonModule` | نام ماژول اجرایی؛ پیش‌فرض `minutemate` |
| `WorkingDirectory` | پوشهٔ کاری پروسه (خالی = خودکار از `engine/pyproject.toml`) |
| `Storage.SessionsRoot` | ریشهٔ جلسه‌ها (خالی = `<پوشهٔ داده>/sessions`) |
| `Storage.OutputDirectory` | خروجی حالت مسطح قدیمی |
| `Storage.ModelsDirectory` | مسیر مدل‌ها؛ در job به‌صورت `modelsDir` ارسال می‌شود |

`settings.json` (در `%LOCALAPPDATA%\MinuteMate\settings.json`) روی این مقادیر مقدم است: `PythonPath`, `EngineExecutablePath`, `SessionsRoot`, `OutputDirectory`, `ModelsDirectory`, `NumSpeakers`, `Device`, `ComputeType`, `EnableMinutes`. مقادیر خالی، مقدار `appsettings.json` را پاک نمی‌کنند.

## ۵. رفتار پروتکل در سمت C#

- job با `StandardInputEncoding = UTF8(no BOM)` نوشته و سپس stdin بسته می‌شود.
- خطوط `stdout` که JSON معتبر نیستند، به رویداد `log` با `level=debug` تبدیل می‌شوند (تحمل نویز).
- در پایان: کل `stderr` یک‌بار به‌عنوان رویداد `log` منتشر می‌شود؛ اگر کد خروج ≠ ۰ و رویداد `error` دیده نشده باشد، یک `error` با `code=exit_<code>` ساخته می‌شود.
- لغو ⇒ `Kill(entireProcessTree: true)`.

## ۶. وضعیت فعلی و شکاف‌ها

| قابلیت | وضعیت |
| :--- | :--- |
| شناسایی موتور و نمایش آماده‌بودن | ✅ |
| انتخاب فایل صوتی و باز کردن پوشهٔ داده | ✅ |
| اجرا از UI + پیشرفت/لغو/لاگ زنده | ✅ M1a |
| فرم اجرا (عنوان، تاریخ، گویندگان، دستگاه، نوع محاسبه) | ✅ M1b |
| تاریخچهٔ جلسه‌ها + جست‌وجوی کلیدواژه + اجرای مجدد | ✅ M1b |
| صفحهٔ تنظیمات پایدار + پیش‌بررسی آمادگی + هشدار نسخه | ✅ M1b/M5.4 |
| باز کردن فایل/پوشهٔ خروجی | ✅ M1b |
| نصب‌کننده و نسخهٔ بدون پایتون | ⏳ M5 |

## ۷. ساخت و اجرا

```powershell
dotnet build desktop\MinuteMate.Desktop.sln
dotnet test  desktop\MinuteMate.Desktop.sln
powershell -File desktop\scripts\run.ps1
```

