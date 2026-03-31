@echo off
REM Helper script to authorize Telegram account in Docker (Windows)

echo ==========================================
echo Telegram Authorization (Docker)
echo ==========================================
echo.
echo This will help you authorize your Telegram account
echo.

REM Check if container is running
docker ps | findstr telegram-automation >nul 2>&1
if errorlevel 1 (
    echo Error: telegram-automation container is not running
    echo Start it first with: docker compose up -d
    exit /b 1
)

echo Running authorization script in container...
echo.

docker exec -it telegram-automation python authorize.py

echo.
echo Done! Restarting container...
docker compose restart telegram-automation

echo.
echo Authorization complete. Access dashboard at: http://localhost:8000
pause
