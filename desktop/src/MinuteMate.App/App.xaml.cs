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

        try
        {
            _host = Host.CreateDefaultBuilder()
                .UseContentRoot(AppContext.BaseDirectory)
                .ConfigureAppConfiguration((_, configuration) =>
                {
                    configuration.SetBasePath(AppContext.BaseDirectory);
                    configuration.AddJsonFile("appsettings.json", optional: true, reloadOnChange: false);
                })
                .ConfigureLogging(logging => logging.AddDebug())
                .ConfigureServices((context, services) =>
                {
                    services.AddSingleton<ISettingsStore, JsonSettingsStore>();
                    services.AddSingleton<IEngineLocator, EngineLocator>();
                    services.AddSingleton(_ =>
                    {
                        var options = new EngineClientOptions();
                        context.Configuration.GetSection("Engine").Bind(options);
                        return options;
                    });
                    services.AddSingleton<IEngineRunner, EngineProcessRunner>();
                    services.AddSingleton<IFileDialogService, FileDialogService>();
                    services.AddSingleton<MainWindowViewModel>();
                    services.AddSingleton<MainWindow>();
                })
                .Build();

            await _host.StartAsync();

            var window = _host.Services.GetRequiredService<MainWindow>();
            MainWindow = window;
            window.Show();
        }
        catch (Exception exception)
        {
            MessageBox.Show(
                exception.Message,
                "MinuteMate",
                MessageBoxButton.OK,
                MessageBoxImage.Error);

            Shutdown(1);
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
