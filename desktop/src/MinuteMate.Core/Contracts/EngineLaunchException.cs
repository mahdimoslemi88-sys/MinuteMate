namespace MinuteMate.Core.Contracts;

public sealed class EngineLaunchException : Exception
{
    public EngineLaunchException(string message)
        : base(message)
    {
    }

    public EngineLaunchException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
