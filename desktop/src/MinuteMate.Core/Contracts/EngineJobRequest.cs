namespace MinuteMate.Core.Contracts;

public sealed class EngineJobRequest
{
    public string JobId { get; set; } = Guid.NewGuid().ToString("N");

    public string AudioPath { get; set; } = string.Empty;

    public string OutputDirectory { get; set; } = string.Empty;

    public string? SessionDirectory { get; set; }

    public string? SessionsRoot { get; set; }

    public string? MetricsDirectory { get; set; }

    public string Stem { get; set; } = "meeting";

    public string Title { get; set; } = string.Empty;

    public DateOnly? Date { get; set; }

    public int NumSpeakers { get; set; } = 4;

    public ComputeDevice Device { get; set; } = ComputeDevice.Auto;

    public string ComputeType { get; set; } = "auto";

    public int? BatchSize { get; set; }

    public double? AsrChunkSeconds { get; set; }

    public double? AsrChunkOverlapSeconds { get; set; }

    public string? ParallelStages { get; set; }

    public bool? AutoDownloadModels { get; set; }

    public string? SpeakerEmbedding { get; set; }

    public string Language { get; set; } = "fa";

    public string? AsrModel { get; set; }

    public string? FfmpegPath { get; set; }

    public string? ModelsDir { get; set; }

    public Dictionary<int, SpeakerProfile> SpeakerMap { get; set; } = new();

    public MinutesOptions? Minutes { get; set; }
}
