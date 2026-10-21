using MinuteMate.Core.Contracts;

namespace MinuteMate.Core.Abstractions;

public interface IEnginePreflight
{
    Task<PreflightResult> RunAsync(
        string device,
        string computeType,
        string? modelsDirectory,
        CancellationToken cancellationToken = default);
}
