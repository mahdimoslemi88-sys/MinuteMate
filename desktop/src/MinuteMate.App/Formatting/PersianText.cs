using System.Globalization;

namespace MinuteMate.App.Formatting;

public static class PersianText
{
    private static readonly char[] PersianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];

    public static string Digits(string value)
    {
        var characters = value.ToCharArray();
        for (var index = 0; index < characters.Length; index++)
        {
            if (characters[index] is >= '0' and <= '9')
            {
                characters[index] = PersianDigits[characters[index] - '0'];
            }
        }

        return new string(characters);
    }

    public static string Number(long value) => Digits(value.ToString(CultureInfo.InvariantCulture));

    public static string Date(DateOnly date) => Digits(date.ToString("yyyy/MM/dd", CultureInfo.InvariantCulture));

    public static string Duration(double seconds)
    {
        if (seconds <= 0)
        {
            return "—";
        }

        var span = TimeSpan.FromSeconds(seconds);
        return span.TotalHours >= 1
            ? Digits($"{(int)span.TotalHours}:{span.Minutes:00}:{span.Seconds:00}")
            : Digits($"{span.Minutes:00}:{span.Seconds:00}");
    }
}
