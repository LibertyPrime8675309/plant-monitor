@echo off
rem Double-click this to update the Plant record app from the newest zip in this folder.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update-plant-database.ps1" %*
echo.
pause
