namespace MinuteMate.Core.Contracts;

public sealed class MinutesOptions
{
    public bool Enabled { get; set; }

    public string Provider { get; set; } = "none";

    public string? BaseUrl { get; set; }

    public string? Model { get; set; }

    public string ApiKeyEnv { get; set; } = "MINUTEMATE_LLM_API_KEY";

    public double Temperature { get; set; } = 0.2;

    public int MaxOutputTokens { get; set; } = 4000;

    public int TimeoutSeconds { get; set; } = 120;

    public int ChunkSeconds { get; set; } = 900;

    public string Language { get; set; } = "fa";

    public string Template { get; set; } = "official-v1";

    public bool IncludeActionItems { get; set; } = true;

    public bool Redact { get; set; }
}
