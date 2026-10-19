param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Debug"
)

$root = Split-Path -Parent $PSScriptRoot
$solution = Join-Path $root "MinuteMate.Desktop.sln"

dotnet build $solution -c $Configuration
