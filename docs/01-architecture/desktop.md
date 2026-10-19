# معماری اپ دسکتاپ (Desktop)

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| در جریان (M1) | 1405-07-27 | Desktop |

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
| `MinuteMate.EngineClient/EngineLocator.cs` | ترتیب جست‌وجو: `ExecutablePath` → `engine/minutemate-engine(.exe)` کنار برنامه → `python` (از `PythonPath` یا `PATH`) با ماژول `PythonModule`؛ حل پوشهٔ کاری با یافتن `engine/pyproject.toml` |
| `MinuteMate.EngineClient/EngineProcessRunner.cs` | `ProcessStartInfo` با stdin/stdout/stderr UTF-8، ارسال job، خواندن NDJSON خط‌به‌خط، `Kill(entireProcessTree)` روی لغو، تبدیل stderr به رویداد `log` |
| `MinuteMate.App/ViewModels/MainWindowViewModel.cs` | وضعیت موتور، انتخاب فایل صوتی، باز کردن پوشهٔ داده |
| `MinuteMate.App/Services/FileDialogService.cs` | انتخاب فایل صوتی (OpenFileDialog) |
| `MinuteMate.App/App.xaml.cs` | ساخت `IHost`، تزریق وابستگی‌ها، بارگذاری `appsettings.json` |

## ۳. ترتیب راه‌اندازی

1. `App.OnStartup` ⇒ `Host` ساخته می‌شود، `appsettings.json` بارگذاری و به `EngineClientOptions` نگاشت می‌شود.
2. `EngineLocator.Locate` تلاش می‌کند یک `EngineLaunchSpec` بسازد (`run --job -`).
3. `MainWindowViewModel` وضعیت «آماده/ناقص» را نشان می‌دهد (`IsEngineReady`).
4. هنگام اجرا: `EngineProcessRunner.RunAsync` job را می‌فرستد و رویدادها را به‌ترتیب `IAsyncEnumerable` بیرون می‌دهد.

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
  "Storage": { "OutputDirectory": "" }
}
```

| کلید | معنا |
| :--- | :--- |
| `ExecutablePath` | مسیر sidecar ساخته‌شده (`minutemate-engine.exe`) ⏳ M5 |
| `PythonPath` | مسیر مفسر پایتون (خالی = جست‌وجو در `PATH`) |
| `PythonModule` | نام ماژول اجرایی؛ پیش‌فرض `minutemate` |
| `WorkingDirectory` | پوشهٔ کاری پروسه (خالی = خودکار از `engine/pyproject.toml`) |

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
| اجرا از UI + پیشرفت/لغو/لاگ زنده | ⏳ M1 |
| صفحهٔ تنظیمات و تاریخچهٔ اجرا | ⏳ M1 |
| نمایش خطاهای موتور با راهنما | ⏳ M1 |

## ۷. ساخت و اجرا

```powershell
dotnet build desktop\MinuteMate.Desktop.sln
dotnet test  desktop\MinuteMate.Desktop.sln
powershell -File desktop\scripts\run.ps1
```
