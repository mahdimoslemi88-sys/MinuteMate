namespace MinuteMate.Core.Contracts;

public sealed class PreflightResult
{
    public string? EngineVersion { get; set; }

    public bool ModelsReady { get; set; }

    public List<string> MissingModels { get; set; } = [];

    public bool Ffmpeg { get; set; }

    public string? FfmpegError { get; set; }

    public string Device { get; set; } = "cpu";

    public string ComputeType { get; set; } = "int8";

    public int GpuCount { get; set; }

    public int BeamSize { get; set; } = 1;

    public int BatchSize { get; set; }

    public string SpeakerEmbedding { get; set; } = "wespeaker";

    public string? ModelsDirectory { get; set; }

    public string RawJson { get; set; } = string.Empty;

    public string? Error { get; set; }
}
