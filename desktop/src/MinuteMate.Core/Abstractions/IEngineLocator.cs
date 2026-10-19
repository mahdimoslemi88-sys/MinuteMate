using MinuteMate.Core.Contracts;

namespace MinuteMate.Core.Abstractions;

public interface IEngineLocator
{
    EngineLaunchSpec? Locate(EngineClientOptions options);
}
