using System.IO;
using System.Runtime.CompilerServices;
using MinuteMate.App.Services;
using MinuteMate.App.ViewModels;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Contracts;
using MinuteMate.Core.Infrastructure;
using MinuteMate.Core.Models;

namespace MinuteMate.App.Tests;

public class MainWindowViewModelTests
{
    [Fact]
    public async Task StartJob_ExposesStageProgressAndEta()
    {
        var viewModel = CreateViewModel(new FakeRunner(
            new EngineEvent { Type = EngineEventType.Started, Message = "pid=1; log=C:\\logs\\job" },
            new EngineEvent
            {
                Type = EngineEventType.Stage,
                Stage = EngineStage.Transcription,
                Status = "running",
                Progress = 0.5,
                EtaSeconds = 120
            }));

        viewModel.SelectedAudioPath = "meeting.mp3";

        await viewModel.StartJobCommand.ExecuteAsync(null);

        Assert.Equal("رونویسی گفتار", viewModel.StageText);
        Assert.Equal(50.0, viewModel.ProgressValue);
        Assert.Contains("02:00", viewModel.EtaText);
        Assert.False(viewModel.IsRunning);
        Assert.False(viewModel.HasError);
    }

    [Fact]
    public async Task StartJob_CompletionMarksDone()
    {
        var viewModel = CreateViewModel(new FakeRunner(
            new EngineEvent
            {
                Type = EngineEventType.Stage,
                Stage = EngineStage.Export,
                Status = "done",
                Progress = 1
            },
            new EngineEvent
            {
                Type = EngineEventType.Artifact,
                Kind = "01_raw_transcript.txt",
                Path = "out\\01_raw_transcript.txt"
            },
            new EngineEvent { Type = EngineEventType.Done }));

        viewModel.SelectedAudioPath = "meeting.mp3";

        await viewModel.StartJobCommand.ExecuteAsync(null);

        Assert.Equal(100.0, viewModel.ProgressValue);
        Assert.Equal("پایان", viewModel.StageText);
        Assert.Contains("موفقیت", viewModel.StatusText);
        Assert.False(viewModel.HasError);
        Assert.Contains(viewModel.LogEntries, entry => entry.Message.Contains("پردازش کامل شد"));
    }

    [Fact]
    public async Task StartJob_ErrorIsSurfaced()
    {
        var viewModel = CreateViewModel(new FakeRunner(
            new EngineEvent
            {
                Type = EngineEventType.Error,
                Code = "input_error",
                Message = "فایل ورودی پیدا نشد",
                Hint = "log=C:\\logs\\job"
            }));

        viewModel.SelectedAudioPath = "meeting.mp3";

        await viewModel.StartJobCommand.ExecuteAsync(null);

        Assert.True(viewModel.HasError);
        Assert.Equal("فایل ورودی پیدا نشد", viewModel.ErrorTitle);
        Assert.Contains("input_error", viewModel.ErrorHint);
        Assert.Equal("خطا", viewModel.StageText);
    }

    [Fact]
    public async Task StartJob_CancellationIsNotAnError()
    {
        var viewModel = CreateViewModel(new FakeRunner(
            new EngineEvent { Type = EngineEventType.Error, Code = "cancelled", Message = "لغو شد" }));

        viewModel.SelectedAudioPath = "meeting.mp3";

        await viewModel.StartJobCommand.ExecuteAsync(null);

        Assert.False(viewModel.HasError);
        Assert.Contains("لغو", viewModel.StatusText);
        Assert.Equal("لغو شد", viewModel.StageText);
    }

    [Fact]
    public void StartJob_IsDisabledWithoutAudioPath()
    {
        var viewModel = CreateViewModel(new FakeRunner());

        Assert.True(viewModel.IsEngineReady);
        Assert.False(viewModel.StartJobCommand.CanExecute(null));

        viewModel.SelectedAudioPath = "meeting.mp3";

        Assert.True(viewModel.StartJobCommand.CanExecute(null));
    }

    [Fact]
    public async Task StartJob_OmitsMinutesWhenDisabled()
    {
        var runner = new FakeRunner(new EngineEvent { Type = EngineEventType.Done });
        var viewModel = CreateViewModel(runner);

        Assert.False(viewModel.EnableMinutes);

        viewModel.SelectedAudioPath = "meeting.mp3";
        await viewModel.StartJobCommand.ExecuteAsync(null);

        Assert.Null(runner.LastRequest!.Minutes);
    }

    [Fact]
    public async Task StartJob_SendsMinutesWhenEnabled()
    {
        var runner = new FakeRunner(new EngineEvent { Type = EngineEventType.Done });
        var viewModel = CreateViewModel(runner, new MinutesOptions
        {
            Provider = "ollama",
            Model = "llama3",
            BaseUrl = "http://127.0.0.1:11434"
        });

        viewModel.SelectedAudioPath = "meeting.mp3";
        viewModel.EnableMinutes = true;
        await viewModel.StartJobCommand.ExecuteAsync(null);

        var minutes = runner.LastRequest!.Minutes;
        Assert.NotNull(minutes);
        Assert.True(minutes!.Enabled);
        Assert.Equal("ollama", minutes.Provider);
        Assert.Equal("llama3", minutes.Model);
    }

    [Fact]
    public async Task StartJob_SendsRunOptionsAndSessionsRoot()
    {
        var runner = new FakeRunner(new EngineEvent { Type = EngineEventType.Done });
        var viewModel = CreateViewModel(runner);

        viewModel.SelectedAudioPath = "C:\\audio\\meeting.mp3";
        viewModel.Title = "جلسهٔ هفتگی";
        viewModel.NumSpeakers = 2;
        viewModel.SelectedDevice = "cpu";
        viewModel.SelectedComputeType = "int8";
        viewModel.SelectedDate = new DateTime(2026, 10, 19);

        await viewModel.StartJobCommand.ExecuteAsync(null);

        var request = runner.LastRequest!;
        Assert.Equal("جلسهٔ هفتگی", request.Title);
        Assert.Equal(2, request.NumSpeakers);
        Assert.Equal(ComputeDevice.Cpu, request.Device);
        Assert.Equal("int8", request.ComputeType);
        Assert.Equal(new DateOnly(2026, 10, 19), request.Date);
        Assert.False(string.IsNullOrWhiteSpace(request.SessionsRoot));
        Assert.True(string.IsNullOrEmpty(request.OutputDirectory));
        Assert.EndsWith("metrics", request.MetricsDirectory);
        Assert.True(request.AutoDownloadModels);
    }

    [Fact]
    public async Task InitializeAsync_LoadsSessionsAndMetrics()
    {
        var root = CreateSessionsRoot();
        WriteSession(root, "2026-10-19-a", "جلسه بودجه", "2026-10-19", 120);
        WriteSession(root, "2026-10-18-b", "جلسه فنی", "2026-10-18", 60);

        var viewModel = CreateViewModel(new FakeRunner(), sessionsRoot: root);
        await viewModel.InitializeAsync();

        Assert.True(viewModel.HasSessions);
        Assert.Equal(2, viewModel.Sessions.Count);
        Assert.Equal("۲", viewModel.SessionCountText);
        Assert.Equal("۲۰۲۶/۱۰/۱۹", viewModel.Sessions[0].DateText);
        Assert.Contains("بودجه", viewModel.Sessions[0].Title);
    }

    [Fact]
    public async Task SessionQuery_FiltersSessions()
    {
        var root = CreateSessionsRoot();
        WriteSession(root, "2026-10-19-a", "جلسه بودجه", "2026-10-19", 120);
        WriteSession(root, "2026-10-18-b", "جلسه فنی", "2026-10-18", 60);

        var viewModel = CreateViewModel(new FakeRunner(), sessionsRoot: root);
        await viewModel.InitializeAsync();

        viewModel.SessionQuery = "بودجه";

        var row = Assert.Single(viewModel.Sessions);
        Assert.Contains("بودجه", row.Title);
    }

    [Fact]
    public async Task RerunSession_SelectsRawAudio()
    {
        var root = CreateSessionsRoot();
        var directory = WriteSession(root, "2026-10-19-a", "جلسه بودجه", "2026-10-19", 120);
        var raw = Path.Combine(directory, "raw", "meeting.mp3");
        Directory.CreateDirectory(Path.GetDirectoryName(raw)!);
        File.WriteAllText(raw, "audio");

        var viewModel = CreateViewModel(new FakeRunner(), sessionsRoot: root);
        await viewModel.InitializeAsync();

        viewModel.RerunSessionCommand.Execute(viewModel.Sessions[0]);

        Assert.Equal(raw, viewModel.SelectedAudioPath);
        Assert.Equal("جلسه بودجه", viewModel.Title);
    }

    [Fact]
    public async Task Done_PicksMinutesArtifactAsLastOutput()
    {
        var viewModel = CreateViewModel(new FakeRunner(
            new EngineEvent
            {
                Type = EngineEventType.Artifact,
                Kind = "01_raw_transcript.txt",
                Path = "C:\\out\\01_raw_transcript.txt"
            },
            new EngineEvent
            {
                Type = EngineEventType.Artifact,
                Kind = "03_official_meeting_minutes.md",
                Path = "C:\\out\\03_official_meeting_minutes.md"
            },
            new EngineEvent { Type = EngineEventType.Done }));

        viewModel.SelectedAudioPath = "meeting.mp3";
        await viewModel.StartJobCommand.ExecuteAsync(null);

        Assert.EndsWith("03_official_meeting_minutes.md", viewModel.LastOutputPath);
    }

    [Fact]
    public async Task OpenSettings_AppliesAndSaves()
    {
        var store = new FakeSettingsStore();
        var dialog = new FakeSettingsDialog(new AppSettings
        {
            NumSpeakers = 2,
            Device = "cpu",
            ComputeType = "int8",
            SessionsRoot = "C:\\sessions"
        });

        var viewModel = CreateViewModel(
            new FakeRunner(),
            settingsStore: store,
            settingsDialog: dialog);

        await viewModel.InitializeAsync();
        await viewModel.OpenSettingsCommand.ExecuteAsync(null);

        Assert.Equal(2, viewModel.NumSpeakers);
        Assert.Equal("cpu", viewModel.SelectedDevice);
        Assert.Equal("C:\\sessions", viewModel.SessionsRoot);
        Assert.NotNull(store.LastSaved);
        Assert.Equal(2, store.LastSaved!.NumSpeakers);
    }

    [Fact]
    public async Task CheckPreflight_WarnsWhenEngineVersionDiffers()
    {
        var viewModel = CreateViewModel(
            new FakeRunner(),
            preflight: new FakePreflight { EngineVersion = "0.2.0" });

        await viewModel.CheckPreflightCommand.ExecuteAsync(null);

        Assert.Contains("0.2.0", viewModel.VersionWarning);
        Assert.Contains("0.1.0", viewModel.VersionWarning);
    }

    [Fact]
    public async Task CheckPreflight_NoWarningWhenVersionsMatch()
    {
        var viewModel = CreateViewModel(
            new FakeRunner(),
            preflight: new FakePreflight { EngineVersion = "0.1.5" });

        await viewModel.CheckPreflightCommand.ExecuteAsync(null);

        Assert.Equal(string.Empty, viewModel.VersionWarning);
        Assert.Contains("0.1.5", viewModel.PreflightDetail);
    }

    private static MainWindowViewModel CreateViewModel(
        IEngineRunner runner,
        MinutesOptions? minutesOptions = null,
        string? sessionsRoot = null,
        ISettingsStore? settingsStore = null,
        ISettingsDialogService? settingsDialog = null,
        IEnginePreflight? preflight = null)
    {
        var directory = Path.Combine(Path.GetTempPath(), "mm-app-tests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);

        var locator = new FakeLocator(new EngineLaunchSpec("engine.exe", ["run"], directory, "engine"));

        return new MainWindowViewModel(
            locator,
            runner,
            new EngineClientOptions(),
            new StorageOptions
            {
                OutputDirectory = directory,
                SessionsRoot = sessionsRoot ?? Path.Combine(directory, "sessions")
            },
            new FakeFileDialogService(),
            settingsStore ?? new FakeSettingsStore(),
            new SessionCatalog(),
            preflight ?? new FakePreflight(),
            settingsDialog ?? new FakeSettingsDialog(null),
            minutesOptions);
    }

    private static string CreateSessionsRoot()
    {
        var root = Path.Combine(Path.GetTempPath(), "mm-app-sessions", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        return root;
    }

    private static string WriteSession(
        string root,
        string id,
        string title,
        string date,
        double durationSeconds)
    {
        var directory = Path.Combine(root, id);
        Directory.CreateDirectory(directory);

        var manifest = $$"""
            {
              "schemaVersion": 1,
              "id": "{{id}}",
              "title": "{{title}}",
              "date": "{{date}}",
              "source": { "fileName": "meeting.mp3", "durationSeconds": {{durationSeconds}} },
              "run": { "numSpeakersDetected": 2 },
              "status": "transcribed"
            }
            """;

        File.WriteAllText(Path.Combine(directory, "session.json"), manifest);
        return directory;
    }

    private sealed class FakeRunner(params EngineEvent[] engineEvents) : IEngineRunner
    {
        public EngineJobRequest? LastRequest { get; private set; }

        public async IAsyncEnumerable<EngineEvent> RunAsync(
            EngineJobRequest request,
            [EnumeratorCancellation] CancellationToken cancellationToken = default)
        {
            LastRequest = request;

            foreach (var engineEvent in engineEvents)
            {
                yield return engineEvent;
                await Task.Yield();
            }
        }
    }

    private sealed class FakeLocator(EngineLaunchSpec spec) : IEngineLocator
    {
        public EngineLaunchSpec? Locate(EngineClientOptions options) => spec;
    }

    private sealed class FakeFileDialogService : IFileDialogService
    {
        public string? PickAudioFile() => null;

        public string? PickFile(string title, string filter) => null;

        public string? PickFolder(string? initialDirectory = null, string title = "انتخاب پوشه") => null;
    }

    private sealed class FakeSettingsStore(AppSettings? settings = null) : ISettingsStore
    {
        public AppSettings? LastSaved { get; private set; }

        public Task<AppSettings> LoadAsync(CancellationToken cancellationToken = default)
        {
            return Task.FromResult(settings ?? new AppSettings());
        }

        public Task SaveAsync(AppSettings settings, CancellationToken cancellationToken = default)
        {
            LastSaved = settings;
            return Task.CompletedTask;
        }
    }

    private sealed class FakeSettingsDialog(AppSettings? result) : ISettingsDialogService
    {
        public AppSettings? Show(AppSettings current) => result;
    }

    private sealed class FakePreflight : IEnginePreflight
    {
        public string? EngineVersion { get; init; } = "0.1.0";

        public Task<PreflightResult> RunAsync(
            string device,
            string computeType,
            string? modelsDirectory,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(new PreflightResult
            {
                ModelsReady = true,
                Ffmpeg = true,
                Device = device,
                ComputeType = computeType,
                EngineVersion = EngineVersion
            });
        }
    }
}
