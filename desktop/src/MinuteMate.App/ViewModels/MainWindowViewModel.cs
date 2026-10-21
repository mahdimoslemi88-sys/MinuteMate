using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MinuteMate.App.Formatting;
using MinuteMate.App.Services;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Contracts;
using MinuteMate.Core.Infrastructure;
using MinuteMate.Core.Models;

namespace MinuteMate.App.ViewModels;

public partial class MainWindowViewModel : ObservableObject
{
    private const int MaxLogEntries = 500;

    private readonly IEngineLocator _engineLocator;
    private readonly IEngineRunner _engineRunner;
    private readonly EngineClientOptions _engineOptions;
    private readonly StorageOptions _storageOptions;
    private readonly MinutesOptions _minutesOptions;
    private readonly IFileDialogService _fileDialogService;
    private readonly ISettingsStore _settingsStore;
    private readonly ISessionCatalog _sessionCatalog;
    private readonly IEnginePreflight _enginePreflight;
    private readonly ISettingsDialogService _settingsDialog;

    private readonly List<string> _artifacts = [];
    private CancellationTokenSource? _jobCancellation;
    private int _sessionGeneration;
    private bool _initialized;

    [ObservableProperty]
    private string _engineStatusTitle = "موتور آماده نیست";

    [ObservableProperty]
    private string _engineStatusDetail = "مسیر موتور را در تنظیمات مشخص کنید.";

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(StartJobCommand))]
    private bool _isEngineReady;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(StartJobCommand))]
    private string? _selectedAudioPath;

    [ObservableProperty]
    private string _selectedAudioName = "فایلی انتخاب نشده";

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(StartJobCommand))]
    private bool _isRunning;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(CancelJobCommand))]
    private bool _isCancelling;

    [ObservableProperty]
    private double _progressValue;

    [ObservableProperty]
    private string _stageText = "آماده";

    [ObservableProperty]
    private string _statusText = "برای شروع، یک فایل صوتی یا تصویری انتخاب کنید.";

    [ObservableProperty]
    private string _etaText = string.Empty;

    [ObservableProperty]
    private bool _hasError;

    [ObservableProperty]
    private string _errorTitle = string.Empty;

    [ObservableProperty]
    private string _errorHint = string.Empty;

    [ObservableProperty]
    private string? _logDirectory;

    [ObservableProperty]
    private bool _enableMinutes;

    [ObservableProperty]
    private string? _title;

    [ObservableProperty]
    private DateTime? _selectedDate = DateTime.Today;

    [ObservableProperty]
    private int _numSpeakers = 4;

    [ObservableProperty]
    private string _selectedDevice = "auto";

    [ObservableProperty]
    private string _selectedComputeType = "auto";

    [ObservableProperty]
    private string _sessionQuery = string.Empty;

    [ObservableProperty]
    private bool _hasSessions;

    [ObservableProperty]
    private string _sessionCountText = "۰";

    [ObservableProperty]
    private string _processedDurationText = "۰:۰۰";

    [ObservableProperty]
    private string _lastSessionText = "—";

    [ObservableProperty]
    private string? _lastOutputPath;

    [ObservableProperty]
    private bool _isPreflightRunning;

    [ObservableProperty]
    private string _preflightText = "بررسی نشده";

    [ObservableProperty]
    private string _preflightDetail = "برای بررسی مدل‌ها و FFmpeg دکمهٔ «بررسی آمادگی» را بزنید.";

    [ObservableProperty]
    private bool? _preflightReady;

    [ObservableProperty]
    private string _versionWarning = string.Empty;

    public MainWindowViewModel(
        IEngineLocator engineLocator,
        IEngineRunner engineRunner,
        EngineClientOptions engineOptions,
        StorageOptions storageOptions,
        IFileDialogService fileDialogService,
        ISettingsStore settingsStore,
        ISessionCatalog sessionCatalog,
        IEnginePreflight enginePreflight,
        ISettingsDialogService settingsDialog,
        MinutesOptions? minutesOptions = null)
    {
        _engineLocator = engineLocator;
        _engineRunner = engineRunner;
        _engineOptions = engineOptions;
        _storageOptions = storageOptions;
        _minutesOptions = minutesOptions ?? new MinutesOptions();
        _enableMinutes = _minutesOptions.Enabled;
        _fileDialogService = fileDialogService;
        _settingsStore = settingsStore;
        _sessionCatalog = sessionCatalog;
        _enginePreflight = enginePreflight;
        _settingsDialog = settingsDialog;

        AppPaths.EnsureCreated();
        RefreshEngineStatus();
    }

    public string DataDirectory => AppPaths.Root;

    public string OutputDirectory => ResolveOutputDirectory();

    public string SessionsRoot => ResolveSessionsRoot();

    public ObservableCollection<LogEntry> LogEntries { get; } = [];

    public ObservableCollection<SessionRow> Sessions { get; } = [];

    public IReadOnlyList<int> SpeakerCounts { get; } = Enumerable.Range(0, 11).ToArray();

    public IReadOnlyList<string> Devices { get; } = ["auto", "cuda", "cpu"];

    public IReadOnlyList<string> ComputeTypes { get; } = ["auto", "float16", "int8", "float32"];

    public IReadOnlyList<string> AsrModels { get; } = ["turbo", "fa"];

    [ObservableProperty]
    private string _selectedAsrModel = "turbo";

    public async Task InitializeAsync()
    {
        if (_initialized)
        {
            return;
        }

        _initialized = true;

        AppSettings settings;
        try
        {
            settings = await _settingsStore.LoadAsync();
        }
        catch (Exception exception)
        {
            settings = new AppSettings();
            AddLog("warning", $"تنظیمات خوانده نشد: {exception.Message}");
        }

        ApplySettings(settings);
        RefreshEngineStatus();
        RefreshSessions();
    }

    partial void OnSelectedAudioPathChanged(string? value)
    {
        SelectedAudioName = string.IsNullOrWhiteSpace(value)
            ? "فایلی انتخاب نشده"
            : Path.GetFileName(value);

        if (!string.IsNullOrWhiteSpace(value) && string.IsNullOrWhiteSpace(Title))
        {
            Title = Path.GetFileNameWithoutExtension(value);
        }
    }

    partial void OnSessionQueryChanged(string value)
    {
        RefreshSessions();
    }

    [RelayCommand]
    private void PickAudio()
    {
        var path = _fileDialogService.PickAudioFile();
        if (!string.IsNullOrWhiteSpace(path))
        {
            SelectedAudioPath = path;
        }
    }

    [RelayCommand]
    private void OpenDataFolder()
    {
        AppPaths.EnsureCreated();
        OpenFolder(AppPaths.Root);
    }

    [RelayCommand]
    private void OpenSessionsFolder()
    {
        var root = ResolveSessionsRoot();
        Directory.CreateDirectory(root);
        OpenFolder(root);
    }

    [RelayCommand]
    private void OpenOutputFolder()
    {
        var directory = ResolveOutputDirectory();
        if (!Directory.Exists(directory))
        {
            Directory.CreateDirectory(directory);
        }

        OpenFolder(directory);
    }

    [RelayCommand]
    private void OpenLogFolder()
    {
        if (!string.IsNullOrWhiteSpace(LogDirectory) && Directory.Exists(LogDirectory))
        {
            OpenFolder(LogDirectory);
        }
    }

    [RelayCommand]
    private void OpenLastOutput()
    {
        if (!string.IsNullOrWhiteSpace(LastOutputPath) && File.Exists(LastOutputPath))
        {
            OpenPath(LastOutputPath!);
        }
    }

    [RelayCommand]
    private void OpenSessionFolder(SessionRow? row)
    {
        if (row is not null)
        {
            OpenFolder(row.Summary.DirectoryPath);
        }
    }

    [RelayCommand]
    private void OpenSessionOutput(SessionRow? row)
    {
        var path = row?.Summary.MinutesPath ?? row?.Summary.TranscriptPath;
        if (!string.IsNullOrWhiteSpace(path) && File.Exists(path))
        {
            OpenPath(path!);
        }
        else if (row is not null)
        {
            OpenFolder(Path.Combine(row.Summary.DirectoryPath, "out"));
        }
    }

    [RelayCommand]
    private void RerunSession(SessionRow? row)
    {
        if (row?.Summary.RawAudioPath is not { } audio || !File.Exists(audio))
        {
            StatusText = "فایل صوتی اصلی این جلسه پیدا نشد.";
            return;
        }

        SelectedAudioPath = audio;
        Title = row.Title;
        StatusText = "برای اجرای مجدد، «شروع پردازش» را بزنید.";
    }

    [RelayCommand]
    private void RefreshSessionsList()
    {
        RefreshSessions();
    }

    [RelayCommand]
    private async Task OpenSettingsAsync()
    {
        var updated = _settingsDialog.Show(CurrentSettings());
        if (updated is null)
        {
            return;
        }

        ApplySettings(updated);
        RefreshEngineStatus();
        RefreshSessions();

        try
        {
            await _settingsStore.SaveAsync(updated);
            AddLog("info", "تنظیمات ذخیره شد.");
        }
        catch (Exception exception)
        {
            HasError = true;
            ErrorTitle = "ذخیرهٔ تنظیمات ناموفق بود.";
            ErrorHint = exception.Message;
        }
    }

    [RelayCommand]
    private async Task CheckPreflightAsync()
    {
        if (IsPreflightRunning)
        {
            return;
        }

        IsPreflightRunning = true;
        PreflightReady = null;
        PreflightText = "در حال بررسی…";
        PreflightDetail = "مدل‌ها، FFmpeg و دستگاه بررسی می‌شوند.";

        try
        {
            var result = await _enginePreflight.RunAsync(
                SelectedDevice,
                SelectedComputeType,
                _storageOptions.ModelsDirectory);

            if (!string.IsNullOrWhiteSpace(result.Error))
            {
                PreflightReady = false;
                PreflightText = "بررسی ناموفق";
                PreflightDetail = result.Error!;
                VersionWarning = string.Empty;
                return;
            }

            var ready = result.ModelsReady && result.Ffmpeg;
            PreflightReady = ready;
            PreflightText = ready ? "آماده" : "ناقص";
            PreflightDetail = BuildPreflightDetail(result);
            VersionWarning = BuildVersionWarning(result.EngineVersion) ?? string.Empty;
        }
        catch (Exception exception)
        {
            PreflightReady = false;
            PreflightText = "بررسی ناموفق";
            PreflightDetail = exception.Message;
            VersionWarning = string.Empty;
        }
        finally
        {
            IsPreflightRunning = false;
        }
    }

    private bool CanStartJob()
    {
        return !IsRunning
            && IsEngineReady
            && !string.IsNullOrWhiteSpace(SelectedAudioPath);
    }

    [RelayCommand(CanExecute = nameof(CanStartJob))]
    private async Task StartJobAsync()
    {
        if (string.IsNullOrWhiteSpace(SelectedAudioPath))
        {
            return;
        }

        var audioPath = SelectedAudioPath!;
        var jobId = Guid.NewGuid().ToString("N");
        var sessionsRoot = ResolveSessionsRoot();
        Directory.CreateDirectory(sessionsRoot);

        LogDirectory = Path.Combine(
            string.IsNullOrWhiteSpace(_engineOptions.LogDirectory) ? AppPaths.Logs : _engineOptions.LogDirectory!,
            jobId);

        ResetForNewRun();

        var job = new EngineJobRequest
        {
            JobId = jobId,
            AudioPath = audioPath,
            OutputDirectory = string.Empty,
            SessionsRoot = sessionsRoot,
            MetricsDirectory = MetricsDirectoryFor(sessionsRoot),
            Stem = Path.GetFileNameWithoutExtension(audioPath),
            Title = string.IsNullOrWhiteSpace(Title)
                ? Path.GetFileNameWithoutExtension(audioPath)
                : Title!.Trim(),
            Date = DateOnly.FromDateTime(SelectedDate ?? DateTime.Today),
            NumSpeakers = NumSpeakers,
            Device = ParseDevice(SelectedDevice),
            ComputeType = string.IsNullOrWhiteSpace(SelectedComputeType) ? "auto" : SelectedComputeType,
            Language = "fa",
            AsrModel = SelectedAsrModel,
            ModelsDir = _storageOptions.ModelsDirectory,
            AutoDownloadModels = true,
            Minutes = EnableMinutes ? BuildMinutesOptions() : null
        };

        using var cancellation = new CancellationTokenSource();
        _jobCancellation = cancellation;
        IsRunning = true;

        try
        {
            await foreach (var engineEvent in _engineRunner.RunAsync(job, cancellation.Token))
            {
                HandleEvent(engineEvent);
            }
        }
        catch (EngineLaunchException exception)
        {
            HasError = true;
            ErrorTitle = exception.Message;
            ErrorHint = "مسیر موتور یا پایتون را در تنظیمات بررسی کنید.";
            StatusText = "اجرای موتور ممکن نشد.";
        }
        catch (Exception exception)
        {
            HasError = true;
            ErrorTitle = exception.Message;
            StatusText = "خطای غیرمنتظره در اجرای موتور.";
        }
        finally
        {
            IsRunning = false;
            IsCancelling = false;
            _jobCancellation = null;
            RefreshSessions();
        }
    }

    private bool CanCancelJob()
    {
        return IsRunning && !IsCancelling;
    }

    [RelayCommand(CanExecute = nameof(CanCancelJob))]
    private void CancelJob()
    {
        IsCancelling = true;
        _jobCancellation?.Cancel();
        StatusText = "درخواست لغو ارسال شد…";
    }

    private void HandleEvent(EngineEvent engineEvent)
    {
        switch (engineEvent.Type)
        {
            case EngineEventType.Started:
                var logPath = ExtractTag(engineEvent.Message, "log");
                if (!string.IsNullOrWhiteSpace(logPath))
                {
                    LogDirectory = logPath;
                }

                AddLog("info", "موتور MinuteMate اجرا شد.");
                break;

            case EngineEventType.Stage:
                HandleStage(engineEvent);
                break;

            case EngineEventType.Log:
                AddLog(engineEvent.Level ?? "info", engineEvent.Message ?? string.Empty);
                break;

            case EngineEventType.Artifact:
                if (!string.IsNullOrWhiteSpace(engineEvent.Path))
                {
                    _artifacts.Add(engineEvent.Path!);
                    AddLog("info", $"خروجی: {engineEvent.Path}");
                }

                break;

            case EngineEventType.Done:
                ProgressValue = 100;
                StageText = "پایان";
                EtaText = string.Empty;
                StatusText = "پردازش با موفقیت کامل شد.";
                LastOutputPath = PickLastOutput(_artifacts);
                AddLog("info", "پردازش کامل شد.");
                break;

            case EngineEventType.Error:
                HandleError(engineEvent);
                break;
        }
    }

    private void HandleStage(EngineEvent engineEvent)
    {
        var label = StageLabel(engineEvent.Stage);

        if (engineEvent.Progress is double progress)
        {
            ProgressValue = Math.Clamp(progress * 100.0, 0, 100);
        }

        StageText = label;
        StatusText = $"در حال {label}…";
        EtaText = engineEvent.EtaSeconds is > 0
            ? $"زمان تقریبی باقی‌مانده: {FormatDuration(engineEvent.EtaSeconds.Value)}"
            : string.Empty;

        if (engineEvent.Status == "done")
        {
            AddLog("info", $"مرحله {label} انجام شد.");
        }
    }

    private void HandleError(EngineEvent engineEvent)
    {
        if (engineEvent.Code == "cancelled")
        {
            StageText = "لغو شد";
            EtaText = string.Empty;
            StatusText = "پردازش توسط کاربر لغو شد.";
            AddLog("warning", "پردازش توسط کاربر لغو شد.");
            return;
        }

        HasError = true;
        ErrorTitle = string.IsNullOrWhiteSpace(engineEvent.Message)
            ? "خطای موتور MinuteMate"
            : engineEvent.Message!;
        ErrorHint = BuildErrorHint(engineEvent);
        StageText = "خطا";
        EtaText = string.Empty;
        StatusText = "پردازش با خطا متوقف شد.";
        AddLog("error", engineEvent.Message ?? "خطای نامشخص");
    }

    private void ResetForNewRun()
    {
        LogEntries.Clear();
        _artifacts.Clear();
        LastOutputPath = null;
        HasError = false;
        ErrorTitle = string.Empty;
        ErrorHint = string.Empty;
        ProgressValue = 0;
        StageText = "در حال شروع…";
        StatusText = "موتور در حال آماده‌سازی است…";
        EtaText = string.Empty;
    }

    private void AddLog(string level, string message)
    {
        LogEntries.Add(new LogEntry(DateTime.Now, level, message));

        while (LogEntries.Count > MaxLogEntries)
        {
            LogEntries.RemoveAt(0);
        }
    }

    private void RefreshSessions()
    {
        var generation = ++_sessionGeneration;
        var root = ResolveSessionsRoot();
        var query = SessionQuery;

        IReadOnlyList<SessionSummary> sessions;
        try
        {
            sessions = string.IsNullOrWhiteSpace(query)
                ? _sessionCatalog.LoadAll(root)
                : _sessionCatalog.Search(root, query);
        }
        catch (Exception exception)
        {
            AddLog("warning", $"خواندن جلسه‌ها ناموفق بود: {exception.Message}");
            sessions = [];
        }

        if (generation != _sessionGeneration)
        {
            return;
        }

        Sessions.Clear();
        foreach (var session in sessions)
        {
            Sessions.Add(new SessionRow(session));
        }

        HasSessions = Sessions.Count > 0;
        SessionCountText = PersianText.Number(Sessions.Count);
        ProcessedDurationText = PersianText.Duration(sessions.Sum(session => session.DurationSeconds));

        var latest = sessions.FirstOrDefault();
        LastSessionText = latest?.CreatedAt is { } createdAt
            ? PersianText.Date(DateOnly.FromDateTime(createdAt.LocalDateTime))
            : latest?.Date is { } date
                ? PersianText.Date(date)
                : "—";
    }

    private void ApplySettings(AppSettings settings)
    {
        SettingsMapper.Apply(settings, _engineOptions, _storageOptions, _minutesOptions);

        NumSpeakers = settings.NumSpeakers is >= 0 and <= 20 ? settings.NumSpeakers : 4;
        SelectedDevice = string.IsNullOrWhiteSpace(settings.Device) ? "auto" : settings.Device;
        SelectedComputeType = string.IsNullOrWhiteSpace(settings.ComputeType) ? "auto" : settings.ComputeType;
        SelectedAsrModel = string.IsNullOrWhiteSpace(settings.AsrModel) ? "turbo" : settings.AsrModel;
        EnableMinutes = settings.EnableMinutes;

        OnPropertyChanged(nameof(SessionsRoot));
        OnPropertyChanged(nameof(OutputDirectory));
    }

    private AppSettings CurrentSettings()
    {
        return new AppSettings
        {
            PythonPath = _engineOptions.PythonPath,
            EngineExecutablePath = _engineOptions.ExecutablePath,
            OutputDirectory = _storageOptions.OutputDirectory,
            SessionsRoot = _storageOptions.SessionsRoot,
            ModelsDirectory = _storageOptions.ModelsDirectory,
            NumSpeakers = NumSpeakers,
            Device = SelectedDevice,
            ComputeType = SelectedComputeType,
            AsrModel = SelectedAsrModel,
            EnableMinutes = EnableMinutes,
            Theme = "System",
            Language = "fa"
        };
    }

    private string ResolveOutputDirectory()
    {
        return string.IsNullOrWhiteSpace(_storageOptions.OutputDirectory)
            ? AppPaths.Output
            : _storageOptions.OutputDirectory!;
    }

    private string ResolveSessionsRoot()
    {
        return string.IsNullOrWhiteSpace(_storageOptions.SessionsRoot)
            ? Path.Combine(AppPaths.Root, "sessions")
            : _storageOptions.SessionsRoot!;
    }

    private MinutesOptions BuildMinutesOptions()
    {
        var options = _minutesOptions;
        return new MinutesOptions
        {
            Enabled = true,
            Provider = options.Provider,
            BaseUrl = options.BaseUrl,
            Model = options.Model,
            ApiKeyEnv = options.ApiKeyEnv,
            Temperature = options.Temperature,
            MaxOutputTokens = options.MaxOutputTokens,
            TimeoutSeconds = options.TimeoutSeconds,
            ChunkSeconds = options.ChunkSeconds,
            Language = options.Language,
            Template = options.Template,
            IncludeActionItems = options.IncludeActionItems,
            Redact = options.Redact
        };
    }

    private void RefreshEngineStatus()
    {
        var launch = _engineLocator.Locate(_engineOptions);
        var configured = !string.IsNullOrWhiteSpace(_engineOptions.ExecutablePath)
            || !string.IsNullOrWhiteSpace(_engineOptions.PythonPath);
        var sidecar = launch?.Kind == "engine";

        IsEngineReady = launch is not null && (sidecar || configured);

        if (launch is null)
        {
            EngineStatusTitle = "موتور آماده نیست";
            EngineStatusDetail = "فایل اجرایی موتور یا مسیر پایتون را در تنظیمات مشخص کنید.";
            return;
        }

        if (IsEngineReady)
        {
            EngineStatusTitle = "موتور آماده است";
            EngineStatusDetail = $"{launch.Kind} · {Path.GetFileName(launch.FileName)}";
            return;
        }

        EngineStatusTitle = "موتور شناسایی نشد";
        EngineStatusDetail = "پایتون پیدا شد، اما موتور MinuteMate هنوز ساخته نشده است.";
    }

    private static string BuildPreflightDetail(PreflightResult result)
    {
        var parts = new List<string>
        {
            $"دستگاه: {result.Device} ({result.ComputeType})"
        };

        if (!string.IsNullOrWhiteSpace(result.EngineVersion))
        {
            parts.Add($"نسخهٔ موتور: {result.EngineVersion}");
        }

        if (result.GpuCount > 0)
        {
            parts.Add($"{PersianText.Number(result.GpuCount)} GPU");
        }

        if (result.BatchSize > 0)
        {
            parts.Add($"batch: {PersianText.Number(result.BatchSize)}");
        }

        parts.Add(result.Ffmpeg ? "FFmpeg موجود است" : "FFmpeg پیدا نشد");

        if (result.MissingModels.Count > 0)
        {
            parts.Add($"مدل‌های ناقص: {string.Join("، ", result.MissingModels.Take(3))}");
        }
        else if (result.ModelsReady)
        {
            parts.Add("همهٔ مدل‌ها موجودند");
        }

        if (!string.IsNullOrWhiteSpace(result.FfmpegError))
        {
            parts.Add(result.FfmpegError!);
        }

        return string.Join(" · ", parts);
    }

    private static string? MetricsDirectoryFor(string sessionsRoot)
    {
        if (string.IsNullOrWhiteSpace(sessionsRoot))
        {
            return null;
        }

        var parent = Path.GetDirectoryName(Path.GetFullPath(sessionsRoot));
        return string.IsNullOrWhiteSpace(parent) ? null : Path.Combine(parent, "metrics");
    }

    private static string? BuildVersionWarning(string? engineVersion)
    {
        if (string.IsNullOrWhiteSpace(engineVersion) || !Version.TryParse(engineVersion, out var engine))
        {
            return null;
        }

        var desktop = typeof(MainWindowViewModel).Assembly.GetName().Version ?? new Version(0, 0, 0);
        if (engine.Major == desktop.Major && engine.Minor == desktop.Minor)
        {
            return null;
        }

        return $"نسخهٔ موتور ({engineVersion}) با دسکتاپ ({desktop.ToString(3)}) هم‌خوان نیست؛ ممکن است قرارداد job متفاوت باشد.";
    }

    private static ComputeDevice ParseDevice(string value)
    {
        return Enum.TryParse<ComputeDevice>(value, true, out var device) ? device : ComputeDevice.Auto;
    }

    private static string? PickLastOutput(IReadOnlyList<string> artifacts)
    {
        string[] preference =
        [
            "03_official_meeting_minutes.md",
            "02_diarized_cleaned_transcript.md",
            "02_diarized_cleaned_transcript.txt",
            "01_raw_transcript.txt"
        ];

        foreach (var kind in preference)
        {
            var match = artifacts.LastOrDefault(path =>
                string.Equals(Path.GetFileName(path), kind, StringComparison.OrdinalIgnoreCase));
            if (match is not null)
            {
                return match;
            }
        }

        return artifacts.LastOrDefault();
    }

    private static void OpenFolder(string path)
    {
        if (!Directory.Exists(path))
        {
            Directory.CreateDirectory(path);
        }

        OpenPath(path);
    }

    private static void OpenPath(string path)
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = path,
            UseShellExecute = true
        });
    }

    private static string StageLabel(EngineStage? stage)
    {
        return stage switch
        {
            EngineStage.Models => "دانلود مدل‌ها",
            EngineStage.Preprocess => "پیش‌پردازش صوت",
            EngineStage.Diarization => "تفکیک گویندگان",
            EngineStage.Transcription => "رونویسی گفتار",
            EngineStage.Merge => "ادغام و پالایش",
            EngineStage.Export => "تولید خروجی",
            EngineStage.Minutes => "تولید صورت‌جلسه",
            _ => "در حال پردازش"
        };
    }

    private static string FormatDuration(double seconds)
    {
        var span = TimeSpan.FromSeconds(seconds);
        return span.TotalHours >= 1
            ? $"{(int)span.TotalHours}:{span.Minutes:00}:{span.Seconds:00}"
            : $"{span.Minutes:00}:{span.Seconds:00}";
    }

    private static string BuildErrorHint(EngineEvent engineEvent)
    {
        var parts = new List<string>();

        if (!string.IsNullOrWhiteSpace(engineEvent.Code))
        {
            parts.Add($"کد خطا: {engineEvent.Code}");
        }

        if (!string.IsNullOrWhiteSpace(engineEvent.Hint))
        {
            parts.Add(engineEvent.Hint!);
        }

        return string.Join(Environment.NewLine, parts);
    }

    private static string? ExtractTag(string? message, string key)
    {
        if (string.IsNullOrWhiteSpace(message))
        {
            return null;
        }

        var token = key + "=";
        var index = message.IndexOf(token, StringComparison.OrdinalIgnoreCase);
        if (index < 0)
        {
            return null;
        }

        var start = index + token.Length;
        var end = message.IndexOf(';', start);
        var value = end < 0 ? message[start..] : message[start..end];
        return value.Trim();
    }
}
