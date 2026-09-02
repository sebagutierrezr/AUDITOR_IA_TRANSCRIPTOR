$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build,dist,release
python -m PyInstaller --noconfirm --clean AUDITOR_IA.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller fallo.' }
$ffmpeg=$env:AUDITOR_IA_FFMPEG_BIN
if ($ffmpeg) {
  New-Item -ItemType Directory -Force build_assets\ffmpeg | Out-Null
  Copy-Item "$ffmpeg\ffmpeg.exe" build_assets\ffmpeg\ -Force
}
New-Item -ItemType Directory -Force release | Out-Null
& "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe" installer\AUDITOR_IA.iss
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup fallo.' }
