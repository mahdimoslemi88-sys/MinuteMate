using System.Collections.Concurrent;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;
using Microsoft.Extensions.Logging;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Contracts;
using MinuteMate.Core.Infrastructure;

namespace MinuteMate.EngineClient;

public sealed class EngineProcessRunner : IEngineRunner
{
    private const string InfoLevel = "info";
    private const string WarningLevel = "warning";
    private const string ErrorLevel = "error";
    private const string DebugLevel = "debug";

    private readonly EngineClientOptions _options;
    private readonly IEngineLocator _locator;
    private readonly ILogger<EngineProcessRunner> _logger;
    private readonly ConcurrentDictionary<string, byte> _running = new(StringComparer.Ordinal);

    public EngineProcessRunner(EngineClientOptions options, IEngineLocator locator, ILogger<EngineProcessRunner> logger)
    {
        _options = options;
        _locator = locator;
        _logger = logger;
    }

    public async IAsyncEnumerable<EngineEvent> RunAsync(
        EngineJobRequest request,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);

        if (!_running.TryAdd(request.JobId, 0))
        {
            yield return new EngineEvent
            {
                Type = EngineEventType.Error,
                Code = "already_running",
                Message = $"job «{request.JobId}» همین حالا در حال اجراست."
            };

            yield break;
        }

        _logger.LogInformation("Starting job {JobId}", request.JobId);

        await foreach (var engineEvent in RunCoreAsync(request, cancellationToken).ConfigureAwait(false))
        {
            yield return engineEvent;
        }

        _logger.LogInformation("Job {JobId} completed successfully", request.JobId);
    }

    private async IAsyncEnumerable<EngineEvent> RunCoreAsync(
        EngineJobRequest request,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var launch = _locator.Locate(_options)
            ?? throw new EngineLaunchException(
                "موتور MinuteMate پیدا نشد. مسیر فایل اجرایی یا پایتون را در appsettings.json تنظیم کنید.");

        using var process = new Process { StartInfo = BuildStartInfo(launch) };

        try
        {
            if (!process.Start())
            {
                throw new EngineLaunchException("اجرای موتور MinuteMate ممکن نشد.");
            }
        }
        catch (Exception ex) when (ex is System.ComponentModel.Win32Exception or InvalidOperationException)
        {
            _logger.LogError(ex, "Failed to start engine process for job {JobId}", request.JobId);
            throw new EngineLaunchException("اجرای موتور MinuteMate ممکن نشد.", ex);
        }

        var logDirectory = PrepareLogDirectory(request.JobId);
        var stdoutPath = Path.Combine(logDirectory, "stdout.ndjson");
        var stderrPath = Path.Combine(logDirectory, "stderr.log");

        _logger.LogDebug("Job {JobId}: log directory {LogDir}, stdout {Stdout}, stderr {Stderr}",
            request.JobId, logDirectory, stdoutPath, stderrPath);

        yield return new EngineEvent
        {
            Type = EngineEventType.Started,
            Message = $"pid={process.Id}; log={logDirectory}"
        };

        var state = new RunState(_options.MaxStderrTailLines);
        var channel = Channel.CreateUnbounded<EngineEvent>(new UnboundedChannelOptions
        {
            SingleReader = true,
            SingleWriter = false
        });

        using var stdoutLog = OpenLogWriter(stdoutPath);
        using var stderrLog = OpenLogWriter(stderrPath);

        var stdoutTask = Task.Run(() => PumpStdoutAsync(
            process.StandardOutput,
            channel.Writer,
            stdoutLog,
            state,
            _options.MaxLineLength));

        var stderrTask = Task.Run(() => PumpStderrAsync(
            process.StandardError,
            channel.Writer,
            stderrLog,
            state,
            _options));

        using var registration = cancellationToken.Register(
            () => RequestCancel(process, state, _options.CancelGraceSeconds));

        var jobTask = WriteJobAsync(process, request, channel.Writer, stderrPath);

        var completionTask = Task.Run(() => CompleteAsync(
            process,
            channel.Writer,
            state,
            stderrPath,
            stdoutTask,
            stderrTask,
            jobTask,
            _logger));

        await foreach (var engineEvent in channel.Reader.ReadAllAsync().ConfigureAwait(false))
        {
            yield return engineEvent;
        }

        await completionTask.ConfigureAwait(false);
    }

    private static ProcessStartInfo BuildStartInfo(EngineLaunchSpec launch)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = launch.FileName,
            WorkingDirectory = launch.WorkingDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardInputEncoding = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false),
            StandardOutputEncoding = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false),
            StandardErrorEncoding = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false)
        };

        startInfo.Environment["PYTHONUTF8"] = "1";
        startInfo.Environment["PYTHONIOENCODING"] = "utf-8";

        foreach (var argument in launch.Arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        return startInfo;
    }

    private string PrepareLogDirectory(string jobId)
    {
        var root = string.IsNullOrWhiteSpace(_options.LogDirectory)
            ? AppPaths.Logs
            : _options.LogDirectory!;

        var directory = Path.Combine(root, jobId);
        Directory.CreateDirectory(directory);
        return directory;
    }

    private static StreamWriter OpenLogWriter(string path)
    {
        var stream = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.Read);
        return new StreamWriter(stream, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false))
        {
            AutoFlush = true
        };
    }

    private static async Task WriteJobAsync(
        Process process,
        EngineJobRequest request,
        ChannelWriter<EngineEvent> writer,
        string stderrPath)
    {
        try
        {
            var payload = JsonSerializer.Serialize(request, JsonDefaults.Engine);
            await process.StandardInput.WriteAsync(payload).ConfigureAwait(false);
            await process.StandardInput.FlushAsync().ConfigureAwait(false);
            process.StandardInput.Close();
        }
        catch (Exception ex) when (ex is IOException or ObjectDisposedException or InvalidOperationException)
        {
            writer.TryWrite(new EngineEvent
            {
                Type = EngineEventType.Error,
                Code = "input_pipe_closed",
                Message = "اتصال stdin موتور پیش از نوشتن job بسته شد.",
                Hint = $"log={stderrPath}"
            });
        }
    }

    private static async Task PumpStdoutAsync(
        StreamReader reader,
        ChannelWriter<EngineEvent> writer,
        StreamWriter log,
        RunState state,
        int maxLineLength)
    {
        try
        {
            while (true)
            {
                var line = await reader.ReadLineAsync().ConfigureAwait(false);
                if (line is null)
                {
                    break;
                }

                if (line.Length > 0)
                {
                    await log.WriteLineAsync(line).ConfigureAwait(false);
                }

                if (string.IsNullOrWhiteSpace(line))
                {
                    continue;
                }

                if (line.Length > maxLineLength)
                {
                    writer.TryWrite(new EngineEvent
                    {
                        Type = EngineEventType.Log,
                        Level = WarningLevel,
                        Message = $"خط stdout بلندتر از {maxLineLength} کاراکتر بود و بریده شد."
                    });

                    line = line[..maxLineLength];
                }

                var engineEvent = Parse(line);
                if (engineEvent is null)
                {
                    writer.TryWrite(new EngineEvent
                    {
                        Type = EngineEventType.Log,
                        Level = DebugLevel,
                        Message = line
                    });

                    continue;
                }

                ApplyEventState(engineEvent, state);

                if (engineEvent.Type == EngineEventType.Artifact
                    && !string.IsNullOrWhiteSpace(engineEvent.Path)
                    && !File.Exists(engineEvent.Path))
                {
                    writer.TryWrite(new EngineEvent
                    {
                        Type = EngineEventType.Log,
                        Level = WarningLevel,
                        Message = $"فایل artifact پیدا نشد: {engineEvent.Path}"
                    });
                }

                writer.TryWrite(engineEvent);
            }
        }
        catch (Exception ex) when (ex is IOException or ObjectDisposedException or InvalidOperationException)
        {
        }
        finally
        {
            try
            {
                await log.FlushAsync().ConfigureAwait(false);
            }
            catch (Exception ex) when (ex is IOException or ObjectDisposedException)
            {
            }
        }
    }

    private static async Task PumpStderrAsync(
        StreamReader reader,
        ChannelWriter<EngineEvent> writer,
        StreamWriter log,
        RunState state,
        EngineClientOptions options)
    {
        var throttle = Math.Max(1, options.StderrThrottlePerSecond);
        var windowStart = Stopwatch.GetTimestamp();
        var emittedInWindow = 0;
        var suppressed = 0;

        try
        {
            while (true)
            {
                var line = await reader.ReadLineAsync().ConfigureAwait(false);
                if (line is null)
                {
                    break;
                }

                state.AddStderrTail(line);

                if (line.Length > 0)
                {
                    await log.WriteLineAsync(line).ConfigureAwait(false);
                }

                if (emittedInWindow < throttle)
                {
                    writer.TryWrite(new EngineEvent
                    {
                        Type = EngineEventType.Log,
                        Level = ClassifyStderrLevel(line),
                        Message = line
                    });

                    emittedInWindow++;
                }
                else
                {
                    suppressed++;
                }

                if (Stopwatch.GetElapsedTime(windowStart) >= TimeSpan.FromSeconds(1))
                {
                    if (suppressed > 0)
                    {
                        writer.TryWrite(new EngineEvent
                        {
                            Type = EngineEventType.Log,
                            Level = InfoLevel,
                            Message = $"… (+{suppressed} lines)"
                        });

                        suppressed = 0;
                    }

                    windowStart = Stopwatch.GetTimestamp();
                    emittedInWindow = 0;
                }
            }
        }
        catch (Exception ex) when (ex is IOException or ObjectDisposedException or InvalidOperationException)
        {
        }
        finally
        {
            if (suppressed > 0)
            {
                writer.TryWrite(new EngineEvent
                {
                    Type = EngineEventType.Log,
                    Level = InfoLevel,
                    Message = $"… (+{suppressed} lines)"
                });
            }

            try
            {
                await log.FlushAsync().ConfigureAwait(false);
            }
            catch (Exception ex) when (ex is IOException or ObjectDisposedException)
            {
            }
        }
    }

    private static async Task CompleteAsync(
        Process process,
        ChannelWriter<EngineEvent> writer,
        RunState state,
        string stderrPath,
        Task stdoutTask,
        Task stderrTask,
        Task jobTask,
        ILogger logger)
    {
        try
        {
            await Task.WhenAll(stdoutTask, stderrTask, jobTask).ConfigureAwait(false);

            if (state.Cancelled)
            {
                using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));

                try
                {
                    await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false);
                }
                catch (OperationCanceledException)
                {
                    logger.LogWarning("Process kill timeout, force killing");
                    TryKill(process);
                    await process.WaitForExitAsync(CancellationToken.None).ConfigureAwait(false);
                }
            }
            else
            {
                await process.WaitForExitAsync(CancellationToken.None).ConfigureAwait(false);
            }

            state.ExitCode = SafeExitCode(process);

            foreach (var engineEvent in BuildCompletionEvents(state, stderrPath))
            {
                writer.TryWrite(engineEvent);
            }

            logger.LogInformation("Job completed with exit code {ExitCode}", state.ExitCode);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Completion error");
            writer.TryWrite(new EngineEvent
            {
                Type = EngineEventType.Error,
                Code = "runner_error",
                Message = ex.Message,
                Hint = $"log={stderrPath}"
            });
        }
        finally
        {
            writer.TryComplete();
        }
    }

    private static IEnumerable<EngineEvent> BuildCompletionEvents(RunState state, string stderrPath)
    {
        var hint = BuildHint(state, stderrPath);

        if (state.SawError)
        {
            yield break;
        }

        if (state.Cancelled)
        {
            if (state.SawDone)
            {
                yield break;
            }

            yield return new EngineEvent
            {
                Type = EngineEventType.Log,
                Level = WarningLevel,
                Message = "cancelled by user"
            };

            yield return new EngineEvent
            {
                Type = EngineEventType.Error,
                Code = "cancelled",
                Message = "اجرای موتور توسط کاربر لغو شد.",
                Hint = hint
            };

            yield break;
        }

        if (state.SawDone)
        {
            yield break;
        }

        switch (state.ExitCode)
        {
            case 0:
                yield return new EngineEvent
                {
                    Type = EngineEventType.Error,
                    Code = "exit_0_without_done",
                    Message = "موتور بدون ارسال رویداد done خارج شد.",
                    Hint = hint
                };
                break;
            case 1:
                yield return new EngineEvent
                {
                    Type = EngineEventType.Error,
                    Code = "engine_error",
                    Message = MessageOrStderr(state, "موتور با خطای داخلی خارج شد."),
                    Hint = hint
                };
                break;
            case 2:
                yield return new EngineEvent
                {
                    Type = EngineEventType.Error,
                    Code = "input_error",
                    Message = MessageOrStderr(state, "ورودی ارسالی به موتور نامعتبر است."),
                    Hint = hint
                };
                break;
            case 130:
                yield return new EngineEvent
                {
                    Type = EngineEventType.Error,
                    Code = "cancelled",
                    Message = "اجرای موتور لغو شد.",
                    Hint = hint
                };
                break;
            default:
                yield return new EngineEvent
                {
                    Type = EngineEventType.Error,
                    Code = $"exit_{state.ExitCode}",
                    Message = MessageOrStderr(state, $"موتور با کد {state.ExitCode} خارج شد."),
                    Hint = hint
                };
                break;
        }
    }

    private static void ApplyEventState(EngineEvent engineEvent, RunState state)
    {
        switch (engineEvent.Type)
        {
            case EngineEventType.Error:
                state.SawError = true;
                break;
            case EngineEventType.Done:
                state.SawDone = true;
                break;
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

    private static string ClassifyStderrLevel(string line)
    {
        var trimmed = line.TrimStart();

        if (trimmed.StartsWith("ERROR", StringComparison.Ordinal)
            || trimmed.StartsWith("Traceback", StringComparison.Ordinal))
        {
            return ErrorLevel;
        }

        if (trimmed.StartsWith("WARNING", StringComparison.Ordinal))
        {
            return WarningLevel;
        }

        return InfoLevel;
    }

    private static string MessageOrStderr(RunState state, string fallback)
    {
        return string.IsNullOrWhiteSpace(state.StderrTail) ? fallback : state.StderrTail;
    }

    private static string BuildHint(RunState state, string stderrPath)
    {
        var tail = state.StderrTail;
        return string.IsNullOrWhiteSpace(tail)
            ? $"log={stderrPath}"
            : $"{tail}{Environment.NewLine}---{Environment.NewLine}log={stderrPath}";
    }

    private static int SafeExitCode(Process process)
    {
        try
        {
            return process.HasExited ? process.ExitCode : -1;
        }
        catch (InvalidOperationException)
        {
            return -1;
        }
    }

    private static void RequestCancel(Process process, RunState state, double graceSeconds)
    {
        state.Cancelled = true;

        try
        {
            if (process.HasExited)
            {
                return;
            }

            try
            {
                process.StandardInput.Close();
            }
            catch (Exception ex) when (ex is IOException or ObjectDisposedException or InvalidOperationException)
            {
            }

            var graceMilliseconds = Math.Max(0, (int)(graceSeconds * 1000));
            if (!process.WaitForExit(graceMilliseconds))
            {
                TryKill(process);
            }
        }
        catch (Exception ex) when (ex is InvalidOperationException or System.ComponentModel.Win32Exception)
        {
            TryKill(process);
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

    private sealed class RunState
    {
        private readonly object _gate = new();
        private readonly Queue<string> _stderrTail = new();
        private readonly int _maxStderrTailLines;

        public RunState(int maxStderrTailLines)
        {
            _maxStderrTailLines = Math.Max(1, maxStderrTailLines);
        }

        public bool SawError { get; set; }

        public bool SawDone { get; set; }

        public volatile bool Cancelled;

        public int ExitCode { get; set; } = -1;

        public string StderrTail
        {
            get
            {
                lock (_gate)
                {
                    return string.Join(Environment.NewLine, _stderrTail);
                }
            }
        }

        public void AddStderrTail(string line)
        {
            if (string.IsNullOrWhiteSpace(line))
            {
                return;
            }

            lock (_gate)
            {
                while (_stderrTail.Count >= _maxStderrTailLines)
                {
                    _stderrTail.Dequeue();
                }

                _stderrTail.Enqueue(line);
            }
        }
    }
}