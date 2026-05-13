@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
set "PS1_FILE=%~dp008-api-logs.ps1"

echo Running Photo Map script...
echo %PS1_FILE%
echo.

if not exist "%PS1_FILE%" (
  echo ERROR: PowerShell script not found.
  echo %PS1_FILE%
  echo.
  pause
  exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1_FILE%"

echo.
echo Press any key to exit...
pause >nul
exit /b %ERRORLEVEL%
