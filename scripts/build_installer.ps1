param(
    [switch]$SkipEngine
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$app = Join-Path $root "desktop\src\MinuteMate.App"
$publish = Join-Path $app "bin\Release\net8.0-windows\win-x64\publish"
$engineDist = Join-Path $root "engine\dist\minutemate-engine"

if (-not $SkipEngine) {
    & (Join-Path $PSScriptRoot "build_engine.ps1") -Clean
}

dotnet publish (Join-Path $app "MinuteMate.App.csproj") -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -o $publish
if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed ($LASTEXITCODE)"
}

if (-not (Test-Path -LiteralPath $engineDist)) {
    throw "Engine sidecar not built. Run scripts\build_engine.ps1 first or drop -SkipEngine."
}

$targetEngine = Join-Path $publish "engine"
Remove-Item -Recurse -Force $targetEngine -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $targetEngine | Out-Null
Copy-Item -Recurse -Force (Join-Path $engineDist "*") $targetEngine

$isccPath = $null
$isccCommand = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($isccCommand) {
    $isccPath = $isccCommand.Source
}
if (-not $isccPath) {
    $candidate = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path -LiteralPath $candidate) {
        $isccPath = $candidate
    }
}

if (-not $isccPath) {
    Write-Output "publish ready: $publish"
    Write-Output "Inno Setup (iscc.exe) not found. Install it, then run: iscc desktop\installer\MinuteMate.iss"
    exit 0
}

& $isccPath (Join-Path $root "desktop\installer\MinuteMate.iss")
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed ($LASTEXITCODE)"
}
Write-Output "installer: $(Join-Path $root 'dist')"
Copy-Item -Force (Join-Path $root "desktop\installer\README-fa.md") (Join-Path $root "dist\README-Models.md")
