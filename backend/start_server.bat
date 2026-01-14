@echo off
echo ========================================
echo   Seega Game - Backend Server
echo ========================================
echo.

REM Verificar si existe el entorno virtual
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias si es necesario
echo Verificando dependencias...
pip install -r requirements.txt --quiet

echo.
echo ========================================
echo   Iniciando servidor en http://0.0.0.0:8000
echo   Documentacion: http://localhost:8000/docs
echo ========================================
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

REM Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
