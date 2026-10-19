using MinuteMate.Core.Contracts;

namespace MinuteMate.Core.Abstractions;

public interface IEngineRunner
{
    IAsyncEnumerable<EngineEvent> RunAsync(
        EngineJobRequest request,
        CancellationToken cancellationToken = default);
}
