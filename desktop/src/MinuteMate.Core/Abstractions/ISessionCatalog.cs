using MinuteMate.Core.Models;

namespace MinuteMate.Core.Abstractions;

public interface ISessionCatalog
{
    IReadOnlyList<SessionSummary> LoadAll(string sessionsRoot, int limit = 200);

    IReadOnlyList<SessionSummary> Search(string sessionsRoot, string query, int limit = 200);
}
