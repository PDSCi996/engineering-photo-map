@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Photo Map - V0.3.29b formal local check

REM Always run from project root, even if this CMD is double-clicked in tools.
cd /d "%~dp0.."

echo ============================================================
echo Photo Map - V0.3.29b formal local check
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
    echo Please create .venv or install Python.
    echo.
    pause
    exit /b 1
)

echo [1/3] Python version
"%PY_EXE%" --version
echo.

echo [2/3] Check tools\check_all.py exists
if not exist "tools\check_all.py" (
    echo [FAIL] tools\check_all.py not found.
    echo.
    pause
    exit /b 1
)
echo [OK] Found tools\check_all.py
echo.

echo [3/3] Run formal project checks
"%PY_EXE%" "tools\check_all.py"
set "ERR=%ERRORLEVEL%"

echo.
if "%ERR%"=="0" (
    echo Check finished: no critical failure code returned.
) else (
    echo Check finished: critical failure returned. Please read reports and logs.
)

echo.
echo Reports are usually saved in:
echo   reports\dev-check-YYYYMMDD_HHMMSS.md
echo Logs are usually saved in:
echo   logs\dev-check-raw-YYYYMMDD_HHMMSS.txt
echo.
echo This window will not close automatically.
pause
exit /b %ERR%
