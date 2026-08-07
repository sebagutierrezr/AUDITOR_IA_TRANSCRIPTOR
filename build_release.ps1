$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path release) { Remove-Item release -Recurse -Force }
New-Item -ItemType Directory -Path release | Out-Null

Write-Host "VERIFICANDO HUGGING FACE HUB..."
python -c "import huggingface_hub; print('huggingface_hub OK:', huggingface_hub.__version__)"
if ($LASTEXITCODE -ne 0) {
    python -m pip install "huggingface_hub>=0.23,<1.0"
    if ($LASTEXITCODE -ne 0) {
        throw "No fue posible instalar huggingface_hub."
    }
}

Write-Host "DESCARGANDO Y VERIFICANDO MODELOS..."
python "scripts\download_release_models.py"

Write-Host "COMPILANDO APLICACIÓN..."
python -m PyInstaller --clean --noconfirm AUDITOR_IA.spec

$portable = Join-Path `
    $PSScriptRoot `
    "dist\AUDITOR_IA_6.1.0_PORTABLE"

foreach ($folder in @(
    "models",
    "config",
    "data",
    "exports",
    "logs",
    "recordings",
    "temp",
    "engines"
)) {
    New-Item `
        -ItemType Directory `
        -Path (Join-Path $portable $folder) `
        -Force | Out-Null
}

Write-Host "COPIANDO MODELOS OFFLINE..."
Copy-Item `
    "$PSScriptRoot\models\base" `
    "$portable\models\base" `
    -Recurse -Force

Copy-Item `
    "$PSScriptRoot\models\small" `
    "$portable\models\small" `
    -Recurse -Force

Copy-Item `
    "$PSScriptRoot\models\pyannote-community-1" `
    "$portable\models\pyannote-community-1" `
    -Recurse -Force

if (Test-Path "$PSScriptRoot\config\settings.json") {
    Copy-Item `
        "$PSScriptRoot\config\settings.json" `
        "$portable\config\settings.json" `
        -Force
}

if (Test-Path "$PSScriptRoot\config\defaults.json") {
    Copy-Item `
        "$PSScriptRoot\config\defaults.json" `
        "$portable\config\defaults.json" `
        -Force
}

Copy-Item `
    "$PSScriptRoot\ATTRIBUTIONS.md" `
    "$portable\ATTRIBUTIONS.md" `
    -Force

$zip = Join-Path `
    $PSScriptRoot `
    "release\AUDITOR_IA_6.1.0_Portable.zip"

Compress-Archive `
    -Path "$portable\*" `
    -DestinationPath $zip `
    -CompressionLevel Optimal `
    -Force

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if (-not (Test-Path $iscc)) {
    throw "No se encontró Inno Setup: $iscc"
}

& $iscc "installer\AUDITOR_IA.iss"

Write-Host "ARCHIVOS GENERADOS:"
Get-ChildItem release
