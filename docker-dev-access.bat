@echo off
REM Helper script to access development volumes in Docker on Windows

echo ========================================
echo Docker Development Volume Access
echo ========================================
echo.

if "%1"=="" (
    echo Usage: docker-dev-access.bat [logs^|data^|shell]
    echo.
    echo Commands:
    echo   logs  - View application logs
    echo   data  - Access SQLite database
    echo   shell - Open shell in container
    echo.
    exit /b 1
)

if "%1"=="logs" (
    echo Tailing application logs...
    docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f telegram-automation
    exit /b 0
)

if "%1"=="data" (
    echo Accessing database volume...
    echo To copy database out: docker cp telegram-automation:/app/data/app.db ./app.db
    echo To inspect: docker exec -it telegram-automation ls -la /app/data
    docker exec -it telegram-automation ls -la /app/data
    exit /b 0
)

if "%1"=="shell" (
    echo Opening shell in container...
    docker exec -it telegram-automation /bin/bash
    exit /b 0
)

echo Unknown command: %1
echo Use: docker-dev-access.bat [logs^|data^|shell]
exit /b 1
