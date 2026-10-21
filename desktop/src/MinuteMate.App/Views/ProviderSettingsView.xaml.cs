using System.Windows;
using System.Windows.Controls;
using MinuteMate.App.ViewModels;

namespace MinuteMate.App.Views;

public partial class ProviderSettingsView : UserControl
{
    public ProviderSettingsView()
    {
        InitializeComponent();
    }

    private void ApiKeyBox_Loaded(object sender, RoutedEventArgs e)
    {
        if (sender is PasswordBox box && box.DataContext is ProviderItemViewModel vm && box.Password != vm.ApiKey)
        {
            box.Password = vm.ApiKey;
        }
    }

    private void ApiKeyBox_PasswordChanged(object sender, RoutedEventArgs e)
    {
        if (sender is PasswordBox box && box.DataContext is ProviderItemViewModel vm)
        {
            vm.ApiKey = box.Password;
        }
    }
}
