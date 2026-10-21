using MinuteMate.Core.Models;

namespace MinuteMate.App.Services;

public interface ISettingsDialogService
{
    AppSettings? Show(AppSettings current);
}

public sealed class SettingsDialogService : ISettingsDialogService
{
    private readonly IFileDialogService _fileDialogService;

    public SettingsDialogService(IFileDialogService fileDialogService)
    {
        _fileDialogService = fileDialogService;
    }

    public AppSettings? Show(AppSettings current)
    {
        var viewModel = new ViewModels.SettingsViewModel(current, _fileDialogService);
        var window = new SettingsWindow(viewModel)
        {
            Owner = System.Windows.Application.Current?.MainWindow
        };

        return window.ShowDialog() == true ? viewModel.Result : null;
    }
}
