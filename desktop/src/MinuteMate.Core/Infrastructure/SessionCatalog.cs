using System.Text;
using System.Text.Json;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Models;

namespace MinuteMate.Core.Infrastructure;

public sealed class SessionCatalog : ISessionCatalog
{
    private const int SearchReadLimit = 512 * 1024;

    public IReadOnlyList<SessionSummary> LoadAll(string sessionsRoot, int limit = 200)
    {
        if (string.IsNullOrWhiteSpace(sessionsRoot) || !Directory.Exists(sessionsRoot))
        {
            return [];
        }

        var sessions = new List<SessionSummary>();

        foreach (var directory in Directory.EnumerateDirectories(sessionsRoot))
        {
            var manifestPath = Path.Combine(directory, "session.json");
            var manifest = TryReadManifest(manifestPath);
            if (manifest is null)
            {
                continue;
            }

            sessions.Add(ToSummary(directory, manifest));
        }

        return sessions
            .OrderByDescending(session => session.Date)
            .ThenByDescending(session => session.CreatedAt)
            .ThenByDescending(session => session.Id, StringComparer.Ordinal)
            .Take(limit)
            .ToArray();
    }

    public IReadOnlyList<SessionSummary> Search(string sessionsRoot, string query, int limit = 200)
    {
        var sessions = LoadAll(sessionsRoot, limit);
        var needle = Normalize(query);
        if (needle.Length == 0)
        {
            return sessions;
        }

        var matches = new List<SessionSummary>();
        foreach (var session in sessions)
        {
            if (MatchesMetadata(session, needle) || TranscriptContains(session, needle))
            {
                matches.Add(session);
            }
        }

        return matches;
    }

    private static bool MatchesMetadata(SessionSummary session, string needle)
    {
        return Normalize(session.Title).Contains(needle, StringComparison.Ordinal)
            || Normalize(session.Id).Contains(needle, StringComparison.Ordinal)
            || Normalize(session.Status).Contains(needle, StringComparison.Ordinal)
            || (session.Date is { } date
                && (date.ToString("yyyy-MM-dd").Contains(needle, StringComparison.Ordinal)
                    || date.ToShortDateString().Contains(needle, StringComparison.Ordinal)));
    }

    private static bool TranscriptContains(SessionSummary session, string needle)
    {
        if (session.TranscriptPath is null || !File.Exists(session.TranscriptPath))
        {
            return false;
        }

        try
        {
            using var stream = new FileStream(
                session.TranscriptPath,
                FileMode.Open,
                FileAccess.Read,
                FileShare.ReadWrite);
            using var reader = new StreamReader(stream, Encoding.UTF8, true);
            var buffer = new char[16 * 1024];
            var consumed = 0;
            var overlap = string.Empty;

            while (consumed < SearchReadLimit)
            {
                var read = reader.Read(buffer, 0, buffer.Length);
                if (read <= 0)
                {
                    break;
                }

                consumed += read;
                var text = overlap + new string(buffer, 0, read);
                if (Normalize(text).Contains(needle, StringComparison.Ordinal))
                {
                    return true;
                }

                overlap = text.Length > 512 ? text[^512..] : text;
            }
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }

        return false;
    }

    private static SessionSummary ToSummary(string directory, SessionManifest manifest)
    {
        var outDirectory = Path.Combine(directory, "out");
        var rawDirectory = Path.Combine(directory, "raw");

        var transcript = FirstExisting(
            Path.Combine(outDirectory, "02_diarized_cleaned_transcript.md"),
            Path.Combine(outDirectory, "02_diarized_cleaned_transcript.txt"),
            Path.Combine(outDirectory, "01_raw_transcript.txt"));

        var minutes = FirstExisting(Path.Combine(outDirectory, "03_official_meeting_minutes.md"));

        string? rawAudio = null;
        if (!string.IsNullOrWhiteSpace(manifest.Source.FileName))
        {
            rawAudio = FirstExisting(Path.Combine(rawDirectory, manifest.Source.FileName));
        }

        rawAudio ??= FirstExisting(Directory.Exists(rawDirectory)
            ? Directory.EnumerateFiles(rawDirectory).OrderBy(path => path).FirstOrDefault()
            : null);

        DateOnly? date = DateOnly.TryParse(manifest.Date, out var parsedDate) ? parsedDate : null;

        return new SessionSummary
        {
            Id = string.IsNullOrWhiteSpace(manifest.Id) ? Path.GetFileName(directory) : manifest.Id,
            Title = manifest.Title,
            Date = date,
            CreatedAt = manifest.CreatedAt,
            DurationSeconds = manifest.Source.DurationSeconds ?? 0,
            NumSpeakers = manifest.Run.NumSpeakersDetected > 0
                ? manifest.Run.NumSpeakersDetected
                : manifest.Speakers.Count,
            Status = manifest.Status,
            DirectoryPath = directory,
            TranscriptPath = transcript,
            MinutesPath = minutes,
            RawAudioPath = rawAudio
        };
    }

    private static SessionManifest? TryReadManifest(string manifestPath)
    {
        if (!File.Exists(manifestPath))
        {
            return null;
        }

        try
        {
            using var stream = File.OpenRead(manifestPath);
            return JsonSerializer.Deserialize<SessionManifest>(stream, JsonDefaults.App);
        }
        catch (JsonException)
        {
            return null;
        }
        catch (IOException)
        {
            return null;
        }
        catch (UnauthorizedAccessException)
        {
            return null;
        }
    }

    private static string? FirstExisting(params string?[] candidates)
    {
        return candidates.FirstOrDefault(path => !string.IsNullOrWhiteSpace(path) && File.Exists(path));
    }

    private static string Normalize(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return string.Empty;
        }

        var builder = new StringBuilder(value.Length);
        foreach (var character in value)
        {
            builder.Append(character switch
            {
                'ي' => 'ی',
                'ك' => 'ک',
                '\u200c' => '\0',
                >= '\u06F0' and <= '\u06F9' => (char)('0' + (character - '\u06F0')),
                >= '\u0660' and <= '\u0669' => (char)('0' + (character - '\u0660')),
                _ => character
            });
        }

        return builder.ToString()
            .Replace("\0", string.Empty, StringComparison.Ordinal)
            .Trim()
            .ToLowerInvariant();
    }
}
