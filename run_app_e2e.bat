@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: No se encuentra .venv\Scripts\activate.bat
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

set PYTHONPATH=%CD%
set STEEL_DB_PATH=db\steel_mvp_e2e_sprint7.db

echo.
echo Iniciando Steel MVP en modo E2E Sprint 7...
echo.
echo DB usada: %STEEL_DB_PATH%
echo.
echo Esta app NO usa la DB de produccion.
echo Para cerrar, vuelve a esta ventana y pulsa CTRL+C.
echo.

streamlit run src/ui/app.py

pause
