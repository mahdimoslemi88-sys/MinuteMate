using System.Diagnostics;
using System.Text;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Contracts;

namespace MinuteMate.EngineClient.Tests;

public class EngineProcessRunnerTests
{
    private const string StreamPreamble = """
        $stdout = [System.IO.StreamWriter]::new([Console]::OpenStandardOutput(), [System.Text.UTF8Encoding]::new($false))
        $stdout.AutoFlush = $true
        $stderr = [System.IO.StreamWriter]::new([Console]::OpenStandardError(), [System.Text.UTF8Encoding]::new($false))
        $stderr.AutoFlush = $true
        """;

    [Fact]
    public async Task StderrLineArrivesBeforeDoneEvent()
    {
        var script = Script(
            """
            $stdout.WriteLine('{"type":"started","message":"fake"}')
            $stderr.WriteLine('ready line')
            Start-Sleep -Milliseconds 1500
            $stdout.WriteLine('{"type":"done"}')
            exit 0
            """);

        var events = await CollectAsync(CreateRunner(script).RunAsync(NewJob()));

        var readyIndex = events.FindIndex(e => e.Type == EngineEventType.Log && e.Message == "ready line");
        var doneIndex = events.FindIndex(e => e.Type == EngineEventType.Done);

        Assert.True(readyIndex >= 0, "stderr line was not surfaced");
        Assert.True(doneIndex >= 0, "done event missing");
        Assert.True(readyIndex < doneIndex, "stderr was not streamed before process exit");
        Assert.DoesNotContain(events, e => e.Type == EngineEventType.Error);
    }

    [Fact]
    public async Task MalformedStdoutBecomesDebugLogAndContinues()
    {
        var script = Script(
            """
            $stdout.WriteLine('not json at all')
            $stdout.WriteLine('{"type":"done"}')
            exit 0
            """);

        var events = await CollectAsync(CreateRunner(script).RunAsync(NewJob()));

        Assert.Contains(events, e => e.Type == EngineEventType.Log && e.Level == "debug" && e.Message == "not json at all");
        Assert.Contains(events, e => e.Type == EngineEventType.Done);
        Assert.DoesNotContain(events, e => e.Type == EngineEventType.Error);
    }

    [Fact]
    public async Task ExitCodeOneWithoutErrorProducesEngineError()
    {
        var script = Script(
            """
            $stderr.WriteLine('boom failure')
            exit 1
            """);

        var events = await CollectAsync(CreateRunner(script).RunAsync(NewJob()));

        Assert.Contains(events, e => e.Type == EngineEventType.Error && e.Code == "engine_error");
    }

    [Fact]
    public async Task ExitCodeTwoProducesInputError()
    {
        var script = Script("exit 2\n");

        var events = await CollectAsync(CreateRunner(script).RunAsync(NewJob()));

        Assert.Contains(events, e => e.Type == EngineEventType.Error && e.Code == "input_error");
    }

    [Fact]
    public async Task ZeroExitWithoutDoneProducesExitZeroWithoutDone()
    {
        var script = Script("exit 0\n");

        var events = await CollectAsync(CreateRunner(script).RunAsync(NewJob()));

        Assert.Contains(events, e => e.Type == EngineEventType.Error && e.Code == "exit_0_without_done");
    }

    [Fact]
    public async Task PersianTextIsPreservedOnStdoutAndStderr()
    {
        var script = Script(
            """
            $stderr.WriteLine('خطای فارسی')
            $stdout.WriteLine('{"type":"done","message":"جلسهٔ هفتگی"}')
            exit 0
            """);

        var events = await CollectAsync(CreateRunner(script).RunAsync(NewJob()));

        var done = Assert.Single(events, e => e.Type == EngineEventType.Done);
        Assert.Equal("جلسهٔ هفتگی", done.Message);
        Assert.Contains(events, e => e.Type == EngineEventType.Log && e.Message == "خطای فارسی");
        Assert.DoesNotContain(events, e => e.Message?.Contains('?') == true);
    }

    [Fact]
    public async Task LongStdoutLineIsTruncatedWithWarning()
    {
        var script = Script(
            """
            $stdout.WriteLine('a' * 500)
            $stdout.WriteLine('{"type":"done"}')
            exit 0
            """);

        var events = await CollectAsync(
            CreateRunner(script, options => options.MaxLineLength = 100).RunAsync(NewJob()));

        Assert.Contains(events, e => e.Type == EngineEventType.Log && e.Level == "warning");
        Assert.Contains(events, e => e.Type == EngineEventType.Log && e.Level == "debug" && e.Message?.Length == 100);
    }

    [Fact]
    public async Task CancellationReportsCancelledAndStopsProcess()
    {
        var script = Script(
            """
            $stdout.WriteLine('{"type":"stage","stage":"transcription","status":"running","progress":0.1}')
            $stderr.WriteLine('working')
            Start-Sleep -Seconds 30
            exit 0
            """);

        var runner = CreateRunner(script, options => options.CancelGraceSeconds = 1);
        using var cancellation = new CancellationTokenSource();
        var events = new List<EngineEvent>();
        var stopwatch = Stopwatch.StartNew();

        await foreach (var engineEvent in runner.RunAsync(NewJob(), cancellation.Token))
        {
            events.Add(engineEvent);

            if (engineEvent.Type == EngineEventType.Log && engineEvent.Message == "working")
            {
                await cancellation.CancelAsync();
            }
        }

        stopwatch.Stop();

        Assert.Contains(events, e => e.Type == EngineEventType.Error && e.Code == "cancelled");
        Assert.True(stopwatch.Elapsed < TimeSpan.FromSeconds(20), $"cancellation took {stopwatch.Elapsed}");
    }

    [Fact]
    public async Task ClosedInputPipeIsReportedAndReadingContinues()
    {
        var runner = CreateRunner(Script("exit 0\n"));
        var job = NewJob();

        for (var index = 0; index < 50_000; index++)
        {
            job.SpeakerMap[index] = new SpeakerProfile { Name = new string('x', 40) };
        }

        var events = await CollectAsync(runner.RunAsync(job));

        Assert.Contains(events, e => e.Type == EngineEventType.Error && e.Code == "input_pipe_closed");
    }

    private static string Script(string body) => StreamPreamble + "\n" + body;

    private static EngineJobRequest NewJob() => new()
    {
        JobId = Guid.NewGuid().ToString("N"),
        AudioPath = "audio.wav",
        OutputDirectory = "out",
        Stem = "session"
    };

    private static async Task<List<EngineEvent>> CollectAsync(IAsyncEnumerable<EngineEvent> events)
    {
        var collected = new List<EngineEvent>();

        await foreach (var engineEvent in events)
        {
            collected.Add(engineEvent);
        }

        return collected;
    }

    private static EngineProcessRunner CreateRunner(
        string script,
        Action<EngineClientOptions>? configure = null)
    {
        var directory = Path.Combine(Path.GetTempPath(), "mm-engine-tests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);

        var scriptPath = Path.Combine(directory, "fake-engine.ps1");
        File.WriteAllText(scriptPath, script, new UTF8Encoding(encoderShouldEmitUTF8Identifier: true));

        var spec = new EngineLaunchSpec(
            PowerShellPath(),
            ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", scriptPath],
            directory,
            "fake");

        var options = new EngineClientOptions { LogDirectory = Path.Combine(directory, "logs") };
        configure?.Invoke(options);

        return new EngineProcessRunner(options, new FakeLocator(spec), NullLogger<EngineProcessRunner>.Instance);
    }

    private static string PowerShellPath()
    {
        var systemRoot = Environment.GetEnvironmentVariable("SystemRoot") ?? "C:\\Windows";
        var candidate = Path.Combine(systemRoot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
        return File.Exists(candidate) ? candidate : "powershell.exe";
    }

    private sealed class FakeLocator(EngineLaunchSpec spec) : IEngineLocator
    {
        public EngineLaunchSpec? Locate(EngineClientOptions options) => spec;
    }
}
