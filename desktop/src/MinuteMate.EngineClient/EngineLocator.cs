using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Contracts;

namespace MinuteMate.EngineClient;

public sealed class EngineLocator : IEngineLocator
{
    private static readonly string[] ExecutableNames =
    [
        "minutemate-engine.exe",
        "minutemate-engine"
    ];

    public EngineLaunchSpec? Locate(EngineClientOptions options)
    {
        var configured = NormalizePath(options.ExecutablePath);
        if (configured is not null)
        {
            return new EngineLaunchSpec(
                configured,
                ["run", "--job", "-"],
                ResolveWorkingDirectory(options, configured),
                "engine");
        }

        foreach (var name in ExecutableNames)
        {
            var candidate = Path.Combine(AppContext.BaseDirectory, "engine", name);
            if (File.Exists(candidate))
            {
                return new EngineLaunchSpec(
                    candidate,
                    ["run", "--job", "-"],
                    Path.GetDirectoryName(candidate)!,
                    "engine");
            }
        }

        var python = NormalizePath(options.PythonPath)
            ?? FindOnPath("python.exe")
            ?? FindOnPath("python");

        if (python is null)
        {
            return null;
        }

        var module = string.IsNullOrWhiteSpace(options.PythonModule)
            ? "minutemate"
            : options.PythonModule;

        return new EngineLaunchSpec(
            python,
            ["-m", module, "run", "--job", "-"],
            ResolveWorkingDirectory(options, python),
            "python");
    }

    private static string? NormalizePath(string? path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return null;
        }

        var expanded = Environment.ExpandEnvironmentVariables(path.Trim().Trim('"'));
        return File.Exists(expanded) ? Path.GetFullPath(expanded) : null;
    }

    private static string ResolveWorkingDirectory(EngineClientOptions options, string launchFile)
    {
        if (!string.IsNullOrWhiteSpace(options.WorkingDirectory))
        {
            var configured = Environment.ExpandEnvironmentVariables(options.WorkingDirectory.Trim().Trim('"'));
            if (Directory.Exists(configured))
            {
                return Path.GetFullPath(configured);
            }
        }

        var engineDirectory = FindEngineDirectory();
        if (engineDirectory is not null)
        {
            return engineDirectory;
        }

        foreach (var start in new[] { AppContext.BaseDirectory, Directory.GetCurrentDirectory() })
        {
            var current = new DirectoryInfo(start);
            while (current is not null)
            {
                if (File.Exists(Path.Combine(current.FullName, "pipeline.py")))
                {
                    return current.FullName;
                }

                current = current.Parent;
            }
        }

        var fileDirectory = Path.GetDirectoryName(launchFile);
        return string.IsNullOrWhiteSpace(fileDirectory)
            ? AppContext.BaseDirectory
            : fileDirectory;
    }

    private static string? FindEngineDirectory()
    {
        foreach (var start in new[] { AppContext.BaseDirectory, Directory.GetCurrentDirectory() })
        {
            var current = new DirectoryInfo(start);
            while (current is not null)
            {
                var engine = Path.Combine(current.FullName, "engine");
                if (File.Exists(Path.Combine(engine, "pyproject.toml")))
                {
                    return engine;
                }

                current = current.Parent;
            }
        }

        return null;
    }

    private static string? FindOnPath(string fileName)
    {
        var path = Environment.GetEnvironmentVariable("PATH");
        if (string.IsNullOrWhiteSpace(path))
        {
            return null;
        }

        foreach (var directory in path.Split(
                     Path.PathSeparator,
                     StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            try
            {
                var candidate = Path.Combine(directory, fileName);
                if (File.Exists(candidate))
                {
                    return Path.GetFullPath(candidate);
                }
            }
            catch (ArgumentException)
            {
            }
        }

        return null;
    }
}
