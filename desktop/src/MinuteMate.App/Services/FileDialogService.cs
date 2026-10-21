using System.IO;
using Microsoft.Win32;

namespace MinuteMate.App.Services;

public sealed class FileDialogService : IFileDialogService
{
    public string? PickAudioFile()
    {
        var dialog = new OpenFileDialog
        {
            Title = "انتخاب فایل جلسه",
            Filter = "فایل‌های صوتی و تصویری|*.mp3;*.wav;*.m4a;*.ogg;*.flac;*.aac;*.mp4;*.mkv;*.aup4|همه فایل‌ها|*.*",
            CheckFileExists = true,
            Multiselect = false
        };

        return dialog.ShowDialog() == true ? dialog.FileName : null;
    }

    public string? PickFile(string title, string filter)
    {
        var dialog = new OpenFileDialog
        {
            Title = title,
            Filter = filter,
            CheckFileExists = true,
            Multiselect = false
        };

        return dialog.ShowDialog() == true ? dialog.FileName : null;
    }

    public string? PickFolder(string? initialDirectory = null, string title = "انتخاب پوشه")
    {
        var dialog = new OpenFolderDialog
        {
            Title = title,
            Multiselect = false
        };

        if (!string.IsNullOrWhiteSpace(initialDirectory) && Directory.Exists(initialDirectory))
        {
            dialog.InitialDirectory = initialDirectory;
        }

        return dialog.ShowDialog() == true ? dialog.FolderName : null;
    }
}
