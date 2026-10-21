namespace MinuteMate.Core.Contracts;

public sealed class StorageOptions
{
    public string? OutputDirectory { get; set; }

    public string? SessionsRoot { get; set; }

    public string? ModelsDirectory { get; set; }
}
