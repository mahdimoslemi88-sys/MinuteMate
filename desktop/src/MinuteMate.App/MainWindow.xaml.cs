using System.Windows;
using MinuteMate.App.ViewModels;

namespace MinuteMate.App;

public partial class MainWindow : Window
{
    public MainWindow(MainWindowViewModel viewModel)
    {
        InitializeComponent();
        DataContext = viewModel;
    }
}
