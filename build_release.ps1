$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host '=== AUDITOR IA 8.0.0 - BUILD RELEASE DEFINITIVO ==='

# build_assets se conserva: fue generado y validado por el workflow.
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, release
Remove-Item -Force -ErrorAction SilentlyContinue runtime_self_test_ok.txt, runtime_self_test_error.txt

# -----------------------------------------------------------------------------
# 1) Validar TODO lo que debe terminar dentro del instalador
# -----------------------------------------------------------------------------
$assetRoot = Join-Path $PSScriptRoot 'build_assets'
$requiredAssets = @(
    (Join-Path $assetRoot 'ffmpeg\bin\ffmpeg.exe'),
    (Join-Path $assetRoot 'ffmpeg\bin\ffprobe.exe'),
    (Join-Path $assetRoot 'nemo-speech\bin\nemo-speech.exe'),
    (Join-Path $assetRoot 'models\nemotron-3.5-asr-streaming-0.6b.q8_0.gguf'),
    (Join-Path $assetRoot 'models\sortformer-v2-q8_0.gguf'),
    (Join-Path $assetRoot 'models\small\model.bin'),
    (Join-Path $assetRoot 'models\small\config.json'),
    (Join-Path $assetRoot 'models\small\tokenizer.json')
)

foreach ($required in $requiredAssets) {
    if (-not (Test-Path $required -PathType Leaf)) {
        throw "Falta activo requerido ANTES de PyInstaller: $required"
    }
    if ((Get-Item $required).Length -le 0) {
        throw "Activo vacio ANTES de PyInstaller: $required"
    }
}

foreach ($pattern in @('avcodec-*.dll', 'avformat-*.dll', 'avutil-*.dll', 'swresample-*.dll')) {
    $ffmpegBin = Join-Path $assetRoot 'ffmpeg\bin'
    if (-not (Get-ChildItem -Path $ffmpegBin -Filter $pattern -File -ErrorAction SilentlyContinue | Select-Object -First 1)) {
        throw "FFmpeg Shared incompleto antes de empaquetar. Falta $pattern en $ffmpegBin"
    }
}

Write-Host 'Activos previos OK.'

# -----------------------------------------------------------------------------
# 2) PyInstaller
# -----------------------------------------------------------------------------
Write-Host 'Ejecutando PyInstaller...'
python -m PyInstaller --noconfirm --clean AUDITOR_IA.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller fallo.' }

$distRoot = Join-Path $PSScriptRoot 'dist\AUDITOR_IA_8.0.0_BUILD'
$appExe = Join-Path $distRoot 'AUDITOR_IA.exe'

if (-not (Test-Path $appExe -PathType Leaf)) {
    throw "PyInstaller termino pero no genero: $appExe"
}

# PyInstaller 6 puede usar layout plano o _internal. El spec nuevo fuerza
# layout plano, pero esta deteccion evita volver a romper el build si cambia.
$bundleCandidates = @(
    $distRoot,
    (Join-Path $distRoot '_internal')
)

$bundleRoot = $null
foreach ($candidate in $bundleCandidates) {
    $probe = Join-Path $candidate 'ffmpeg\bin\ffmpeg.exe'
    if (Test-Path $probe -PathType Leaf) {
        $bundleRoot = $candidate
        break
    }
}

if (-not $bundleRoot) {
    Write-Host 'Contenido de dist (primeros 150 archivos):'
    Get-ChildItem -Path $distRoot -Recurse -File -ErrorAction SilentlyContinue |
        Select-Object -First 150 -ExpandProperty FullName |
        ForEach-Object { Write-Host $_ }
    throw 'PyInstaller genero el EXE pero no se encontro la raiz de activos empaquetados.'
}

Write-Host "Raiz de activos empaquetados detectada: $bundleRoot"

$requiredBundled = @(
    (Join-Path $bundleRoot 'ffmpeg\bin\ffmpeg.exe'),
    (Join-Path $bundleRoot 'ffmpeg\bin\ffprobe.exe'),
    (Join-Path $bundleRoot 'nemo-speech\bin\nemo-speech.exe'),
    (Join-Path $bundleRoot 'models\nemotron-3.5-asr-streaming-0.6b.q8_0.gguf'),
    (Join-Path $bundleRoot 'models\sortformer-v2-q8_0.gguf'),
    (Join-Path $bundleRoot 'models\small\model.bin'),
    (Join-Path $bundleRoot 'models\small\config.json'),
    (Join-Path $bundleRoot 'models\small\tokenizer.json'),
    (Join-Path $bundleRoot 'resources\logo.svg')
)

foreach ($required in $requiredBundled) {
    if (-not (Test-Path $required -PathType Leaf)) {
        throw "PyInstaller termino pero falta dentro de dist: $required"
    }
}

Write-Host 'PyInstaller OK: FFmpeg + NeMo + Nemotron + SortFormer + Faster-Whisper + recursos presentes.'

# -----------------------------------------------------------------------------
# 3) Autoprueba REAL del EXE empaquetado
# -----------------------------------------------------------------------------
Write-Host 'Ejecutando autoprueba del EXE empaquetado...'
$oldSelfTest = $env:AUDITOR_IA_SELF_TEST
$env:AUDITOR_IA_SELF_TEST = '1'
try {
    $process = Start-Process -FilePath $appExe -WorkingDirectory $PSScriptRoot -PassThru -Wait
    if ($process.ExitCode -ne 0) {
        $detail = ''
        $errorFile = Join-Path $PSScriptRoot 'runtime_self_test_error.txt'
        if (Test-Path $errorFile) {
            $detail = Get-Content $errorFile -Raw
        }
        throw "Autoprueba del EXE fallo con codigo $($process.ExitCode). $detail"
    }
}
finally {
    if ($null -eq $oldSelfTest) {
        Remove-Item Env:AUDITOR_IA_SELF_TEST -ErrorAction SilentlyContinue
    }
    else {
        $env:AUDITOR_IA_SELF_TEST = $oldSelfTest
    }
}

$okFile = Join-Path $PSScriptRoot 'runtime_self_test_ok.txt'
if (-not (Test-Path $okFile)) {
    throw 'El EXE devolvio codigo 0 pero no genero runtime_self_test_ok.txt.'
}
Write-Host (Get-Content $okFile -Raw)
Write-Host 'Autoprueba del EXE: OK.'

# -----------------------------------------------------------------------------
# 4) Inno Setup
# -----------------------------------------------------------------------------
New-Item -ItemType Directory -Force release | Out-Null

$isccCandidates = @()
if (${env:ProgramFiles(x86)}) {
    $isccCandidates += (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe')
}
if ($env:ProgramFiles) {
    $isccCandidates += (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
}

$iscc = $isccCandidates | Where-Object { Test-Path $_ -PathType Leaf } | Select-Object -First 1
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
if (-not (Test-Path $setup -PathType Leaf)) {
    throw 'Inno Setup termino sin generar release\AUDITOR_IA_8.0.0_Setup.exe.'
}

$setupSize = (Get-Item $setup).Length
if ($setupSize -lt 1MB) {
    throw "El Setup generado parece invalido: $setupSize bytes."
}

Write-Host "=== BUILD COMPLETADO: $setup ($([math]::Round($setupSize / 1MB, 2)) MB) ==="
