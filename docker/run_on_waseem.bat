@echo off
title BugSlayers — Load and Run
echo.
echo  ============================================================
echo   BUGSLAYERS — Load Docker Image and Run
echo   Run this on Waseem's laptop after copying the .tar file
echo  ============================================================
echo.

echo [1/2] Loading Docker images from tar file...
echo       (This may take 5-10 minutes for 7GB image)
docker load -i bugslayers_full.tar

echo.
echo [2/2] Starting all services...
docker compose up

echo.
echo  Open your browser at: http://localhost:8000
pause
