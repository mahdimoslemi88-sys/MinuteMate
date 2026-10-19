namespace MinuteMate.Core.Contracts;

public sealed class EngineEvent
{
    public EngineEventType Type { get; set; }

    public EngineStage? Stage { get; set; }

    public string? Status { get; set; }

    public double? Progress { get; set; }

    public double? EtaSeconds { get; set; }

    public string? Level { get; set; }

    public string? Message { get; set; }

    public string? Code { get; set; }

    public string? Hint { get; set; }

    public string? Kind { get; set; }

    public string? Path { get; set; }

    public double? DurationSeconds { get; set; }
}
