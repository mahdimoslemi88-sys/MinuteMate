param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$engine = Join-Path (Split-Path -Parent $PSScriptRoot) "engine"
Push-Location $engine
try {
    if ($Clean) {
        Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
    }
    python -m PyInstaller --noconfirm --clean minutemate-engine.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed ($LASTEXITCODE)"
    }
    $exe = Join-Path $engine "dist\minutemate-engine\minutemate-engine.exe"
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "Expected executable not found: $exe"
    }
    Write-Output "built: $exe"
}
finally {
    Pop-Location
}
