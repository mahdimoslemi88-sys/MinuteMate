#define MyAppName "MinuteMate"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "MinuteMate"
#define MyAppExeName "MinuteMate.exe"
#define PublishDir "..\src\MinuteMate.App\bin\Release\net8.0-windows\win-x64\publish"

[Setup]
AppId={{7A1F3C2E-9B44-4D7A-9E61-2C8C5B0E4A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=MinuteMate-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DiskSpanning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#PublishDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "env.sample"; DestDir: "{app}"; DestName: ".env"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "README-fa.md"; DestDir: "{app}"; DestName: "README-Models.md"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{group}\Models guide"; Filename: "{app}\README-Models.md"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\engine"
Type: filesandordirs; Name: "{app}\logs"

[Code]
const
  URL_WHISPER = 'https://huggingface.co/deepdml/faster-whisper-large-v3-turbo/tree/main';
  URL_PERSIAN = 'https://huggingface.co/AmirMohseni/whisper-large-v3-persian-ct2-int8/tree/main';
  URL_DIARIZATION = 'https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models';

var
  ModelsPage: TInputOptionWizardPage;
  DownloadPage: TOutputProgressWizardPage;
  LinkWhisper, LinkDiarization, LinkPersian: TNewStaticText;
  ErrorCode: Integer;

procedure OpenUrl(const Url: String);
begin
  ShellExec('open', Url, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;

procedure WhisperLinkClick(Sender: TObject);
begin
  OpenUrl(URL_WHISPER);
end;

procedure PersianLinkClick(Sender: TObject);
begin
  OpenUrl(URL_PERSIAN);
end;

procedure DiarizationLinkClick(Sender: TObject);
begin
  OpenUrl(URL_DIARIZATION);
end;

function MakeLink(Parent: TWinControl; const Caption: String; Top: Integer; OnClick: TNotifyEvent): TNewStaticText;
begin
  Result := TNewStaticText.Create(Parent);
  Result.Parent := Parent;
  Result.Left := 0;
  Result.Top := Top;
  Result.Caption := Caption;
  Result.Font.Color := clBlue;
  Result.Font.Style := [fsUnderline];
  Result.Cursor := crHand;
  Result.OnClick := OnClick;
end;

procedure InitializeWizard;
begin
  ModelsPage := CreateInputOptionPage(wpSelectTasks,
    'AI models (downloaded separately)',
    'The app ships without AI models to keep the download small.',
    'Select the models to download now. Each model is fetched once and works offline afterwards. ' +
    'Unchecked models can be downloaded later from the Models guide in the Start menu.',
    False, False);
  ModelsPage.Add('Whisper Large-v3-Turbo - speech recognition (~1.6 GB)');
  ModelsPage.Add('Speaker diarization - segmentation + voice embeddings (~80 MB)');
  ModelsPage.Add('Persian high-accuracy model - optional (~1.5 GB)');
  ModelsPage.CheckListBox.Checked[0] := True;
  ModelsPage.CheckListBox.Checked[1] := True;
  ModelsPage.CheckListBox.Checked[2] := False;

  LinkWhisper := MakeLink(ModelsPage.Surface, 'Whisper turbo download page (Hugging Face)', 0, @WhisperLinkClick);
  LinkDiarization := MakeLink(ModelsPage.Surface, 'Speaker diarization download page (GitHub)', 0, @DiarizationLinkClick);
  LinkPersian := MakeLink(ModelsPage.Surface, 'Persian model download page (Hugging Face)', 0, @PersianLinkClick);
  Log(Format('models page ready: whisper=%d diarization=%d persian=%d', [
    Ord(ModelsPage.CheckListBox.Checked[0]),
    Ord(ModelsPage.CheckListBox.Checked[1]),
    Ord(ModelsPage.CheckListBox.Checked[2])]));
end;

procedure CurPageChanged(CurPageID: Integer);
var
  Top: Integer;
begin
  if (ModelsPage = nil) or (CurPageID <> ModelsPage.ID) then
    Exit;
  Top := ModelsPage.Surface.Height - ScaleY(86);
  if Top < ScaleY(120) then
    Top := ScaleY(120);
  LinkWhisper.Top := Top;
  LinkDiarization.Top := Top + ScaleY(20);
  LinkPersian.Top := Top + ScaleY(40);
end;

function ModelCount: Integer;
begin
  Result := 0;
  if ModelsPage.CheckListBox.Checked[0] then Result := Result + 1;
  if ModelsPage.CheckListBox.Checked[1] then Result := Result + 1;
  if ModelsPage.CheckListBox.Checked[2] then Result := Result + 1;
end;

function DownloadGroup(const Group, Title: String; Step, Total: Integer): Boolean;
var
  ResultCode: Integer;
  EngineExe, Parameters: String;
begin
  EngineExe := ExpandConstant('{app}\engine\minutemate-engine.exe');
  Parameters := 'models download --group ' + Group +
    ' --models-dir "' + ExpandConstant('{app}\engine\models') + '"';

  DownloadPage.SetText(Title, 'Downloading ' + Title + '. A console window shows the transfer progress.');
  DownloadPage.SetProgress(Step - 1, Total);

  Result := Exec(EngineExe, Parameters, '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
  if (not Result) or (ResultCode <> 0) then
  begin
    if MsgBox('Downloading "' + Title + '" did not finish.' + #13#10#13#10 +
      'You can retry later from Start menu > MinuteMate > Models guide, ' +
      'or download the files manually from the links listed there.' + #13#10#13#10 +
      'Continue with the installation?', mbConfirmation, MB_YESNO) = IDNO then
      Abort;
  end;
  DownloadPage.SetProgress(Step, Total);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Total, Step: Integer;
begin
  if CurStep <> ssPostInstall then
    Exit;
  if WizardSilent then
    Exit;

  Total := ModelCount;
  if Total = 0 then
    Exit;

  DownloadPage := CreateOutputProgressPage('Downloading AI models',
    'This can take several minutes on a slow connection.');
  DownloadPage.Show;
  try
    Step := 0;
    if ModelsPage.CheckListBox.Checked[0] then
    begin
      Step := Step + 1;
      DownloadGroup('whisper', 'Whisper Large-v3-Turbo (1.6 GB)', Step, Total);
    end;
    if ModelsPage.CheckListBox.Checked[1] then
    begin
      Step := Step + 1;
      DownloadGroup('diarization', 'Speaker diarization (80 MB)', Step, Total);
    end;
    if ModelsPage.CheckListBox.Checked[2] then
    begin
      Step := Step + 1;
      DownloadGroup('whisper-fa', 'Persian high-accuracy model (1.5 GB)', Step, Total);
    end;
  finally
    DownloadPage.Hide;
  end;
end;
