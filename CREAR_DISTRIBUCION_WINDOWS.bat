@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title AUDITOR IA 6.0 - CREAR DISTRIBUCION

where py >nul 2>&1
if errorlevel 1 (
  echo Se requiere Python 3.11 para construir la distribucion.
  pause
  exit /b 1
)

py -3.11 -m venv .buildvenv
call .buildvenv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller==6.14.2

where iscc >nul 2>&1
if errorlevel 1 (
  echo.
  echo Falta Inno Setup 6. Instálalo antes de continuar.
  echo https://jrsoftware.org/isdl.php
  pause
  exit /b 1
)

powershell -ExecutionPolicy Bypass -File build_release.ps1
pause
