$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = "7.0.0"
$distRoot = Join-Path $PSScriptRoot "dist"
$appFolder = Join-Path $distRoot "AUDITOR_IA_7.0.0_APP"
$releaseRoot = Join-Path $PSScriptRoot "release"
$setup = Join-Path $releaseRoot "AUDITOR_IA_7.0.0_Setup.exe"

if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path $distRoot) { Remove-Item $distRoot -Recurse -Force }
if (Test-Path $releaseRoot) { Remove-Item $releaseRoot -Recurse -Force }
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

Write-Host "========================================="
Write-Host " AUDITOR IA 7.0.0 - WINDOWS INSTALLER"
Write-Host "========================================="
Write-Host "Build ligero de alta precisión. Solo instalador Windows."

Write-Host "[1/4] Ejecutando pruebas..."
python -m unittest discover -s tests -p "test_*.py" -v
if ($LASTEXITCODE -ne 0) { throw "Las pruebas fallaron." }

Write-Host "[2/4] Compilando aplicación..."
python -m PyInstaller --clean --noconfirm "$PSScriptRoot\AUDITOR_IA.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló." }

$exe = Join-Path $appFolder "AUDITOR_IA.exe"
if (-not (Test-Path $exe)) { throw "No se generó AUDITOR_IA.exe." }

Write-Host "[3/4] Self-test del EXE real..."
$env:AUDITOR_IA_SELF_TEST = "1"
$process = Start-Process -FilePath $exe -WorkingDirectory $appFolder -Wait -PassThru
Remove-Item Env:AUDITOR_IA_SELF_TEST
if ($process.ExitCode -ne 0) {
    $errorFile = Join-Path $appFolder "runtime_self_test_error.txt"
    if (Test-Path $errorFile) { Get-Content $errorFile }
    throw "El EXE no superó el self-test. ExitCode=$($process.ExitCode)"
}
$okFile = Join-Path $appFolder "runtime_self_test_ok.txt"
if (Test-Path $okFile) { Get-Content $okFile }

Write-Host "[4/4] Creando instalador..."
$isccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 no está instalado." }

& $iscc "$PSScriptRoot\installer\AUDITOR_IA.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló." }
if (-not (Test-Path $setup)) { throw "No se generó $setup" }

$sizeMb = [Math]::Round((Get-Item $setup).Length / 1MB, 1)
Write-Host "INSTALADOR LISTO: AUDITOR_IA_7.0.0_Setup.exe ($sizeMb MB)"
