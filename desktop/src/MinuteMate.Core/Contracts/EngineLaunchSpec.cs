namespace MinuteMate.Core.Contracts;

public sealed record EngineLaunchSpec(
    string FileName,
    IReadOnlyList<string> Arguments,
    string WorkingDirectory,
    string Kind);
