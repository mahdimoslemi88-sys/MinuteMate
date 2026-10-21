# قرارداد رفتاری اجراکنندهٔ موتور (EngineProcessRunner)

| وضعیت | آخرین به‌روزرسانی | مالک |
| :--- | :--- | :--- |
| پیاده‌شده (M1a) | 1405-07-28 | Desktop / Contracts |

این سند رفتار `desktop/src/MinuteMate.EngineClient/EngineProcessRunner.cs` را برای M1a تثبیت می‌کند. هدف: لاگ زنده، بدون deadlock، لغو قابل‌اتکا و خطای قابل‌فهم. قرارداد job/NDJSON در `job-json.md` و `ndjson-events.md` است و این سند آن را تغییر نمی‌دهد.

## ۱. وضعیت فعلی و شکاف‌ها

| موضوع | اکنون | مشکل |
| :--- | :--- | :--- |
| stderr | `ReadToEndAsync` و انتشار یک‌جا در پایان | کاربر تا پایان اجرا هیچ لاگی نمی‌بیند |
| stdin | نوشتن job و بستن | اگر پروسه زودتر بمیرد، `IOException` مدیریت‌نشده |
| stdout | خط‌به‌خط | خوب؛ ولی سقف طول خط و نویز ندارد |
| لغو | `Kill(entireProcessTree)` فوری | فرصت پاک‌سازی/بستن فایل نیست؛ `yield break` بدون `error` |
| کد خروج | فقط `exit_<code>` | `130` و `2` و «صفر بدون done» تفکیک نمی‌شوند |
| رویداد `started` | ساختگی با `JobId` | PID و مسیر لاگ ندارد |
| لاگ خام | نگه‌داری نمی‌شود | دیباگ بعدی سخت است |

## ۲. قرارداد API

```csharp
public interface IEngineRunner
{
    IAsyncEnumerable<EngineEvent> RunAsync(
        EngineJobRequest request,
        CancellationToken cancellationToken = default);
}
```

- `RunAsync` تا پایان پروسه یا لغو، رویدادها را **به‌ترتیب** تولید می‌کند.
- هیچ استثنای مدیریت‌نشده برای خطاهای معمول موتور پرتاب نمی‌شود؛ خطاها به `EngineEvent` با `Type=Error` تبدیل می‌شوند.
- استثنا فقط برای «موتور پیدا نشد» یا «پروسه شروع نشد» مجاز است (`EngineLaunchException`).

## ۳. راه‌اندازی پروسه

```csharp
var startInfo = new ProcessStartInfo
{
    FileName = launch.FileName,
    WorkingDirectory = launch.WorkingDirectory,
    UseShellExecute = false,
    CreateNoWindow = true,
    RedirectStandardInput = true,
    RedirectStandardOutput = true,
    RedirectStandardError = true,
    StandardInputEncoding = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false),
    StandardOutputEncoding = new UTF8Encoding(false),
    StandardErrorEncoding = new UTF8Encoding(false),
};
startInfo.Environment["PYTHONUTF8"] = "1";
startInfo.Environment["PYTHONIOENCODING"] = "utf-8";
```

- `ArgumentList` استفاده شود (نه رشتهٔ دستور) تا مسیرهای دارای فاصله/یونیکد سالم بمانند.
- پوشهٔ لاگ: `%LOCALAPPDATA%\MinuteMate\logs\<jobId>\` (یا `AppPaths.Logs`). فایل‌ها: `stdout.ndjson`, `stderr.log`.
- اولین رویداد بعد از `Start()`:

```json
{ "type": "started", "message": "pid=12345; log=...\\logs\\<jobId>" }
```

## ۴. نوشتن job

1. `JsonSerializer.Serialize(request, JsonDefaults.Engine)`.
2. نوشتن در stdin با UTF-8 بدون BOM و `FlushAsync`.
3. بستن stdin.
4. `IOException`/`ObjectDisposedException` ⇒ یک `error` با `code=input_pipe_closed` و سپس ادامهٔ خواندن stdout/stderr تا خروج پروسه (شاید موتور خطای خودش را فرستاده باشد).
5. job هرگز لاگ نشود (ممکن است مسیر/نام حساس داشته باشد)؛ فقط `jobId` و تعداد بایت.

## ۵. خواندن stdout

```csharp
while (!cancellationToken.IsCancellationRequested)
{
    var line = await process.StandardOutput.ReadLineAsync(cancellationToken);
    if (line is null) break;
    if (string.IsNullOrWhiteSpace(line)) continue;
    if (line.Length > MaxLineLength) { emit log(level=warning, truncated); line = line[..MaxLineLength]; }
    var parsed = Parse(line);
    yield return parsed ?? new EngineEvent { Type = Log, Level = "debug", Message = line };
}
```

- `MaxLineLength` پیشنهادی: `64 * 1024` کاراکتر.
- خط نامعتبر هرگز باعث توقف نمی‌شود.
- خط خام stdout در فایل `stdout.ndjson` نوشته شود (بدون تغییر) برای بازپخش.
- رویدادهای `artifact` بلافاصله به UI برسند؛ مسیرها مطلق‌اند.
- اگر `done` دید، آن را نگه دار؛ بعد از خروج، نبودِ آن با کد ۰ ⇒ `error(code=exit_0_without_done)`.

## ۶. خواندن stderr (لاگ زنده)

- stderr **هم‌زمان** با stdout و خط‌به‌خط خوانده شود؛ هرگز `ReadToEnd` قبل از پایان.
- هر خط به یک `EngineEvent { Type=Log, Level="info", Message=line }` تبدیل شود.
- throttle: حداکثر ۱۰ رویداد در ثانیه؛ خطوط اضافی در یک پیام تجمیعی (`… (+N lines)`) ادغام شوند تا UI سیل نشود.
- اگر خط با `ERROR`/`Traceback` شروع شد ⇒ `Level="error"`؛ اگر `WARNING` ⇒ `Level="warning"`.
- ۱۰۰ خط آخر همیشه در حافظه نگه داشته شود (`stderrTail`) برای ضمیمه به خطا.
- فایل `stderr.log` همزمان نوشته شود (flush دوره‌ای).

## ۷. لغو

```csharp
using var registration = cancellationToken.Register(() => RequestCancel(process));
```

1. درخواست لغو ⇒ تلاش برای خروج نرم: بستن stdin (اگر باز است) و ارسال `Ctrl+C`/`SIGINT` در صورت امکان؛ در ویندوز فعلی موتور کانال لغو مستقل ندارد، پس:
2. مهلت ۳ ثانیه برای خروج؛ سپس `Kill(entireProcessTree: true)`.
3. `WaitForExitAsync` با مهلت ۵ ثانیه؛ در نهایت `Dispose`.
4. خروجی: یک `log` با `message="cancelled by user"` و سپس `error` با `code=cancelled` (اگر موتور خودش `done`/`error` نداده باشد). UI می‌تواند این را به‌عنوان لغو نمایش دهد، نه شکست.
5. هیچ پروسهٔ فرزندی (ffmpeg/پایتون) باقی نماند؛ تست با پروسهٔ fake که فرزند می‌سازد.

> نکته: `CancellationToken` نباید به `ReadLineAsync` داده شود و هم‌زمان `Kill` شود؛ ابتدا kill، سپس خواندن تا EOF با توکن `CancellationToken.None` و مهلت. در غیر این صورت ممکن است `OperationCanceledException` جای `error` را بگیرد.

## ۸. نگاشت کد خروج

| کد | رفتار |
| :---: | :--- |
| `0` + `done` | پایان موفق؛ هیچ رویداد اضافه‌ای لازم نیست |
| `0` بدون `done` | `error(code=exit_0_without_done, hint=stderrTail)` |
| `1` + `error` | همان `error` موتور عبور کند (بدون تکرار) |
| `1` بدون `error` | `error(code=engine_error, message=stderrTail)` |
| `2` | `error(code=input_error, message=stderrTail)` |
| `130` | `error(code=cancelled)` |
| سایر | `error(code=exit_<code>, message=stderrTail)` |

- در همهٔ خطاها `hint` شامل ۱۰ خط آخر stderr و مسیر `stderr.log` باشد.
- اگر `sawError=true`، رویداد خطای مصنوعی تولید نشود.

## ۹. چرخهٔ عمر و منابع

- `using var process`؛ پس از `WaitForExit`، `ExitCode` خوانده شود.
- `StandardInput/Output/Error` پس از پایان dispose شوند.
- حداکثر یک اجرا برای هر `jobId`؛ اجرای هم‌زمان جدید باید `InvalidOperationException` یا `error(code=already_running)` بدهد.
- فایل‌های لاگ در پایان flush و بسته شوند.
- رویدادهای `artifact` مسیرهای ناموجود را گزارش نکنند؛ در صورت نبود، `log(level=warning)`.

## ۱۰. تست‌های لازم

1. **fake engine** که ۳ خط stderr با تأخیر می‌نویسد ⇒ رویدادهای log باید قبل از پایان برسند.
2. **stdout نویز** (خط غیر JSON) ⇒ `log(debug)` و ادامه.
3. **کد خروج ۱ بدون error** ⇒ `error(code=engine_error)`.
4. **کد خروج ۲** ⇒ `error(code=input_error)`.
5. **لغو** در میانهٔ اجرا ⇒ پروسه/فرزندها کشته شوند، `error(code=cancelled)`، بدون orphan.
6. **stdin بسته‌شده** ⇒ `error(code=input_pipe_closed)` و ادامهٔ خواندن.
7. **UTF-8 فارسی** در stdout/stderr ⇒ بدون `?`.
8. **خط بسیار بلند** ⇒ truncate + warning.
9. **done بدون artifact** ⇒ موفق؛ UI نباید فرض کند artifact هست.

## ۱۱. تغییرات UI مرتبط (M1a)

- دکمهٔ «شروع» job می‌سازد (`jobId=Guid.NewGuid():N`، مسیر خروجی از `Storage.OutputDirectory`).
- نمایش مرحله/درصد/ETA از رویداد `stage`.
- پنجرهٔ لاگ زنده از `log`؛ خطا با `code` و `hint` و دکمهٔ «باز کردن پوشهٔ لاگ».
- «لغو» توکن را cancel می‌کند؛ تا دریافت `cancelled` دکمه غیرفعال بماند.
- پس از `done`، artifactها با «باز کردن پوشهٔ خروجی» قابل دسترسی باشند.

## ۱۲. سازگاری

- افزودن `hint`/`path`/`durationSeconds` به `EngineEvent` قبلاً انجام شده؛ تغییر جدید قرارداد NDJSON لازم نیست.
- اگر `error(code=cancelled)` اضافه شود، C# و `events.py` هم‌زمان به‌روزرسانی شوند (در حال حاضر `cancelled` در جدول خطاهای سند NDJSON هست).

## ۱۳. وضعیت پیاده‌سازی

| بخش | وضعیت |
| :--- | :--- |
| راه‌اندازی پروسه + `started` با PID/مسیر لاگ | ✅ |
| نوشتن job + `input_pipe_closed` | ✅ |
| خواندن stdout خط‌به‌خط + truncate + لاگ `stdout.ndjson` | ✅ |
| stderr زنده + throttle + `stderrTail` + لاگ `stderr.log` | ✅ |
| لغو نرم (۳ ثانیه) سپس `Kill(entireProcessTree)` | ✅ |
| نگاشت کد خروج (۰/۱/۲/۱۳۰/سایر) | ✅ |
| محافظ `already_running` برای هر `jobId` | ✅ |
| تغییرات UI بخش ۱۱ | ✅ |

تست‌ها:
- `desktop/tests/MinuteMate.EngineClient.Tests/EngineProcessRunnerTests.cs` (۹ تست با موتور fake مبتنی بر PowerShell).
- `desktop/tests/MinuteMate.App.Tests/MainWindowViewModelTests.cs` (۵ تست برای نگاشت رویداد به وضعیت UI).

تنظیمات زمان‌بندی از طریق `EngineClientOptions` قابل تغییر است.
