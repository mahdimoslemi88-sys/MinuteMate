using System.Diagnostics;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MinuteMate.App.Services;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Contracts;
using MinuteMate.Core.Infrastructure;

namespace MinuteMate.App.ViewModels;

public partial class MainWindowViewModel : ObservableObject
{
    private readonly IEngineLocator _engineLocator;
    private readonly EngineClientOptions _engineOptions;
    private readonly IFileDialogService _fileDialogService;

    [ObservableProperty]
    private string _engineStatusTitle = "موتور آماده نیست";

    [ObservableProperty]
    private string _engineStatusDetail = "مسیر موتور را در تنظیمات مشخص کنید.";

    [ObservableProperty]
    private bool _isEngineReady;

    [ObservableProperty]
    private string? _selectedAudioPath;

    [ObservableProperty]
    private string _selectedAudioName = "فایلی انتخاب نشده";

    public MainWindowViewModel(
        IEngineLocator engineLocator,
        EngineClientOptions engineOptions,
        IFileDialogService fileDialogService)
    {
        _engineLocator = engineLocator;
        _engineOptions = engineOptions;
        _fileDialogService = fileDialogService;

        AppPaths.EnsureCreated();
        RefreshEngineStatus();
    }

    public string DataDirectory => AppPaths.Root;

    partial void OnSelectedAudioPathChanged(string? value)
    {
        SelectedAudioName = string.IsNullOrWhiteSpace(value)
            ? "فایلی انتخاب نشده"
            : Path.GetFileName(value);
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
        Process.Start(new ProcessStartInfo
        {
            FileName = "explorer.exe",
            Arguments = AppPaths.Root,
            UseShellExecute = true
        });
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
            EngineStatusDetail = "فایل اجرایی موتور یا مسیر پایتون را در appsettings.json تنظیم کنید.";
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
}
