@echo off
echo ===================================================
echo   EL ORACULO DE ETERNIA - ESCANEO AUTOMATICO
echo ===================================================
date /t & time /t
echo.

cd /d "%~dp0"

echo [1/3] Activando Entorno Virtual...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate
) else (
    echo ERROR: No se encuentra .venv
    pause
    exit /b 1
)

echo [2/3] Iniciando Escaneo Diario y Backup...
python -m src.jobs.daily_scan

echo.
echo [3/3] Fin del Proceso.
echo ===================================================
timeout /t 10
