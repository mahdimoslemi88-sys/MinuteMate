namespace MinuteMate.Core.Infrastructure;

public static class AppPaths
{
    private const string DataDirectoryVariable = "MINUTEMATE_DATA_DIR";

    public static string Root
    {
        get
        {
            var custom = Environment.GetEnvironmentVariable(DataDirectoryVariable);
            if (!string.IsNullOrWhiteSpace(custom))
            {
                return custom;
            }

            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "MinuteMate");
        }
    }

    public static string Models => Path.Combine(Root, "models");

    public static string ResolveModelsDirectory(string? configured)
    {
        if (!string.IsNullOrWhiteSpace(configured))
        {
            return configured;
        }

        var fromEnvironment = Environment.GetEnvironmentVariable("MINUTEMATE_MODELS_DIR");
        if (!string.IsNullOrWhiteSpace(fromEnvironment))
        {
            return fromEnvironment;
        }

        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            var candidate = Path.Combine(current.FullName, "models");
            if (Directory.Exists(Path.Combine(candidate, "whisper")))
            {
                return candidate;
            }

            current = current.Parent;
        }

        return Models;
    }

    public static string Projects => Path.Combine(Root, "projects");

    public static string Logs => Path.Combine(Root, "logs");

    public static string Output => Path.Combine(Root, "output");

    public static string SettingsFile => Path.Combine(Root, "settings.json");

    public static void EnsureCreated()
    {
        Directory.CreateDirectory(Root);
        Directory.CreateDirectory(Models);
        Directory.CreateDirectory(Projects);
        Directory.CreateDirectory(Logs);
        Directory.CreateDirectory(Output);
    }
}
