using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Contracts;
using MinuteMate.Core.Infrastructure;

namespace MinuteMate.EngineClient;

public sealed class EngineProcessRunner : IEngineRunner
{
    private readonly EngineClientOptions _options;
    private readonly IEngineLocator _locator;

    public EngineProcessRunner(EngineClientOptions options, IEngineLocator locator)
    {
        _options = options;
        _locator = locator;
    }

    public async IAsyncEnumerable<EngineEvent> RunAsync(
        EngineJobRequest request,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var launch = _locator.Locate(_options)
            ?? throw new InvalidOperationException(
                "موتور MinuteMate پیدا نشد. مسیر فایل اجرایی یا پایتون را در appsettings.json تنظیم کنید.");

        var startInfo = new ProcessStartInfo
        {
            FileName = launch.FileName,
            WorkingDirectory = launch.WorkingDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardInputEncoding = new UTF8Encoding(false),
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };

        foreach (var argument in launch.Arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        using var process = new Process { StartInfo = startInfo };

        if (!process.Start())
        {
            throw new InvalidOperationException("اجرای موتور MinuteMate ممکن نشد.");
        }

        yield return new EngineEvent
        {
            Type = EngineEventType.Started,
            Message = request.JobId
        };

        using var registration = cancellationToken.Register(() => TryKill(process));

        await process.StandardInput.WriteAsync(
            JsonSerializer.Serialize(request, JsonDefaults.Engine));
        await process.StandardInput.FlushAsync();
        process.StandardInput.Close();

        var stderrTask = process.StandardError.ReadToEndAsync();
        var sawError = false;

        while (true)
        {
            if (cancellationToken.IsCancellationRequested)
            {
                yield break;
            }

            var line = await process.StandardOutput.ReadLineAsync(cancellationToken);
            if (line is null)
            {
                break;
            }

            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }

            var engineEvent = Parse(line);
            if (engineEvent is null)
            {
                yield return new EngineEvent
                {
                    Type = EngineEventType.Log,
                    Level = "debug",
                    Message = line
                };

                continue;
            }

            if (engineEvent.Type == EngineEventType.Error)
            {
                sawError = true;
            }

            yield return engineEvent;
        }

        await process.WaitForExitAsync(CancellationToken.None);
        var stderr = await stderrTask;

        if (!string.IsNullOrWhiteSpace(stderr))
        {
            yield return new EngineEvent
            {
                Type = EngineEventType.Log,
                Level = process.ExitCode == 0 ? "stderr" : "error",
                Message = stderr.Trim()
            };
        }

        if (process.ExitCode != 0 && !sawError)
        {
            yield return new EngineEvent
            {
                Type = EngineEventType.Error,
                Code = $"exit_{process.ExitCode}",
                Message = string.IsNullOrWhiteSpace(stderr)
                    ? $"موتور MinuteMate با کد {process.ExitCode} خارج شد."
                    : stderr.Trim()
            };
        }
    }

    private static EngineEvent? Parse(string line)
    {
        try
        {
            return JsonSerializer.Deserialize<EngineEvent>(line, JsonDefaults.Engine);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static void TryKill(Process process)
    {
        try
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
            }
        }
        catch (InvalidOperationException)
        {
        }
        catch (System.ComponentModel.Win32Exception)
        {
        }
    }
}
