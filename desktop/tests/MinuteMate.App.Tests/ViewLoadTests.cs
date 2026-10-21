using System.Threading;
using System.Windows;
using MinuteMate.App.Services;
using MinuteMate.App.ViewModels;
using MinuteMate.Core.Abstractions;
using MinuteMate.Core.Models;

namespace MinuteMate.App.Tests;

public class ViewLoadTests
{
    [Fact]
    public void SettingsWindow_AndProviderView_LoadWithoutXamlErrors()
    {
        RunOnSta(() =>
        {
            EnsureApplication();

            var settings = new AppSettings
            {
                Providers =
                [
                    new ProviderSettings
                    {
                        Name = "Groq",
                        Type = ProviderType.Groq,
                        BaseUrl = "https://api.groq.com/openai/v1",
                        ApiKey = "test",
                        ModelId = "whisper-large-v3-turbo"
                    }
                ],
                LocalModels =
                [
                    new LocalModelSettings
                    {
                        Name = "turbo",
                        ModelPath = @"C:\models\whisper",
                        Device = "auto",
                        ComputeType = "auto"
                    }
                ]
            };

            var reloaded = new SettingsViewModel(settings, new NoopFileDialogService());

            var window = new SettingsWindow(reloaded);
            try
            {
                window.ApplyTemplate();
                var provider = reloaded.ProviderSettings;
                Assert.Single(provider.Providers);
                Assert.Equal("Groq", provider.Providers[0].Name);
                Assert.Equal("Groq", provider.Providers[0].Type);
                Assert.False(provider.Providers[0].IsEditing);
            }
            finally
            {
                window.Close();
            }
        });
    }

    private static void EnsureApplication()
    {
        if (Application.Current is null)
        {
            var application = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
            application.Resources.MergedDictionaries.Add(new ResourceDictionary
            {
                Source = new Uri("/MinuteMate;component/Themes/Theme.xaml", UriKind.Relative)
            });
        }
    }

    private static void RunOnSta(Action action)
    {
        Exception? failure = null;
        var thread = new Thread(() =>
        {
            try
            {
                action();
            }
            catch (Exception exception)
            {
                failure = exception;
            }
            finally
            {
                System.Windows.Threading.Dispatcher.CurrentDispatcher.InvokeShutdown();
            }
        });

        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        thread.Join(TimeSpan.FromSeconds(60));

        if (failure is not null)
        {
            throw new Xunit.Sdk.XunitException($"STA action failed: {failure}");
        }
    }

    private sealed class NoopFileDialogService : IFileDialogService
    {
        public string? PickAudioFile() => null;

        public string? PickFile(string title, string filter) => null;

        public string? PickFolder(string? initialDirectory = null, string title = "انتخاب پوشه") => null;
    }
}
