$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python not found in PATH."
}

python -m pip install -r requirements.txt

$requiredAssets = @(
    "assets\fonts\IRANYekanX-Regular.ttf",
    "assets\icons\app-icon.png",
    "assets\icons\chevron-down.svg"
)
foreach ($relativePath in $requiredAssets) {
    $fullPath = Join-Path $PSScriptRoot $relativePath
    if (-not (Test-Path $fullPath)) {
        throw "Missing bundled asset: $relativePath — see assets/ASSETS.md"
    }
}

$iconIco = Join-Path $PSScriptRoot "assets\icons\app-icon.ico"
$iconPng = Join-Path $PSScriptRoot "assets\icons\app-icon.png"
if (-not (Test-Path $iconIco)) {
    Write-Host "Generating app-icon.ico from app-icon.png..."
    python -c "from PIL import Image; img=Image.open(r'$iconPng'); img.save(r'$iconIco', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
}

python -m PyInstaller --noconfirm ai-api-key-setter.spec

Write-Host ""
Write-Host "Build complete:"
Write-Host "  dist\ai-api-key-setter.exe"
