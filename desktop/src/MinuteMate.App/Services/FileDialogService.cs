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
}
