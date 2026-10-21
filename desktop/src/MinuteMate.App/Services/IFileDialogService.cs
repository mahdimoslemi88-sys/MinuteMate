namespace MinuteMate.App.Services;

public interface IFileDialogService
{
    string? PickAudioFile();

    string? PickFile(string title, string filter);

    string? PickFolder(string? initialDirectory = null, string title = "انتخاب پوشه");
}
