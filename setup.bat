@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title AUDITOR IA 6.0 - INSTALACION

where py >nul 2>&1
if errorlevel 1 goto python_error

py -3.11 --version >nul 2>&1
if errorlevel 1 goto python_error

if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 goto error
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error

".venv\Scripts\python.exe" -m compileall -q app
if errorlevel 1 goto error

echo.
echo INSTALACION COMPLETADA.
echo EJECUTA run.bat.
pause
exit /b 0

:python_error
echo.
echo SE REQUIERE PYTHON 3.11 DE 64 BITS.
pause
exit /b 1

:error
echo.
echo NO SE PUDO COMPLETAR LA INSTALACION.
pause
exit /b 1
