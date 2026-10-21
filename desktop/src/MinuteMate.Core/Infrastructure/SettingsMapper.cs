using MinuteMate.Core.Contracts;
using MinuteMate.Core.Models;

namespace MinuteMate.Core.Infrastructure;

public static class SettingsMapper
{
    public static void Apply(
        AppSettings settings,
        EngineClientOptions engine,
        StorageOptions storage,
        MinutesOptions minutes)
    {
        if (settings.EngineExecutablePath is not null)
        {
            engine.ExecutablePath = settings.EngineExecutablePath;
        }

        if (settings.PythonPath is not null)
        {
            engine.PythonPath = settings.PythonPath;
        }

        if (settings.OutputDirectory is not null)
        {
            storage.OutputDirectory = settings.OutputDirectory;
        }

        if (settings.SessionsRoot is not null)
        {
            storage.SessionsRoot = settings.SessionsRoot;
        }

        if (settings.ModelsDirectory is not null)
        {
            storage.ModelsDirectory = settings.ModelsDirectory;
        }

        minutes.Enabled = settings.EnableMinutes;
    }

    public static AppSettings Snapshot(
        AppSettings current,
        EngineClientOptions engine,
        StorageOptions storage,
        MinutesOptions minutes)
    {
        return new AppSettings
        {
            OutputDirectory = storage.OutputDirectory ?? current.OutputDirectory,
            SessionsRoot = storage.SessionsRoot ?? current.SessionsRoot,
            ModelsDirectory = storage.ModelsDirectory ?? current.ModelsDirectory,
            EngineExecutablePath = engine.ExecutablePath ?? current.EngineExecutablePath,
            PythonPath = engine.PythonPath ?? current.PythonPath,
            NumSpeakers = current.NumSpeakers,
            Device = current.Device,
            ComputeType = current.ComputeType,
            EnableMinutes = minutes.Enabled,
            Theme = current.Theme,
            Language = current.Language,
            Providers = current.Providers,
            LocalModels = current.LocalModels
        };
    }
}
