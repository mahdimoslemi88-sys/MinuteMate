using MinuteMate.Core.Infrastructure;

namespace MinuteMate.Core.Tests;

public sealed class AppPathsTests
{
    [Fact]
    public void ResolveModelsDirectory_KeepsConfiguredPath()
    {
        var configured = Path.Combine(Path.GetTempPath(), "mm-models-configured");

        Assert.Equal(configured, AppPaths.ResolveModelsDirectory(configured));
    }

    [Fact]
    public void ResolveModelsDirectory_FindsRepositoryModels()
    {
        var previous = Environment.GetEnvironmentVariable("MINUTEMATE_MODELS_DIR");
        Environment.SetEnvironmentVariable("MINUTEMATE_MODELS_DIR", null);

        try
        {
            var resolved = AppPaths.ResolveModelsDirectory(null);

            Assert.True(Directory.Exists(Path.Combine(resolved, "whisper")));
        }
        finally
        {
            Environment.SetEnvironmentVariable("MINUTEMATE_MODELS_DIR", previous);
        }
    }
}
