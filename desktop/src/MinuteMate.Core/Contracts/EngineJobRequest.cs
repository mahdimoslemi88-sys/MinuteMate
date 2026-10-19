namespace MinuteMate.Core.Contracts;

public sealed class EngineJobRequest
{
    public string JobId { get; set; } = Guid.NewGuid().ToString("N");

    public string AudioPath { get; set; } = string.Empty;

    public string OutputDirectory { get; set; } = string.Empty;

    public string Stem { get; set; } = "meeting";

    public string Title { get; set; } = string.Empty;

    public DateOnly? Date { get; set; }

    public int NumSpeakers { get; set; } = 4;

    public ComputeDevice Device { get; set; } = ComputeDevice.Auto;

    public string ComputeType { get; set; } = "auto";

    public string Language { get; set; } = "fa";

    public string? FfmpegPath { get; set; }

    public Dictionary<int, SpeakerProfile> SpeakerMap { get; set; } = new();
}
