$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path release) { Remove-Item release -Recurse -Force }
New-Item -ItemType Directory -Path release | Out-Null

python -m PyInstaller --clean --noconfirm AUDITOR_IA.spec

$portable = Join-Path $PSScriptRoot "dist\AUDITOR_IA_6.0_PORTABLE"
foreach ($folder in @("models","config","data","exports","logs","recordings","temp","engines")) {
    New-Item -ItemType Directory -Path (Join-Path $portable $folder) -Force | Out-Null
}

$zip = Join-Path $PSScriptRoot "release\AUDITOR_IA_6.0_Portable.zip"
Compress-Archive -Path "$portable\*" -DestinationPath $zip -CompressionLevel Optimal -Force

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    throw "No se encontró Inno Setup: $iscc"
}
& $iscc "installer\AUDITOR_IA.iss"

Write-Host "ARCHIVOS GENERADOS:"
Get-ChildItem release
