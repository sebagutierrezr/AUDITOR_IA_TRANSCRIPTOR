@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
 echo [ERROR] NO SE ENCONTRO PYTHON.
 pause
 exit /b 1
)
py -3.11 --version >nul 2>&1
if errorlevel 1 (
 echo [ERROR] NO SE ENCONTRO PYTHON 3.11.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.11 -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
 echo [ERROR] NO FUE POSIBLE PREPARAR EL ENTORNO.
 pause
 exit /b 1
)
echo CONFIGURACION COMPLETADA.
pause
