@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Photo Map - install V0.3.29b dev check tools

cd /d "%~dp0.."

echo ============================================================
echo Photo Map - install dev check tools
echo Project root: %CD%
echo ============================================================
echo.

set "PY_EXE="

if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if not errorlevel 1 set "PY_EXE=python"
)

if "%PY_EXE%"=="" (
    echo [FAIL] Python not found.
    pause
    exit /b 1
)

echo [1/2] Python version
"%PY_EXE%" --version
echo.

echo [2/2] Install / upgrade dev check tools
"%PY_EXE%" -m pip install -U pip
"%PY_EXE%" -m pip install -U -r "tools\requirements-dev.txt"

echo.
echo Done.
pause
