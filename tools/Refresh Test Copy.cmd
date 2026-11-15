@echo off
rem Plant record test copy (1.58.0): see test-copy.ps1 next to this file.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0test-copy.ps1" -Action Refresh %*
echo.
pause
