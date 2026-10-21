using System;
using System.Globalization;
using System.Windows.Data;

namespace MinuteMate.App.Converters;

public sealed class EnumToStringConverter : IValueConverter
{
    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is Enum e)
        {
            return e.ToString();
        }
        return value?.ToString() ?? string.Empty;
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is string s && targetType.IsEnum)
        {
            try
            {
                return Enum.Parse(targetType, s, true);
            }
            catch
            {
                return Enum.GetValues(targetType).GetValue(0)!;
            }
        }
        return Enum.GetValues(targetType).GetValue(0)!;
    }
}