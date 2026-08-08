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

Write-Host "VERIFICANDO HUGGING FACE HUB..."
python -c "import huggingface_hub; print('huggingface_hub OK:', huggingface_hub.__version__)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "INSTALANDO huggingface_hub..."
    python -m pip install "huggingface_hub>=0.23,<1.0"

    if ($LASTEXITCODE -ne 0) {
        throw "No fue posible instalar huggingface_hub."
    }
}

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

$portable = Join-Path $PSScriptRoot "dist\AUDITOR_IA_6.1.1_PORTABLE"

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

Write-Host "CALCULANDO TAMANO DE CARPETA PORTABLE..."
$portableBytes = (
    Get-ChildItem $portable -Recurse -File |
    Measure-Object -Property Length -Sum
).Sum
$portableGB = [Math]::Round($portableBytes / 1GB, 2)
Write-Host "TAMANO PORTABLE SIN COMPRIMIR: $portableGB GB"

$sevenZipCandidates = @(
    "C:\Program Files\7-Zip\7z.exe",
    "C:\Program Files (x86)\7-Zip\7z.exe"
)
$sevenZip = $sevenZipCandidates |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $sevenZip) {
    $sevenZipCommand = Get-Command 7z.exe -ErrorAction SilentlyContinue
    if ($sevenZipCommand) {
        $sevenZip = $sevenZipCommand.Source
    }
}

if (-not $sevenZip) {
    throw "No se encontro 7-Zip en el runner."
}

Write-Host "7-ZIP: $sevenZip"

$portableZip = Join-Path `
    $PSScriptRoot `
    "release\AUDITOR_IA_6.1.1_Portable.zip"

if (Test-Path $portableZip) {
    Remove-Item $portableZip -Force
}

Write-Host "COMPRIMIENDO PORTABLE CON 7-ZIP..."
Push-Location $portable
& $sevenZip a `
    -tzip `
    -mx=5 `
    -mmt=on `
    $portableZip `
    ".\*"
$zipExit = $LASTEXITCODE
Pop-Location

if ($zipExit -ne 0) {
    throw "7-Zip no pudo generar el archivo portable. Codigo: $zipExit"
}

if (-not (Test-Path $portableZip)) {
    throw "No se genero el ZIP portable."
}

$portableZipBytes = (Get-Item $portableZip).Length
$portableZipGB = [Math]::Round($portableZipBytes / 1GB, 2)
Write-Host "PORTABLE ZIP: $portableZipGB GB"

# GitHub Release: 2 GiB max por asset.
$githubLimit = 2GB

if ($portableZipBytes -ge $githubLimit) {
    throw "El Portable ZIP pesa $portableZipGB GB y supera el limite de 2 GiB de GitHub Releases."
}

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if (-not (Test-Path $iscc)) {
    throw "No se encontro Inno Setup: $iscc"
}

Write-Host "GENERANDO INSTALADOR..."
& $iscc "$PSScriptRoot\installer\AUDITOR_IA.iss"

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup no pudo generar el instalador."
}

$setupFile = Join-Path `
    $PSScriptRoot `
    "release\AUDITOR_IA_6.1.1_Setup.exe"

if (-not (Test-Path $setupFile)) {
    throw "No se genero el instalador esperado: $setupFile"
}

$setupBytes = (Get-Item $setupFile).Length
$setupGB = [Math]::Round($setupBytes / 1GB, 2)

Write-Host "SETUP EXE: $setupGB GB"

if ($setupBytes -ge $githubLimit) {
    throw "El Setup pesa $setupGB GB y supera el limite de 2 GiB de GitHub Releases."
}

Write-Host ""
Write-Host "=============================================="
Write-Host "BUILD COMPLETADO"
Write-Host "Portable ZIP: $portableZipGB GB"
Write-Host "Setup EXE:    $setupGB GB"
Write-Host "Ambos archivos estan bajo el limite de GitHub."
Write-Host "=============================================="
Write-Host ""

Get-ChildItem "$PSScriptRoot\release" |
    Select-Object Name, Length
