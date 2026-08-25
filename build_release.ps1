$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = "7.2.0"
$env:AUDITOR_IA_PROJECT_ROOT = $PSScriptRoot

if (-not $env:AUDITOR_IA_FFMPEG_BIN) {
    throw "AUDITOR_IA_FFMPEG_BIN no esta configurado."
}

$ffmpegSource = $env:AUDITOR_IA_FFMPEG_BIN
$modelsRoot = Join-Path $PSScriptRoot "models"
$smallModel = Join-Path $modelsRoot "small"
$voiceModel = Join-Path $modelsRoot "pyannote-community-1"
$ecapaModel = Join-Path $modelsRoot "speechbrain-ecapa"
$distRoot = Join-Path $PSScriptRoot "dist"
$buildFolder = Join-Path $distRoot "AUDITOR_IA_7.2.0_BUILD"
$releaseRoot = Join-Path $PSScriptRoot "release"

foreach ($folder in @("build", $distRoot, $releaseRoot)) {
    if (Test-Path $folder) { Remove-Item $folder -Recurse -Force }
}
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
New-Item -ItemType Directory -Path $modelsRoot -Force | Out-Null

Write-Host "CORRIGIENDO SPEECHBRAIN PARA WINDOWS..."
python "$PSScriptRoot\scripts\patch_speechbrain_windows.py"
if ($LASTEXITCODE -ne 0) { throw "SpeechBrain Windows patch fallo." }

Write-Host "DESCARGANDO / VERIFICANDO MODELOS LOCALES..."
python "$PSScriptRoot\scripts\download_release_models.py"
if ($LASTEXITCODE -ne 0) { throw "Fallo descarga/verificacion de modelos." }

Write-Host "VERIFICANDO COMMUNITY-1 Y RUNTIME..."
python -m scripts.verify_native_runtime `
    --ffmpeg-bin "$ffmpegSource" `
    --voice-model "$voiceModel"
if ($LASTEXITCODE -ne 0) { throw "Runtime/modelos no validos." }

Write-Host "VERIFICANDO ECAPA LOCAL..."
python -m scripts.verify_speaker_rescue_model --model "$ecapaModel"
if ($LASTEXITCODE -ne 0) { throw "ECAPA local no valido." }

Write-Host "COMPILANDO..."
python -m PyInstaller --clean --noconfirm "$PSScriptRoot\AUDITOR_IA.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo." }

$exe = Join-Path $buildFolder "AUDITOR_IA.exe"
if (-not (Test-Path $exe)) { throw "No se genero AUDITOR_IA.exe." }

foreach ($folder in @("models", "config")) {
    New-Item -ItemType Directory -Path (Join-Path $buildFolder $folder) -Force | Out-Null
}
Copy-Item $smallModel (Join-Path $buildFolder "models\small") -Recurse -Force
Copy-Item $voiceModel (Join-Path $buildFolder "models\pyannote-community-1") -Recurse -Force
Copy-Item $ecapaModel (Join-Path $buildFolder "models\speechbrain-ecapa") -Recurse -Force

Write-Host "COPIANDO FFMPEG SHARED..."
$ffmpegTarget = Join-Path $buildFolder "ffmpeg\bin"
New-Item -ItemType Directory -Path $ffmpegTarget -Force | Out-Null
Get-ChildItem $ffmpegSource -File | Where-Object {
    $_.Extension -ieq ".dll" -or $_.Name -ieq "ffmpeg.exe" -or $_.Name -ieq "ffprobe.exe"
} | Copy-Item -Destination $ffmpegTarget -Force

foreach ($pattern in @("avcodec-*.dll", "avformat-*.dll", "avutil-*.dll", "swresample-*.dll")) {
    if (-not (Get-ChildItem $ffmpegTarget -Filter $pattern -File)) {
        throw "FFmpeg empaquetado incompleto: $pattern"
    }
}

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { throw "Inno Setup no instalado." }
& $iscc "$PSScriptRoot\installer\AUDITOR_IA.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup fallo." }

$setup = Join-Path $releaseRoot "AUDITOR_IA_7.2.0_Setup.exe"
if (-not (Test-Path $setup)) { throw "Setup no generado." }

$bytes = (Get-Item $setup).Length
$gb = [Math]::Round($bytes / 1GB, 2)
Write-Host "AUDITOR_IA_7.2.0_Setup.exe: $gb GB"
if ($bytes -ge 2GB) { throw "El instalador supera 2 GiB y no puede publicarse como un único asset." }

Write-Host "BUILD COMPLETADO. SOLO SETUP WINDOWS."
