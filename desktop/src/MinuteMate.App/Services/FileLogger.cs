using System;
using System.IO;
using System.Text;
using System.Threading;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace MinuteMate.App.Services;

public sealed class FileLogger : ILogger
{
    private readonly string _categoryName;
    private readonly FileLogWriter _writer;
    private readonly FileLoggerOptions _options;

    public FileLogger(string categoryName, FileLogWriter writer, FileLoggerOptions options)
    {
        _categoryName = categoryName;
        _writer = writer;
        _options = options;
    }

    public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;

    public bool IsEnabled(LogLevel logLevel)
    {
        if (logLevel < _options.MinLevel)
        {
            return false;
        }

        if (_options.QuietCategories.Any(prefix => _categoryName.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            && logLevel < _options.QuietCategoryMinLevel)
        {
            return false;
        }

        return true;
    }

    public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
    {
        if (!IsEnabled(logLevel))
        {
            return;
        }

        try
        {
            var line = FormatLogEntry(logLevel, formatter(state, exception), exception);
            _writer.Enqueue(line);
        }
        catch
        {
            // Never let logging take down the app.
        }
    }

    private string FormatLogEntry(LogLevel logLevel, string message, Exception? exception)
    {
        var sb = new StringBuilder(message.Length + 96);
        sb.Append('[').Append(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff")).Append("] ");
        sb.Append('[').Append(logLevel.ToString().ToUpperInvariant()).Append("] ");
        sb.Append('[').Append(_categoryName).Append("] ");
        sb.Append(message);

        if (exception != null)
        {
            sb.AppendLine();
            sb.Append(exception);
        }

        return sb.ToString();
    }
}

public sealed class FileLogWriter : IDisposable
{
    private readonly object _gate = new();
    private readonly FileLoggerOptions _options;
    private readonly string _directory;
    private readonly string _basePath;
    private bool _disabled;

    private StreamWriter? _writer;
    private long _size;
    private int _index;

    public FileLogWriter(FileLoggerOptions options)
    {
        _options = options;
        _directory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MinuteMate",
            "logs");
        Directory.CreateDirectory(_directory);
        _basePath = Path.Combine(_directory, $"minutemate-{DateTime.Now:yyyyMMdd}.log");
        Open();
    }

    public void Enqueue(string line)
    {
        lock (_gate)
        {
            if (_disabled)
            {
                return;
            }

            try
            {
                var bytes = Encoding.UTF8.GetByteCount(line) + Environment.NewLine.Length;
                if (_size + bytes > _options.MaxFileSizeBytes)
                {
                    Rotate();
                }

                _writer!.WriteLine(line);
                _writer.Flush();
                _size += bytes;
            }
            catch
            {
                _disabled = true;
            }
        }
    }

    private void Open()
    {
        var stream = new FileStream(_basePath, FileMode.Append, FileAccess.Write, FileShare.ReadWrite);
        _writer = new StreamWriter(stream, new UTF8Encoding(false));
        _writer.AutoFlush = true;
        _size = stream.Length;
    }

    private void Rotate()
    {
        try
        {
            _writer?.Dispose();
            _writer = null;

            if (_index < _options.MaxFiles - 1 && File.Exists(_basePath))
            {
                _index++;
                var rotated = Path.Combine(_directory, $"minutemate-{DateTime.Now:yyyyMMdd}-{_index}.log");
                File.Move(_basePath, rotated, overwrite: true);
            }
            else
            {
                File.Delete(_basePath);
            }

            Open();
        }
        catch
        {
            throw;
        }
    }

    public void Dispose()
    {
        lock (_gate)
        {
            try
            {
                _writer?.Dispose();
            }
            catch
            {
            }

            _writer = null;
            _disabled = true;
        }
    }
}

public class FileLoggerProvider : ILoggerProvider
{
    private readonly FileLogWriter _writer;
    private readonly FileLoggerOptions _options;

    public FileLoggerProvider(IOptions<FileLoggerOptions> options)
    {
        _options = options.Value;
        _writer = new FileLogWriter(_options);
    }

    public ILogger CreateLogger(string categoryName) => new FileLogger(categoryName, _writer, _options);

    public void Dispose() => _writer.Dispose();
}

public class FileLoggerOptions
{
    public LogLevel MinLevel { get; set; } = LogLevel.Information;
    public LogLevel QuietCategoryMinLevel { get; set; } = LogLevel.Warning;
    public string[] QuietCategories { get; set; } =
    [
        "Microsoft",
        "System.Net.Http",
        "Microsoft.Hosting.Lifetime"
    ];
    public long MaxFileSizeBytes { get; set; } = 5 * 1024 * 1024;
    public int MaxFiles { get; set; } = 3;
}
