using System.Text;
using MinuteMate.Core.Infrastructure;

namespace MinuteMate.Core.Tests;

public class SessionCatalogTests
{
    [Fact]
    public void LoadAll_SortsByDateAndSkipsInvalidManifest()
    {
        var root = CreateRoot();

        WriteSession(root, "2026-10-19-b", """
            {"schemaVersion":1,"id":"2026-10-19-b","title":"جلسه ب","date":"2026-10-19","status":"transcribed"}
            """);
        WriteSession(root, "2026-10-20-a", """
            {"schemaVersion":1,"id":"2026-10-20-a","title":"جلسه الف","date":"2026-10-20","status":"minutes"}
            """);
        Directory.CreateDirectory(Path.Combine(root, "broken"));
        File.WriteAllText(Path.Combine(root, "broken", "session.json"), "{not json");

        var sessions = new SessionCatalog().LoadAll(root);

        Assert.Equal(2, sessions.Count);
        Assert.Equal("2026-10-20-a", sessions[0].Id);
        Assert.Equal("2026-10-19-b", sessions[1].Id);
    }

    [Fact]
    public void LoadAll_PopulatesArtifactsAndAudio()
    {
        var root = CreateRoot();
        var directory = WriteSession(root, "2026-10-19-a", """
            {"schemaVersion":1,"id":"2026-10-19-a","title":"جلسه","date":"2026-10-19",
             "source":{"fileName":"meeting.mp3","durationSeconds":90},
             "run":{"numSpeakersDetected":3},"status":"minutes"}
            """);

        Directory.CreateDirectory(Path.Combine(directory, "out"));
        File.WriteAllText(Path.Combine(directory, "out", "02_diarized_cleaned_transcript.md"), "متن");
        File.WriteAllText(Path.Combine(directory, "out", "03_official_meeting_minutes.md"), "صورت‌جلسه");
        Directory.CreateDirectory(Path.Combine(directory, "raw"));
        File.WriteAllText(Path.Combine(directory, "raw", "meeting.mp3"), "audio");

        var session = Assert.Single(new SessionCatalog().LoadAll(root));

        Assert.Equal(90, session.DurationSeconds);
        Assert.Equal(3, session.NumSpeakers);
        Assert.NotNull(session.TranscriptPath);
        Assert.NotNull(session.MinutesPath);
        Assert.NotNull(session.RawAudioPath);
        Assert.EndsWith("meeting.mp3", session.RawAudioPath);
    }

    [Fact]
    public void Search_MatchesTitleAndTranscript()
    {
        var root = CreateRoot();
        var directory = WriteSession(root, "2026-10-19-a", """
            {"schemaVersion":1,"id":"2026-10-19-a","title":"جلسه بودجه","date":"2026-10-19","status":"transcribed"}
            """);
        Directory.CreateDirectory(Path.Combine(directory, "out"));
        File.WriteAllText(
            Path.Combine(directory, "out", "02_diarized_cleaned_transcript.md"),
            "در این جلسه درباره ویژگی‌های نسخهٔ بعدی صحبت شد.");

        var catalog = new SessionCatalog();

        Assert.Single(catalog.Search(root, "بودجه"));
        Assert.Single(catalog.Search(root, "نسخهٔ بعدی"));
        Assert.Empty(catalog.Search(root, "موضوع نامرتبط"));
    }

    [Fact]
    public void Search_NormalizesPersianCharactersAndDigits()
    {
        var root = CreateRoot();
        WriteSession(root, "2026-10-19-a", """
            {"schemaVersion":1,"id":"2026-10-19-a","title":"يك جلسه","date":"2026-10-19","status":"raw"}
            """);

        var sessions = new SessionCatalog().Search(root, "یک");

        Assert.Single(sessions);
    }

    private static string CreateRoot()
    {
        var root = Path.Combine(Path.GetTempPath(), "mm-catalog-tests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        return root;
    }

    private static string WriteSession(string root, string id, string manifestJson)
    {
        var directory = Path.Combine(root, id);
        Directory.CreateDirectory(directory);
        File.WriteAllText(
            Path.Combine(directory, "session.json"),
            manifestJson,
            new UTF8Encoding(false));
        return directory;
    }
}
