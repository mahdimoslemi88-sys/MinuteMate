using System.Text.Json;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Models;

namespace MinuteMate.Core.Infrastructure;

public sealed class JsonSettingsStore : ISettingsStore
{
    private readonly SemaphoreSlim _gate = new(1, 1);

    public async Task<AppSettings> LoadAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            if (!File.Exists(AppPaths.SettingsFile))
            {
                return new AppSettings();
            }

            await using var stream = File.OpenRead(AppPaths.SettingsFile);
            return await JsonSerializer.DeserializeAsync<AppSettings>(
                stream,
                JsonDefaults.App,
                cancellationToken) ?? new AppSettings();
        }
        catch (JsonException)
        {
            return new AppSettings();
        }
        catch (IOException)
        {
            return new AppSettings();
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task SaveAsync(AppSettings settings, CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken);
        try
        {
            AppPaths.EnsureCreated();
            var temporaryPath = AppPaths.SettingsFile + ".tmp";

            await using (var stream = File.Create(temporaryPath))
            {
                await JsonSerializer.SerializeAsync(
                    stream,
                    settings,
                    JsonDefaults.App,
                    cancellationToken);
            }

            File.Move(temporaryPath, AppPaths.SettingsFile, true);
        }
        finally
        {
            _gate.Release();
        }
    }
}
