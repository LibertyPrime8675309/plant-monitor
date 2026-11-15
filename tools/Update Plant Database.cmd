@echo off
rem Double-click this to update the Plant record app: it fetches the newest release from GitHub (or uses the newest zip here).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update-plant-database.ps1" %*
echo.
pause
