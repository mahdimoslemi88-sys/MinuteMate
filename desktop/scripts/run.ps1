$root = Split-Path -Parent $PSScriptRoot
$project = Join-Path $root "src/MinuteMate.App/MinuteMate.App.csproj"

dotnet run --project $project
