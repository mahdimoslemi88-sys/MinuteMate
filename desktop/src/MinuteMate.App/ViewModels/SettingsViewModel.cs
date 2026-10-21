using System.Collections.Generic;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MinuteMate.App.Services;
using MinuteMate.Core.Models;

namespace MinuteMate.App.ViewModels;

public partial class SettingsViewModel : ObservableObject
{
    protected readonly IFileDialogService _fileDialogService;

    public IFileDialogService FileDialogService => _fileDialogService;

    [ObservableProperty]
    private string? _pythonPath;

    [ObservableProperty]
    private string? _engineExecutablePath;

    [ObservableProperty]
    private string? _outputDirectory;

    [ObservableProperty]
    private string? _sessionsRoot;

    [ObservableProperty]
    private string? _modelsDirectory;

    [ObservableProperty]
    private int _numSpeakers;

    [ObservableProperty]
    private string _device = "auto";

    [ObservableProperty]
    private string _computeType = "auto";

    [ObservableProperty]
    private bool _enableMinutes;

    [ObservableProperty]
    private string? _validationMessage;

    public List<ProviderSettings> Providers { get; set; } = new();

    public List<LocalModelSettings> LocalModels { get; set; } = new();

    public ProviderSettingsViewModel ProviderSettings { get; }

    public SettingsViewModel(AppSettings settings, IFileDialogService fileDialogService)
    {
        _fileDialogService = fileDialogService;
        _pythonPath = settings.PythonPath;
        _engineExecutablePath = settings.EngineExecutablePath;
        _outputDirectory = settings.OutputDirectory;
        _sessionsRoot = settings.SessionsRoot;
        _modelsDirectory = settings.ModelsDirectory;
        _numSpeakers = settings.NumSpeakers;
        _device = settings.Device;
        _computeType = settings.ComputeType;
        _enableMinutes = settings.EnableMinutes;
        Theme = settings.Theme;
        Language = settings.Language;

        Providers = settings.Providers ?? new List<ProviderSettings>();
        LocalModels = settings.LocalModels ?? new List<LocalModelSettings>();

        ProviderSettings = new ProviderSettingsViewModel(this);
    }

    public string Theme { get; }

    public string Language { get; }

    public IReadOnlyList<string> Devices { get; } = ["auto", "cuda", "cpu"];

    public IReadOnlyList<string> ComputeTypes { get; } = ["auto", "float16", "int8", "float32"];

    public IReadOnlyList<int> SpeakerCounts { get; } = Enumerable.Range(0, 11).ToArray();

    public IReadOnlyList<string> AsrModels { get; } = ["turbo", "fa"];

    public AppSettings? Result { get; private set; }

    public event EventHandler? Saved;

    [RelayCommand]
    private void BrowsePython()
    {
        var file = _fileDialogService.PickFile(
            "انتخاب مفسر پایتون",
            "برنامه‌های اجرایی|python.exe;python3.exe;*.exe|همه فایل‌ها|*.*");
        if (!string.IsNullOrWhiteSpace(file))
        {
            PythonPath = file;
        }
    }

    [RelayCommand]
    private void BrowseEngine()
    {
        var file = _fileDialogService.PickFile(
            "انتخاب فایل اجرایی موتور",
            "برنامه‌های اجرایی|minutemate-engine.exe;*.exe|همه فایل‌ها|*.*");
        if (!string.IsNullOrWhiteSpace(file))
        {
            EngineExecutablePath = file;
        }
    }

    [RelayCommand]
    private void BrowseOutput()
    {
        var folder = _fileDialogService.PickFolder(OutputDirectory);
        if (!string.IsNullOrWhiteSpace(folder))
        {
            OutputDirectory = folder;
        }
    }

    [RelayCommand]
    private void BrowseSessions()
    {
        var folder = _fileDialogService.PickFolder(SessionsRoot);
        if (!string.IsNullOrWhiteSpace(folder))
        {
            SessionsRoot = folder;
        }
    }

    [RelayCommand]
    private void BrowseModels()
    {
        var folder = _fileDialogService.PickFolder(ModelsDirectory);
        if (!string.IsNullOrWhiteSpace(folder))
        {
            ModelsDirectory = folder;
        }
    }

    [RelayCommand]
    private void Save()
    {
        if (NumSpeakers is < 0 or > 20)
        {
            ValidationMessage = "تعداد گویندگان باید بین ۰ تا ۲۰ باشد.";
            return;
        }

        ProviderSettings.SaveAll();

        ValidationMessage = null;
        Result = new AppSettings
        {
            PythonPath = Clean(PythonPath),
            EngineExecutablePath = Clean(EngineExecutablePath),
            OutputDirectory = Clean(OutputDirectory),
            SessionsRoot = Clean(SessionsRoot),
            ModelsDirectory = Clean(ModelsDirectory),
            NumSpeakers = NumSpeakers,
            Device = Device,
            ComputeType = ComputeType,
            EnableMinutes = EnableMinutes,
            Theme = Theme,
            Language = Language,
            Providers = Providers,
            LocalModels = LocalModels
        };

        Saved?.Invoke(this, EventArgs.Empty);
    }

    private static string? Clean(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }
}
