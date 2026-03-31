@echo off
REM Fix Docker volume permissions for Windows

echo Fixing directory permissions for Docker on Windows...

REM Create directories if they don't exist
if not exist logs mkdir logs
if not exist sessions mkdir sessions
if not exist data mkdir data
if not exist downloads mkdir downloads

echo Directories created/verified successfully!
echo.
echo Note: On Windows, Docker Desktop handles permissions automatically.
echo If you still have permission issues, try:
echo 1. Restart Docker Desktop
echo 2. In Docker Desktop settings, ensure the drive is shared
echo 3. Run: docker compose down -v
echo 4. Delete logs, sessions, data folders
echo 5. Run: docker compose up -d
echo.
pause
