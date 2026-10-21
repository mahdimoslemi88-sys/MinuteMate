namespace MinuteMate.App.ViewModels;

public sealed record LogEntry(DateTime Timestamp, string Level, string Message)
{
    public string Display => $"{Timestamp:HH:mm:ss}  {Message}";
}
