@echo off
title BugSlayers — Docker Build
echo.
echo  ============================================================
echo   BUGSLAYERS — Full Offline Docker Build
echo   Run this on YOUR laptop (where Qwen is already downloaded)
echo  ============================================================
echo.

set PROJECT=C:\Users\Sana\Hackathons\infineon-hackathon
set DOCKER_DIR=%PROJECT%\docker
set OLLAMA_MODELS=%USERPROFILE%\.ollama\models

echo [1/4] Checking Ollama models folder...
if not exist "%OLLAMA_MODELS%" (
    echo ERROR: Ollama models not found at %OLLAMA_MODELS%
    echo Make sure Ollama is installed and qwen2.5-coder:7b is pulled.
    pause
    exit /b 1
)
echo       Found: %OLLAMA_MODELS%

echo.
echo [2/4] Copying Ollama models into docker build context...
if not exist "%DOCKER_DIR%\ollama_models" mkdir "%DOCKER_DIR%\ollama_models"
xcopy "%OLLAMA_MODELS%" "%DOCKER_DIR%\ollama_models\" /E /I /H /Y
echo       Done.

echo.
echo [3/4] Copying project files into docker build context...
xcopy "%PROJECT%\Server"       "%DOCKER_DIR%\Server\"       /E /I /H /Y
xcopy "%PROJECT%\code"         "%DOCKER_DIR%\code\"         /E /I /H /Y
xcopy "%PROJECT%\gui"          "%DOCKER_DIR%\gui\"          /E /I /H /Y
copy  "%DOCKER_DIR%\app.py"    "%DOCKER_DIR%\gui\backend\app.py" /Y
echo       Done.

echo.
echo [4/4] Building Docker images (this will take 10-20 minutes)...
cd /d "%DOCKER_DIR%"
docker compose build

echo.
echo  ============================================================
echo   Build complete!
echo   Now save the image to a tar file for shipping:
echo.
echo   docker save bugslayers-ollama bugslayers-mcp bugslayers-gui ^
echo     -o bugslayers_full.tar
echo.
echo   Then compress bugslayers_full.tar and ship to Waseem.
echo  ============================================================
pause
