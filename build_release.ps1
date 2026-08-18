$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$env:AUDITOR_IA_PROJECT_ROOT = $PSScriptRoot
$version = "6.1.1"

if (-not $env:AUDITOR_IA_FFMPEG_BIN) {
    throw "AUDITOR_IA_FFMPEG_BIN no configurado."
}

$ffmpegSource = $env:AUDITOR_IA_FFMPEG_BIN
$modelsRoot = Join-Path $PSScriptRoot "models"
$baseModel = Join-Path $modelsRoot "base"
$smallModel = Join-Path $modelsRoot "small"
$voiceModel = Join-Path $modelsRoot "pyannote-community-1"
$distRoot = Join-Path $PSScriptRoot "dist"
$portable = Join-Path $distRoot "AUDITOR_IA_6.1.1_PORTABLE"
$releaseRoot = Join-Path $PSScriptRoot "release"

foreach ($p in @("build", $distRoot, $releaseRoot)) {
    if (Test-Path $p) { Remove-Item $p -Recurse -Force }
}
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
New-Item -ItemType Directory -Path $modelsRoot -Force | Out-Null

Write-Host "DESCARGANDO Y VERIFICANDO MODELOS..."
python "$PSScriptRoot\scripts\download_release_models.py"
if ($LASTEXITCODE -ne 0) { throw "Fallo descarga/verificacion de modelos." }

python "$PSScriptRoot\scripts\verify_native_runtime.py" `
    --ffmpeg-bin "$ffmpegSource" `
    --voice-model "$voiceModel"
if ($LASTEXITCODE -ne 0) { throw "Runtime/modelos no validos." }

Write-Host "COMPILANDO..."
python -m PyInstaller --clean --noconfirm "$PSScriptRoot\AUDITOR_IA.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo." }
if (-not (Test-Path "$portable\AUDITOR_IA.exe")) { throw "No se genero AUDITOR_IA.exe." }

foreach ($folder in @("models","config","data","exports","logs","recordings","temp","engines")) {
    New-Item -ItemType Directory -Path (Join-Path $portable $folder) -Force | Out-Null
}

Copy-Item $baseModel (Join-Path $portable "models\base") -Recurse -Force
Copy-Item $smallModel (Join-Path $portable "models\small") -Recurse -Force
Copy-Item $voiceModel (Join-Path $portable "models\pyannote-community-1") -Recurse -Force

$ffmpegTarget = Join-Path $portable "ffmpeg\bin"
New-Item -ItemType Directory -Path $ffmpegTarget -Force | Out-Null
Get-ChildItem $ffmpegSource -File | Copy-Item -Destination $ffmpegTarget -Force

foreach ($pattern in @("avcodec-*.dll","avformat-*.dll","avutil-*.dll","swresample-*.dll")) {
    if (-not (Get-ChildItem $ffmpegTarget -Filter $pattern -File)) {
        throw "FFmpeg empaquetado incompleto: $pattern"
    }
}

if (Test-Path "$PSScriptRoot\config\settings.json") {
    Copy-Item "$PSScriptRoot\config\settings.json" "$portable\config\settings.json" -Force
}
if (Test-Path "$PSScriptRoot\config\defaults.json") {
    Copy-Item "$PSScriptRoot\config\defaults.json" "$portable\config\defaults.json" -Force
}
if (Test-Path "$PSScriptRoot\ATTRIBUTIONS.md") {
    Copy-Item "$PSScriptRoot\ATTRIBUTIONS.md" "$portable\ATTRIBUTIONS.md" -Force
}

$sevenZip = "C:\Program Files\7-Zip\7z.exe"
if (-not (Test-Path $sevenZip)) { throw "7-Zip no instalado." }
$portableZip = Join-Path $releaseRoot "AUDITOR_IA_6.1.1_Portable.zip"
Push-Location $portable
& $sevenZip a -tzip -mx=5 -mmt=on $portableZip ".\*"
$zipExit = $LASTEXITCODE
Pop-Location
if ($zipExit -ne 0) { throw "7-Zip fallo." }

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { throw "Inno Setup no instalado." }
& $iscc "$PSScriptRoot\installer\AUDITOR_IA.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup fallo." }

$setup = Join-Path $releaseRoot "AUDITOR_IA_6.1.1_Setup.exe"
if (-not (Test-Path $portableZip)) { throw "Portable no generado." }
if (-not (Test-Path $setup)) { throw "Setup no generado." }

$limit = 2GB
foreach ($file in @($portableZip, $setup)) {
    $bytes = (Get-Item $file).Length
    $gb = [Math]::Round($bytes / 1GB, 2)
    Write-Host "$(Split-Path $file -Leaf): $gb GB"
    if ($bytes -ge $limit) { throw "$(Split-Path $file -Leaf) supera 2 GiB." }
}

Write-Host "BUILD COMPLETADO."
