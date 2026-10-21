using System.IO;
using System.Windows;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using MinuteMate.App.Services;
using MinuteMate.App.ViewModels;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Contracts;
using MinuteMate.Core.Infrastructure;
using MinuteMate.EngineClient;

namespace MinuteMate.App;

public partial class App : Application
{
    private IHost? _host;

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        // Global exception handlers
        AppDomain.CurrentDomain.UnhandledException += CurrentDomain_UnhandledException;
        DispatcherUnhandledException += App_DispatcherUnhandledException;
        TaskScheduler.UnobservedTaskException += TaskScheduler_UnobservedTaskException;

        try
        {
            _host = Host.CreateDefaultBuilder()
                .UseContentRoot(AppContext.BaseDirectory)
                .ConfigureAppConfiguration((_, configuration) =>
                {
                    configuration.SetBasePath(AppContext.BaseDirectory);
                    configuration.AddJsonFile("appsettings.json", optional: true, reloadOnChange: false);
                })
                .ConfigureLogging(logging =>
                {
                    logging.ClearProviders();
                    logging.AddDebug();
                    logging.AddFileLogger();
                    logging.SetMinimumLevel(LogLevel.Debug); // Ensure file logger gets all levels
                })
                .ConfigureServices((context, services) =>
                {
                    services.AddSingleton<ISettingsStore, JsonSettingsStore>();
                    services.AddSingleton<ISessionCatalog, SessionCatalog>();
                    services.AddSingleton<IEngineLocator, EngineLocator>();
                    services.AddSingleton(_ =>
                    {
                        var options = new EngineClientOptions();
                        context.Configuration.GetSection("Engine").Bind(options);
                        return options;
                    });
                    services.AddSingleton(_ =>
                    {
                        var options = new StorageOptions();
                        context.Configuration.GetSection("Storage").Bind(options);
                        options.ModelsDirectory = AppPaths.ResolveModelsDirectory(options.ModelsDirectory);
                        return options;
                    });
                    services.AddSingleton(_ =>
                    {
                        var options = new MinutesOptions();
                        context.Configuration.GetSection("Minutes").Bind(options);
                        return options;
                    });
                    services.AddSingleton<IEngineRunner>(sp => new EngineProcessRunner(
                    sp.GetRequiredService<EngineClientOptions>(),
                    sp.GetRequiredService<IEngineLocator>(),
                    sp.GetRequiredService<ILogger<EngineProcessRunner>>()));
                    services.AddSingleton<IEnginePreflight, EnginePreflight>();
                    services.AddSingleton<IFileDialogService, FileDialogService>();
                    services.AddSingleton<ISettingsDialogService, SettingsDialogService>();
                    services.AddSingleton<MainWindowViewModel>();
                    services.AddSingleton<MainWindow>();
                })
                .Build();

            await _host.StartAsync();

            var window = _host.Services.GetRequiredService<MainWindow>();
            MainWindow = window;
            window.Show();

            var logger = _host.Services.GetRequiredService<ILogger<App>>();
            logger.LogInformation(
                "MinuteMate {Version} started. base={Base}",
                typeof(App).Assembly.GetName().Version?.ToString() ?? "unknown",
                AppContext.BaseDirectory);
        }
        catch (Exception exception)
        {
            LogFatal(exception, "Application startup failed");
            MessageBox.Show(
                exception.Message,
                "MinuteMate",
                MessageBoxButton.OK,
                MessageBoxImage.Error);

            Shutdown(1);
        }
    }

    private void CurrentDomain_UnhandledException(object sender, UnhandledExceptionEventArgs e)
    {
        LogFatal(e.ExceptionObject as Exception ?? new Exception(e.ExceptionObject?.ToString()), "Unhandled exception");
    }

    private void App_DispatcherUnhandledException(object sender, System.Windows.Threading.DispatcherUnhandledExceptionEventArgs e)
    {
        LogFatal(e.Exception, "Dispatcher unhandled exception");

        if (IsRepeating(e.Exception))
        {
            try
            {
                MessageBox.Show(
                    "خطای تکرارشونده در رابط کاربری رخ داد و برنامه بسته می‌شود.\nجزئیات در پوشهٔ logs ذخیره شد.",
                    "MinuteMate",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            catch
            {
            }

            e.Handled = true;
            Shutdown(2);
            return;
        }

        e.Handled = true;
    }

    private string? _lastExceptionKey;
    private int _repeatCount;
    private DateTime _lastExceptionAt;

    private bool IsRepeating(Exception? exception)
    {
        var key = exception?.GetType().FullName + "|" + exception?.Message;
        var now = DateTime.UtcNow;

        if (key == _lastExceptionKey && (now - _lastExceptionAt) < TimeSpan.FromSeconds(10))
        {
            _repeatCount++;
        }
        else
        {
            _repeatCount = 1;
        }

        _lastExceptionKey = key;
        _lastExceptionAt = now;

        return _repeatCount > 5;
    }

    private void TaskScheduler_UnobservedTaskException(object? sender, UnobservedTaskExceptionEventArgs e)
    {
        LogFatal(e.Exception, "Unobserved task exception");
        e.SetObserved(); // Prevent crash
    }

    private void LogFatal(Exception? exception, string context)
    {
        try
        {
            var logger = _host?.Services.GetService(typeof(ILogger<App>)) as ILogger<App>;
            logger?.LogCritical(exception, "{Context}: {Message}", context, exception?.Message);
        }
        catch
        {
            // Fallback: write directly to file
            try
            {
                var logPath = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "MinuteMate", "logs", $"crash-{DateTime.Now:yyyyMMdd-HHmmss}.log");
                Directory.CreateDirectory(Path.GetDirectoryName(logPath)!);
                File.WriteAllText(logPath, $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} [FATAL] [{context}]\n{exception}");
            }
            catch { }
        }
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        if (_host is not null)
        {
            await _host.StopAsync(TimeSpan.FromSeconds(3));
            _host.Dispose();
        }

        base.OnExit(e);
    }
}
