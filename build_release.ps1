$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$env:AUDITOR_IA_PROJECT_ROOT = $PSScriptRoot
$version = "6.1.1"
$portableName = "AUDITOR_IA_${version}_PORTABLE"

$modelsRoot = Join-Path $PSScriptRoot "models"
$baseModel = Join-Path $modelsRoot "base"
$smallModel = Join-Path $modelsRoot "small"
$voiceModel = Join-Path $modelsRoot "pyannote-community-1"

$buildRoot = Join-Path $PSScriptRoot "build"
$distRoot = Join-Path $PSScriptRoot "dist"
$releaseRoot = Join-Path $PSScriptRoot "release"
$portable = Join-Path $distRoot $portableName

if (Test-Path $buildRoot) { Remove-Item $buildRoot -Recurse -Force }
if (Test-Path $distRoot) { Remove-Item $distRoot -Recurse -Force }
if (Test-Path $releaseRoot) { Remove-Item $releaseRoot -Recurse -Force }

New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
New-Item -ItemType Directory -Path $modelsRoot -Force | Out-Null

Write-Host "RAIZ DEL PROYECTO: $PSScriptRoot"
Write-Host "CARPETA DE MODELOS: $modelsRoot"

python -c "import huggingface_hub; print('huggingface_hub OK:', huggingface_hub.__version__)"
if ($LASTEXITCODE -ne 0) {
    python -m pip install "huggingface_hub>=0.23,<1.0"
    if ($LASTEXITCODE -ne 0) { throw "No fue posible instalar huggingface_hub." }
}

python "$PSScriptRoot\scripts\download_release_models.py"
if ($LASTEXITCODE -ne 0) { throw "La descarga o verificacion de modelos fallo." }

$requiredModels = @(
    @{ Name = "BASE"; Path = $baseModel; Marker = "model.bin" },
    @{ Name = "SMALL"; Path = $smallModel; Marker = "model.bin" },
    @{ Name = "VOCES"; Path = $voiceModel; Marker = "config.yaml" }
)

foreach ($model in $requiredModels) {
    $markerPath = Join-Path $model.Path $model.Marker
    if (-not (Test-Path $model.Path)) { throw "No existe la carpeta del modelo $($model.Name): $($model.Path)" }
    if (-not (Test-Path $markerPath)) { throw "El modelo $($model.Name) esta incompleto. Falta: $markerPath" }
    Write-Host "MODELO $($model.Name): LISTO"
}

Write-Host "COMPILANDO APLICACION..."
python -m PyInstaller --clean --noconfirm "$PSScriptRoot\AUDITOR_IA.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller no pudo compilar la aplicacion." }

if (-not (Test-Path $distRoot)) { throw "PyInstaller no genero la carpeta dist." }

Write-Host "DETECTANDO SALIDA DE PYINSTALLER..."
$generatedExe = Get-ChildItem -Path $distRoot -Filter "AUDITOR_IA.exe" -File -Recurse | Select-Object -First 1
if (-not $generatedExe) { throw "No se encontro AUDITOR_IA.exe dentro de dist." }

$generatedFolder = $generatedExe.Directory.FullName
Write-Host "EJECUTABLE ENCONTRADO: $($generatedExe.FullName)"
Write-Host "CARPETA GENERADA: $generatedFolder"

if ($generatedFolder -ne $portable) {
    if (Test-Path $portable) { Remove-Item $portable -Recurse -Force }

    if ($generatedFolder -ne $distRoot) {
        Move-Item -Path $generatedFolder -Destination $portable
    }
    else {
        $temporary = Join-Path $PSScriptRoot "_portable_temp"
        if (Test-Path $temporary) { Remove-Item $temporary -Recurse -Force }
        New-Item -ItemType Directory -Path $temporary -Force | Out-Null
        Get-ChildItem $distRoot | Move-Item -Destination $temporary
        Move-Item -Path $temporary -Destination $portable
    }
}

if (-not (Test-Path $portable)) { throw "No fue posible preparar la carpeta portable: $portable" }
if (-not (Test-Path (Join-Path $portable "AUDITOR_IA.exe"))) { throw "La carpeta portable no contiene AUDITOR_IA.exe." }

foreach ($folder in @("models","config","data","exports","logs","recordings","temp","engines")) {
    New-Item -ItemType Directory -Path (Join-Path $portable $folder) -Force | Out-Null
}

Write-Host "COPIANDO MODELOS OFFLINE..."
Copy-Item $baseModel (Join-Path $portable "models\base") -Recurse -Force
Copy-Item $smallModel (Join-Path $portable "models\small") -Recurse -Force
Copy-Item $voiceModel (Join-Path $portable "models\pyannote-community-1") -Recurse -Force

if (Test-Path "$PSScriptRoot\config\settings.json") {
    Copy-Item "$PSScriptRoot\config\settings.json" "$portable\config\settings.json" -Force
}
if (Test-Path "$PSScriptRoot\config\defaults.json") {
    Copy-Item "$PSScriptRoot\config\defaults.json" "$portable\config\defaults.json" -Force
}
if (Test-Path "$PSScriptRoot\ATTRIBUTIONS.md") {
    Copy-Item "$PSScriptRoot\ATTRIBUTIONS.md" "$portable\ATTRIBUTIONS.md" -Force
}

$portableBytes = (Get-ChildItem $portable -Recurse -File | Measure-Object -Property Length -Sum).Sum
$portableGB = [Math]::Round($portableBytes / 1GB, 2)
Write-Host "TAMANO PORTABLE SIN COMPRIMIR: $portableGB GB"

$sevenZipCandidates = @("C:\Program Files\7-Zip\7z.exe","C:\Program Files (x86)\7-Zip\7z.exe")
$sevenZip = $sevenZipCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $sevenZip) {
    $sevenZipCommand = Get-Command 7z.exe -ErrorAction SilentlyContinue
    if ($sevenZipCommand) { $sevenZip = $sevenZipCommand.Source }
}
if (-not $sevenZip) { throw "No se encontro 7-Zip en el runner." }

$portableZip = Join-Path $releaseRoot "AUDITOR_IA_${version}_Portable.zip"
if (Test-Path $portableZip) { Remove-Item $portableZip -Force }

Push-Location $portable
& $sevenZip a -tzip -mx=5 -mmt=on $portableZip ".\*"
$zipExit = $LASTEXITCODE
Pop-Location

if ($zipExit -ne 0) { throw "7-Zip no pudo generar el archivo portable. Codigo: $zipExit" }
if (-not (Test-Path $portableZip)) { throw "No se genero el ZIP portable." }

$portableZipBytes = (Get-Item $portableZip).Length
$portableZipGB = [Math]::Round($portableZipBytes / 1GB, 2)
$githubLimit = 2GB

Write-Host "PORTABLE ZIP: $portableZipGB GB"
if ($portableZipBytes -ge $githubLimit) { throw "El Portable ZIP pesa $portableZipGB GB y supera el limite de 2 GiB de GitHub Releases." }

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { throw "No se encontro Inno Setup: $iscc" }

& $iscc "$PSScriptRoot\installer\AUDITOR_IA.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup no pudo generar el instalador." }

$setupFile = Join-Path $releaseRoot "AUDITOR_IA_${version}_Setup.exe"
if (-not (Test-Path $setupFile)) {
    Write-Host "ARCHIVOS PRESENTES EN RELEASE:"
    Get-ChildItem $releaseRoot | Select-Object Name, Length
    throw "No se genero el instalador esperado: $setupFile"
}

$setupBytes = (Get-Item $setupFile).Length
$setupGB = [Math]::Round($setupBytes / 1GB, 2)
Write-Host "SETUP EXE: $setupGB GB"

if ($setupBytes -ge $githubLimit) { throw "El Setup pesa $setupGB GB y supera el limite de 2 GiB de GitHub Releases." }

Write-Host ""
Write-Host "=============================================="
Write-Host "BUILD COMPLETADO CORRECTAMENTE"
Write-Host "VERSION: $version"
Write-Host "PORTABLE: $portableZipGB GB"
Write-Host "SETUP: $setupGB GB"
Write-Host "=============================================="
Get-ChildItem $releaseRoot | Select-Object Name, Length