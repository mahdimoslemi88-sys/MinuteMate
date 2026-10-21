using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MinuteMate.App.Services;
using MinuteMate.Core.Models;

namespace MinuteMate.App.ViewModels;

public partial class ProviderSettingsViewModel : ObservableObject
{
    private readonly SettingsViewModel _parent;

    public IFileDialogService FileDialogService => _parent.FileDialogService;

    public ObservableCollection<ProviderItemViewModel> Providers { get; } = new();

    public ObservableCollection<LocalModelViewModel> LocalModels { get; } = new();

    public IReadOnlyList<string> ProviderTypes { get; } = ["OpenAI-Compatible", "Anthropic", "Groq", "Together", "Local"];

    public IReadOnlyList<string> Devices { get; } = ["auto", "cuda", "cpu"];

    public IReadOnlyList<string> ComputeTypes { get; } = ["auto", "float16", "int8", "float32"];

    public ProviderSettingsViewModel(SettingsViewModel parent)
    {
        _parent = parent;
        Reload();
    }

    public void Reload()
    {
        Providers.Clear();
        foreach (var provider in _parent.Providers)
        {
            Providers.Add(new ProviderItemViewModel(this, provider));
        }

        LocalModels.Clear();
        foreach (var model in _parent.LocalModels)
        {
            LocalModels.Add(new LocalModelViewModel(this, model));
        }
    }

    [RelayCommand]
    private void AddProvider()
    {
        var model = new ProviderSettings
        {
            Id = Guid.NewGuid().ToString("N"),
            Name = "پرووایدر جدید",
            Type = ProviderType.OpenAICompatible,
            BaseUrl = "https://api.groq.com/openai/v1",
            ModelId = "whisper-large-v3-turbo",
            IsEnabled = true,
            Priority = Providers.Count
        };

        var vm = new ProviderItemViewModel(this, model);
        _parent.Providers.Add(model);
        Providers.Add(vm);
        vm.BeginEdit();
    }

    [RelayCommand]
    private void AddLocalModel()
    {
        var model = new LocalModelSettings
        {
            Id = Guid.NewGuid().ToString("N"),
            Name = "مدل لوکال جدید",
            Device = "auto",
            ComputeType = "auto",
            IsEnabled = true
        };

        var vm = new LocalModelViewModel(this, model);
        _parent.LocalModels.Add(model);
        LocalModels.Add(vm);
        vm.BeginEdit();
    }

    internal void DeleteProvider(ProviderItemViewModel item)
    {
        Providers.Remove(item);
        _parent.Providers.Remove(item.Model);
    }

    internal void DeleteLocalModel(LocalModelViewModel item)
    {
        LocalModels.Remove(item);
        _parent.LocalModels.Remove(item.Model);
    }

    internal void MoveProvider(ProviderItemViewModel item, int offset)
    {
        var index = Providers.IndexOf(item);
        var target = index + offset;
        if (index < 0 || target < 0 || target >= Providers.Count)
        {
            return;
        }

        Providers.Move(index, target);
        _parent.Providers.Remove(item.Model);
        _parent.Providers.Insert(target, item.Model);
    }

    public void SaveAll()
    {
        foreach (var provider in Providers)
        {
            provider.SaveToModel();
        }

        foreach (var model in LocalModels)
        {
            model.SaveToModel();
        }
    }
}

public partial class ProviderItemViewModel : ObservableObject
{
    private readonly ProviderSettingsViewModel _parent;

    public ProviderSettings Model { get; }

    private string _originalName = string.Empty;
    private string _originalBaseUrl = string.Empty;
    private string _originalApiKey = string.Empty;
    private string _originalModelId = string.Empty;
    private ProviderType _originalType;
    private bool _originalIsEnabled;

    [ObservableProperty]
    private string _name = string.Empty;

    [ObservableProperty]
    private string _type = string.Empty;

    [ObservableProperty]
    private string _baseUrl = string.Empty;

    [ObservableProperty]
    private string _apiKey = string.Empty;

    [ObservableProperty]
    private string _modelId = string.Empty;

    [ObservableProperty]
    private bool _isEnabled;

    [ObservableProperty]
    private bool _isEditing;

    public int Priority => Model.Priority;

    public ProviderItemViewModel(ProviderSettingsViewModel parent, ProviderSettings model)
    {
        _parent = parent;
        Model = model;

        _name = model.Name;
        _type = ToDisplay(model.Type);
        _baseUrl = model.BaseUrl;
        _apiKey = model.ApiKey;
        _modelId = model.ModelId;
        _isEnabled = model.IsEnabled;

        CaptureOriginals();
    }

    private void CaptureOriginals()
    {
        _originalName = Name;
        _originalBaseUrl = BaseUrl;
        _originalApiKey = ApiKey;
        _originalModelId = ModelId;
        _originalType = Model.Type;
        _originalIsEnabled = Model.IsEnabled;
    }

    public void BeginEdit()
    {
        CaptureOriginals();
        IsEditing = true;
    }

    [RelayCommand]
    private void Edit() => BeginEdit();

    [RelayCommand]
    private void Save()
    {
        SaveToModel();
        IsEditing = false;
    }

    [RelayCommand]
    private void Cancel()
    {
        Name = _originalName;
        BaseUrl = _originalBaseUrl;
        ApiKey = _originalApiKey;
        ModelId = _originalModelId;
        IsEnabled = _originalIsEnabled;
        Type = ToDisplay(_originalType);
        Model.Type = _originalType;

        if (string.IsNullOrWhiteSpace(_originalName))
        {
            _parent.DeleteProvider(this);
            return;
        }

        IsEditing = false;
    }

    [RelayCommand]
    private void Delete() => _parent.DeleteProvider(this);

    [RelayCommand]
    private void MoveUp() => _parent.MoveProvider(this, -1);

    [RelayCommand]
    private void MoveDown() => _parent.MoveProvider(this, 1);

    public void SaveToModel()
    {
        Model.Name = Name;
        Model.Type = FromDisplay(Type);
        Model.BaseUrl = BaseUrl;
        Model.ApiKey = ApiKey;
        Model.ModelId = ModelId;
        Model.IsEnabled = IsEnabled;
        OnPropertyChanged(nameof(Priority));
    }

    private static string ToDisplay(ProviderType type) => type switch
    {
        ProviderType.OpenAICompatible => "OpenAI-Compatible",
        ProviderType.Anthropic => "Anthropic",
        ProviderType.Groq => "Groq",
        ProviderType.Together => "Together",
        ProviderType.Local => "Local",
        _ => "OpenAI-Compatible"
    };

    private static ProviderType FromDisplay(string? value) => value switch
    {
        "Anthropic" => ProviderType.Anthropic,
        "Groq" => ProviderType.Groq,
        "Together" => ProviderType.Together,
        "Local" => ProviderType.Local,
        _ => ProviderType.OpenAICompatible
    };
}

public partial class LocalModelViewModel : ObservableObject
{
    private readonly ProviderSettingsViewModel _parent;

    public LocalModelSettings Model { get; }

    private string _originalName = string.Empty;
    private string _originalModelPath = string.Empty;
    private string _originalModelId = string.Empty;
    private string _originalDevice = "auto";
    private string _originalComputeType = "auto";
    private bool _originalIsEnabled;

    [ObservableProperty]
    private string _name = string.Empty;

    [ObservableProperty]
    private string _modelPath = string.Empty;

    [ObservableProperty]
    private string _modelId = string.Empty;

    [ObservableProperty]
    private string _device = "auto";

    [ObservableProperty]
    private string _computeType = "auto";

    [ObservableProperty]
    private bool _isEnabled;

    [ObservableProperty]
    private bool _isEditing;

    [ObservableProperty]
    private long _sizeBytes;

    public string SizeText => SizeBytes > 0
        ? $"{SizeBytes / 1024d / 1024d:0.#} MB"
        : "نامشخص";

    public LocalModelViewModel(ProviderSettingsViewModel parent, LocalModelSettings model)
    {
        _parent = parent;
        Model = model;

        _name = model.Name;
        _modelPath = model.ModelPath;
        _modelId = model.ModelId;
        _device = string.IsNullOrWhiteSpace(model.Device) ? "auto" : model.Device;
        _computeType = string.IsNullOrWhiteSpace(model.ComputeType) ? "auto" : model.ComputeType;
        _isEnabled = model.IsEnabled;
        _sizeBytes = model.SizeBytes;

        CaptureOriginals();
    }

    partial void OnSizeBytesChanged(long value) => OnPropertyChanged(nameof(SizeText));

    private void CaptureOriginals()
    {
        _originalName = Name;
        _originalModelPath = ModelPath;
        _originalModelId = ModelId;
        _originalDevice = Device;
        _originalComputeType = ComputeType;
        _originalIsEnabled = IsEnabled;
    }

    public void BeginEdit()
    {
        CaptureOriginals();
        IsEditing = true;
    }

    [RelayCommand]
    private void Edit() => BeginEdit();

    [RelayCommand]
    private void Save()
    {
        SaveToModel();
        IsEditing = false;
    }

    [RelayCommand]
    private void Cancel()
    {
        Name = _originalName;
        ModelPath = _originalModelPath;
        ModelId = _originalModelId;
        Device = _originalDevice;
        ComputeType = _originalComputeType;
        IsEnabled = _originalIsEnabled;

        if (string.IsNullOrWhiteSpace(_originalName) && string.IsNullOrWhiteSpace(_originalModelPath))
        {
            _parent.DeleteLocalModel(this);
            return;
        }

        IsEditing = false;
    }

    [RelayCommand]
    private void Delete() => _parent.DeleteLocalModel(this);

    [RelayCommand]
    private void BrowseModelPath()
    {
        var path = _parent.FileDialogService.PickFolder(ModelPath);
        if (!string.IsNullOrWhiteSpace(path))
        {
            ModelPath = path;
        }
    }

    public void SaveToModel()
    {
        Model.Name = Name;
        Model.ModelPath = ModelPath;
        Model.ModelId = ModelId;
        Model.Device = Device;
        Model.ComputeType = ComputeType;
        Model.IsEnabled = IsEnabled;
        Model.SizeBytes = SizeBytes;
    }
}
