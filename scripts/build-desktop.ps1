param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$desktopApp = Join-Path $projectRoot "desktop-app"
$artifacts = Join-Path $projectRoot "release-artifacts\\desktop"
$buildPath = Join-Path $projectRoot "build\\pyinstaller"

python -m pip install -r (Join-Path $desktopApp "requirements-build.txt")
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "MousePhone-$Version" --paths (Join-Path $desktopApp "src") --distpath $artifacts --workpath $buildPath --specpath $buildPath --collect-all pyautogui --collect-all qrcode (Join-Path $desktopApp "server.py")

Write-Host "Ejecutable creado en $artifacts"
