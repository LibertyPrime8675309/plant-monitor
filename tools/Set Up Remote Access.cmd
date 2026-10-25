@echo off
rem Double-click this to set up or check using Plant record away from home (Tailscale). See README.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-remote-access.ps1" %*
echo.
pause
