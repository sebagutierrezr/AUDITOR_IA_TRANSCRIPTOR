@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title AUDITOR IA 6.0

if not exist ".venv\Scripts\python.exe" (
    echo EJECUTA setup.bat PRIMERO.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py

if errorlevel 1 (
    echo.
    echo LA APLICACION SE CERRO CON UN ERROR.
    echo REVISA LA CARPETA logs.
    pause
)
