$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$env:AUDITOR_IA_PROJECT_ROOT = $PSScriptRoot
$modelsRoot = Join-Path $PSScriptRoot "models"
$baseModel = Join-Path $modelsRoot "base"
$smallModel = Join-Path $modelsRoot "small"
$voiceModel = Join-Path $modelsRoot "pyannote-community-1"

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path release) { Remove-Item release -Recurse -Force }
New-Item -ItemType Directory -Path release -Force | Out-Null
New-Item -ItemType Directory -Path $modelsRoot -Force | Out-Null

Write-Host "RAIZ DEL PROYECTO: $PSScriptRoot"
Write-Host "CARPETA DE MODELOS: $modelsRoot"
Write-Host "DESCARGANDO Y VERIFICANDO MODELOS..."

python "$PSScriptRoot\scripts\download_release_models.py"
if ($LASTEXITCODE -ne 0) {
    throw "La descarga o verificacion de modelos fallo."
}

$requiredModels = @(
    @{ Name = "BASE"; Path = $baseModel; Marker = "model.bin" },
    @{ Name = "SMALL"; Path = $smallModel; Marker = "model.bin" },
    @{ Name = "VOCES"; Path = $voiceModel; Marker = "config.yaml" }
)

foreach ($model in $requiredModels) {
    $markerPath = Join-Path $model.Path $model.Marker

    if (-not (Test-Path $model.Path)) {
        throw "No existe la carpeta del modelo $($model.Name): $($model.Path)"
    }

    if (-not (Test-Path $markerPath)) {
        throw "El modelo $($model.Name) esta incompleto. Falta: $markerPath"
    }

    Write-Host "MODELO $($model.Name): LISTO"
}

Write-Host "COMPILANDO APLICACION..."
python -m PyInstaller --clean --noconfirm "$PSScriptRoot\AUDITOR_IA.spec"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller no pudo compilar la aplicacion."
}

$portable = Join-Path $PSScriptRoot "dist\AUDITOR_IA_6.1.0_PORTABLE"

if (-not (Test-Path $portable)) {
    throw "No se genero la carpeta portable: $portable"
}

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
Copy-Item $baseModel (Join-Path $portable "models\base") -Recurse -Force
Copy-Item $smallModel (Join-Path $portable "models\small") -Recurse -Force
Copy-Item $voiceModel (Join-Path $portable "models\pyannote-community-1") -Recurse -Force

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

if (Test-Path "$PSScriptRoot\ATTRIBUTIONS.md") {
    Copy-Item `
        "$PSScriptRoot\ATTRIBUTIONS.md" `
        "$portable\ATTRIBUTIONS.md" `
        -Force
}

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
    throw "No se encontro Inno Setup: $iscc"
}

& $iscc "$PSScriptRoot\installer\AUDITOR_IA.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup no pudo generar el instalador."
}

Write-Host "ARCHIVOS GENERADOS:"
Get-ChildItem "$PSScriptRoot\release"
