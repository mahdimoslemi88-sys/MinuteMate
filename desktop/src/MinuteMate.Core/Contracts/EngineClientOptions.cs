namespace MinuteMate.Core.Contracts;

public sealed class EngineClientOptions
{
    public string? ExecutablePath { get; set; }

    public string? PythonPath { get; set; }

    public string PythonModule { get; set; } = "minutemate";

    public string? WorkingDirectory { get; set; }

    public string? LogDirectory { get; set; }

    public double CancelGraceSeconds { get; set; } = 3;

    public int StderrThrottlePerSecond { get; set; } = 10;

    public int MaxLineLength { get; set; } = 64 * 1024;

    public int MaxStderrTailLines { get; set; } = 100;
}
