$root = Split-Path -Parent $PSScriptRoot
$solution = Join-Path $root "MinuteMate.Desktop.sln"

dotnet test $solution
