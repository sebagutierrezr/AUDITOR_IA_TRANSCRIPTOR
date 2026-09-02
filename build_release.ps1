$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host '=== AUDITOR IA 8.0.0 - BUILD RELEASE ==='

# No borrar build_assets: contiene NeMo-Speech y los modelos creados por el workflow.
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, release

# -----------------------------------------------------------------------------
# 1) Validar activos nativos antes de empaquetar
# -----------------------------------------------------------------------------
$nemoExe = Join-Path $PSScriptRoot 'build_assets\nemo-speech\bin\nemo-speech.exe'
$asrModel = Join-Path $PSScriptRoot 'build_assets\models\nemotron-3.5-asr-streaming-0.6b.q8_0.gguf'
$diarModel = Join-Path $PSScriptRoot 'build_assets\models\sortformer-v2-q8_0.gguf'

foreach ($required in @($nemoExe, $asrModel, $diarModel)) {
    if (-not (Test-Path $required)) {
        throw "Falta activo requerido para el instalador: $required"
    }
}

# -----------------------------------------------------------------------------
# 2) Copiar FFmpeg Shared ANTES de ejecutar PyInstaller.
#    AUDITOR_IA.spec incluye build_assets/ffmpeg dentro del programa.
#    main.py espera encontrarlo en ffmpeg/bin.
# -----------------------------------------------------------------------------
$ffmpegBin = $env:AUDITOR_IA_FFMPEG_BIN
if ([string]::IsNullOrWhiteSpace($ffmpegBin)) {
    throw 'AUDITOR_IA_FFMPEG_BIN no esta definido. El workflow debe preparar FFmpeg primero.'
}

$ffmpegBin = (Resolve-Path $ffmpegBin).Path
$ffmpegExe = Join-Path $ffmpegBin 'ffmpeg.exe'
$ffprobeExe = Join-Path $ffmpegBin 'ffprobe.exe'

if (-not (Test-Path $ffmpegExe)) { throw "Falta ffmpeg.exe en $ffmpegBin" }
if (-not (Test-Path $ffprobeExe)) { throw "Falta ffprobe.exe en $ffmpegBin" }

foreach ($pattern in @('avcodec-*.dll', 'avformat-*.dll', 'avutil-*.dll', 'swresample-*.dll')) {
    if (-not (Get-ChildItem -Path $ffmpegBin -Filter $pattern -File -ErrorAction SilentlyContinue | Select-Object -First 1)) {
        throw "FFmpeg Shared incompleto. Falta $pattern en $ffmpegBin"
    }
}

$ffmpegTarget = Join-Path $PSScriptRoot 'build_assets\ffmpeg\bin'
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $PSScriptRoot 'build_assets\ffmpeg')
New-Item -ItemType Directory -Force $ffmpegTarget | Out-Null
Copy-Item -Path (Join-Path $ffmpegBin '*') -Destination $ffmpegTarget -Recurse -Force

if (-not (Test-Path (Join-Path $ffmpegTarget 'ffmpeg.exe'))) {
    throw 'FFmpeg no quedo copiado dentro de build_assets\ffmpeg\bin.'
}

Write-Host "FFmpeg empaquetable: $ffmpegTarget"
& (Join-Path $ffmpegTarget 'ffmpeg.exe') -version | Select-Object -First 1

# -----------------------------------------------------------------------------
# 3) PyInstaller
# -----------------------------------------------------------------------------
Write-Host 'Ejecutando PyInstaller...'
python -m PyInstaller --noconfirm --clean AUDITOR_IA.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller fallo.' }

$distRoot = Join-Path $PSScriptRoot 'dist\AUDITOR_IA_8.0.0_BUILD'
$appExe = Join-Path $distRoot 'AUDITOR_IA.exe'
$bundledFfmpeg = Join-Path $distRoot 'ffmpeg\bin\ffmpeg.exe'
$bundledFfprobe = Join-Path $distRoot 'ffmpeg\bin\ffprobe.exe'
$bundledNemo = Join-Path $distRoot 'nemo-speech\bin\nemo-speech.exe'
$bundledAsr = Join-Path $distRoot 'models\nemotron-3.5-asr-streaming-0.6b.q8_0.gguf'
$bundledDiar = Join-Path $distRoot 'models\sortformer-v2-q8_0.gguf'

foreach ($required in @($appExe, $bundledFfmpeg, $bundledFfprobe, $bundledNemo, $bundledAsr, $bundledDiar)) {
    if (-not (Test-Path $required)) {
        throw "PyInstaller termino, pero falta dentro de dist: $required"
    }
}

Write-Host 'PyInstaller OK. FFmpeg, NeMo-Speech y modelos quedaron dentro de dist.'

# -----------------------------------------------------------------------------
# 4) Inno Setup
# -----------------------------------------------------------------------------
New-Item -ItemType Directory -Force release | Out-Null

$isccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
) | Where-Object { $_ -and (Test-Path $_) }

$iscc = $isccCandidates | Select-Object -First 1
if (-not $iscc) {
    $cmd = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}

if (-not $iscc) {
    throw 'No se encontro ISCC.exe de Inno Setup 6 en el runner.'
}

Write-Host "Inno Setup: $iscc"
& $iscc 'installer\AUDITOR_IA.iss'
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup fallo.' }

$setup = Join-Path $PSScriptRoot 'release\AUDITOR_IA_8.0.0_Setup.exe'
if (-not (Test-Path $setup)) {
    throw 'Inno Setup termino sin generar release\AUDITOR_IA_8.0.0_Setup.exe.'
}

$setupSize = (Get-Item $setup).Length
if ($setupSize -lt 1MB) {
    throw "El Setup generado parece invalido: $setupSize bytes."
}

Write-Host "=== BUILD COMPLETADO: $setup ($([math]::Round($setupSize / 1MB, 2)) MB) ==="
