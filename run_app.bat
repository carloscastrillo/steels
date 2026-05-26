@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: No se encuentra .venv\Scripts\activate.bat
    echo Ejecuta primero: python -m venv .venv
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

set PYTHONPATH=%CD%

echo.
echo Iniciando Steel MVP...
echo.
echo La app se abrira en el navegador.
echo Para cerrar, vuelve a esta ventana y pulsa CTRL+C.
echo.

streamlit run src/ui/app.py

pause