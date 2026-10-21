using MinuteMate.App.Formatting;
using MinuteMate.Core.Models;

namespace MinuteMate.App.ViewModels;

public sealed class SessionRow
{
    public SessionRow(SessionSummary summary)
    {
        Summary = summary;
    }

    public SessionSummary Summary { get; }

    public string Id => Summary.Id;

    public string Title => string.IsNullOrWhiteSpace(Summary.Title) ? Summary.Id : Summary.Title;

    public string DateText => Summary.Date is { } date ? PersianText.Date(date) : "—";

    public string DurationText => PersianText.Duration(Summary.DurationSeconds);

    public string SpeakerText => Summary.NumSpeakers > 0
        ? $"{PersianText.Number(Summary.NumSpeakers)} گوینده"
        : "گوینده نامشخص";

    public string StatusText => Summary.Status switch
    {
        "minutes" => "صورت‌جلسه آماده",
        "transcribed" => "متن آماده",
        "raw" => "نیمه‌کاره",
        _ => "نامشخص"
    };

    public bool HasMinutes => Summary.MinutesPath is not null;

    public bool CanRerun => Summary.RawAudioPath is not null;
}
