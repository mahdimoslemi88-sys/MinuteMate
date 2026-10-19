namespace MinuteMate.Core.Contracts;

public sealed class EngineClientOptions
{
    public string? ExecutablePath { get; set; }

    public string? PythonPath { get; set; }

    public string PythonModule { get; set; } = "minutemate";

    public string? WorkingDirectory { get; set; }
}
