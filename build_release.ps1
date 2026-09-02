$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host '=== AUDITOR IA 8.0.0 - BUILD RELEASE ==='

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, release

if (-not (Test-Path 'build_assets\nemo-speech\bin\nemo-speech.exe')) {
    throw 'Falta build_assets\nemo-speech\bin\nemo-speech.exe'
}

foreach ($model in @(
    'build_assets\models\nemotron-3.5-asr-streaming-0.6b.q8_0.gguf',
    'build_assets\models\sortformer-v2-q8_0.gguf'
)) {
    if (-not (Test-Path $model)) {
        throw "Falta modelo requerido: $model"
    }
}

$ffmpegBin = $env:AUDITOR_IA_FFMPEG_BIN
if ([string]::IsNullOrWhiteSpace($ffmpegBin)) {
    $ffmpegCommand = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if ($ffmpegCommand) {
        $ffmpegBin = Split-Path $ffmpegCommand.Source
    }
}

if ([string]::IsNullOrWhiteSpace($ffmpegBin) -or -not (Test-Path $ffmpegBin)) {
    throw 'FFmpeg no esta disponible para empaquetar.'
}

$ffmpegExe = Join-Path $ffmpegBin 'ffmpeg.exe'
$ffprobeExe = Join-Path $ffmpegBin 'ffprobe.exe'

if (-not (Test-Path $ffmpegExe)) {
    throw "Falta ffmpeg.exe en $ffmpegBin"
}
if (-not (Test-Path $ffprobeExe)) {
    throw "Falta ffprobe.exe en $ffmpegBin"
}

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue 'build_assets\ffmpeg'
New-Item -ItemType Directory -Force 'build_assets\ffmpeg' | Out-Null
Copy-Item $ffmpegExe 'build_assets\ffmpeg\ffmpeg.exe' -Force
Copy-Item $ffprobeExe 'build_assets\ffmpeg\ffprobe.exe' -Force

& 'build_assets\ffmpeg\ffmpeg.exe' -version
if ($LASTEXITCODE -ne 0) {
    throw 'El ffmpeg.exe empaquetado no pudo ejecutarse.'
}

& 'build_assets\ffmpeg\ffprobe.exe' -version
if ($LASTEXITCODE -ne 0) {
    throw 'El ffprobe.exe empaquetado no pudo ejecutarse.'
}

Write-Host 'Ejecutando PyInstaller...'
python -m PyInstaller --noconfirm --clean AUDITOR_IA.spec
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller fallo.'
}

$distExe = 'dist\AUDITOR_IA_8.0.0_BUILD\AUDITOR_IA.exe'
if (-not (Test-Path $distExe)) {
    throw "PyInstaller termino pero falta $distExe"
}

$distFfmpeg = 'dist\AUDITOR_IA_8.0.0_BUILD\ffmpeg\ffmpeg.exe'
$distFfprobe = 'dist\AUDITOR_IA_8.0.0_BUILD\ffmpeg\ffprobe.exe'
if (-not (Test-Path $distFfmpeg)) {
    throw 'El build final no contiene ffmpeg.exe.'
}
if (-not (Test-Path $distFfprobe)) {
    throw 'El build final no contiene ffprobe.exe.'
}

New-Item -ItemType Directory -Force release | Out-Null

$iscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (-not (Test-Path $iscc)) {
    throw "No se encontro Inno Setup en $iscc"
}

Write-Host 'Creando instalador...'
& $iscc 'installer\AUDITOR_IA.iss'
if ($LASTEXITCODE -ne 0) {
    throw 'Inno Setup fallo.'
}

$setup = 'release\AUDITOR_IA_8.0.0_Setup.exe'
if (-not (Test-Path $setup)) {
    throw 'No se genero release\AUDITOR_IA_8.0.0_Setup.exe'
}

Write-Host '=== BUILD FINALIZADO CORRECTAMENTE ==='
Write-Host $setup
