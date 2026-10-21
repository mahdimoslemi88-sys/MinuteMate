using System.Diagnostics;
using System.Text;
using System.Text.Json;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Contracts;

namespace MinuteMate.EngineClient;

public sealed class EnginePreflight : IEnginePreflight
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(90);

    private readonly IEngineLocator _locator;
    private readonly EngineClientOptions _options;

    public EnginePreflight(IEngineLocator locator, EngineClientOptions options)
    {
        _locator = locator;
        _options = options;
    }

    public async Task<PreflightResult> RunAsync(
        string device,
        string computeType,
        string? modelsDirectory,
        CancellationToken cancellationToken = default)
    {
        var launch = _locator.Locate(_options)
            ?? throw new InvalidOperationException("موتور MinuteMate پیدا نشد.");

        var arguments = BuildArguments(launch.Kind, device, computeType, modelsDirectory);
        var startInfo = new ProcessStartInfo
        {
            FileName = launch.FileName,
            WorkingDirectory = launch.WorkingDirectory,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = new UTF8Encoding(false),
            StandardErrorEncoding = new UTF8Encoding(false)
        };

        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        startInfo.Environment["PYTHONUTF8"] = "1";
        startInfo.Environment["PYTHONIOENCODING"] = "utf-8";

        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(Timeout);

        using var process = new Process { StartInfo = startInfo, EnableRaisingEvents = true };

        try
        {
            process.Start();
        }
        catch (Exception exception)
        {
            return new PreflightResult { Error = exception.Message };
        }

        var stdoutTask = process.StandardOutput.ReadToEndAsync(timeout.Token);
        var stderrTask = process.StandardError.ReadToEndAsync(timeout.Token);

        try
        {
            await process.WaitForExitAsync(timeout.Token);
        }
        catch (OperationCanceledException)
        {
            TryKill(process);
            return new PreflightResult { Error = "پیش‌بررسی بیش از حد طول کشید." };
        }

        var stdout = await stdoutTask;
        var stderr = await stderrTask;

        return Parse(stdout, stderr, process.ExitCode);
    }

    private IReadOnlyList<string> BuildArguments(
        string kind,
        string device,
        string computeType,
        string? modelsDirectory)
    {
        var arguments = new List<string>();
        if (kind == "python")
        {
            arguments.Add("-m");
            arguments.Add(string.IsNullOrWhiteSpace(_options.PythonModule)
                ? "minutemate"
                : _options.PythonModule);
        }

        arguments.Add("preflight");
        arguments.Add("--device");
        arguments.Add(string.IsNullOrWhiteSpace(device) ? "auto" : device);
        arguments.Add("--compute-type");
        arguments.Add(string.IsNullOrWhiteSpace(computeType) ? "auto" : computeType);

        if (!string.IsNullOrWhiteSpace(modelsDirectory))
        {
            arguments.Add("--models-dir");
            arguments.Add(modelsDirectory);
        }

        return arguments;
    }

    private static PreflightResult Parse(string stdout, string stderr, int exitCode)
    {
        var start = stdout.IndexOf('{');
        var end = stdout.LastIndexOf('}');
        if (start < 0 || end <= start)
        {
            return new PreflightResult
            {
                Error = string.IsNullOrWhiteSpace(stderr)
                    ? $"پیش‌بررسی خروجی معتبری برنگرداند (کد {exitCode})."
                    : stderr.Trim()
            };
        }

        try
        {
            using var document = JsonDocument.Parse(stdout[start..(end + 1)]);
            var root = document.RootElement;

            return new PreflightResult
            {
                EngineVersion = ReadString(root, "engineVersion"),
                ModelsReady = root.TryGetProperty("modelsReady", out var ready) && ready.GetBoolean(),
                MissingModels = ReadStringArray(root, "missingModels"),
                Ffmpeg = root.TryGetProperty("ffmpeg", out var ffmpeg)
                    && ffmpeg.ValueKind == JsonValueKind.String,
                FfmpegError = ReadString(root, "ffmpegError"),
                Device = ReadString(root, "device") ?? "cpu",
                ComputeType = ReadString(root, "computeType") ?? "int8",
                GpuCount = root.TryGetProperty("gpuCount", out var gpu) && gpu.TryGetInt32(out var count)
                    ? count
                    : 0,
                BeamSize = root.TryGetProperty("beamSize", out var beam) && beam.TryGetInt32(out var beamValue)
                    ? beamValue
                    : 1,
                BatchSize = root.TryGetProperty("batchSize", out var batch) && batch.TryGetInt32(out var batchValue)
                    ? batchValue
                    : 0,
                SpeakerEmbedding = root.TryGetProperty("speakerEmbedding", out var embedding)
                    && embedding.ValueKind == JsonValueKind.String
                    ? embedding.GetString() ?? "wespeaker"
                    : "wespeaker",
                ModelsDirectory = ReadString(root, "modelsDir"),
                RawJson = stdout[start..(end + 1)]
            };
        }
        catch (JsonException exception)
        {
            return new PreflightResult { Error = exception.Message };
        }
    }

    private static string? ReadString(JsonElement root, string name)
    {
        return root.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;
    }

    private static List<string> ReadStringArray(JsonElement root, string name)
    {
        if (!root.TryGetProperty(name, out var value) || value.ValueKind != JsonValueKind.Array)
        {
            return [];
        }

        return value.EnumerateArray()
            .Where(item => item.ValueKind == JsonValueKind.String)
            .Select(item => item.GetString()!)
            .ToList();
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
        catch (NotSupportedException)
        {
        }
    }
}
