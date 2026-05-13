@echo off
chcp 936 >nul
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT=%%~fI"
cd /d "%ROOT%" || (
    echo [ERROR] Cannot enter project root: %ROOT%
    pause
    exit /b 1
)

echo ========================================
echo Photo Map - init runtime directories
echo Project root: %CD%
echo ========================================
echo.

call :MKDIR "data"
call :MKDIR "data\db"
call :MKDIR "data\uploads"
call :MKDIR "data\thumbnails"
call :MKDIR "data\previews"
call :MKDIR "data\exports"
call :MKDIR "data\backups"
call :MKDIR "logs"
call :MKDIR "reports"

call :TOUCH "data\.gitkeep"
call :TOUCH "data\db\.gitkeep"
call :TOUCH "data\uploads\.gitkeep"
call :TOUCH "data\thumbnails\.gitkeep"
call :TOUCH "data\previews\.gitkeep"
call :TOUCH "data\exports\.gitkeep"
call :TOUCH "data\backups\.gitkeep"
call :TOUCH "logs\.gitkeep"
call :TOUCH "reports\.gitkeep"

echo.
echo [OK] Runtime directories are ready.
echo.
echo Created or checked:
echo   data\db
echo   data\uploads
echo   data\thumbnails
echo   data\previews
echo   data\exports
echo   data\backups
echo   logs
echo   reports
echo.
echo Note: These are runtime data folders. Do not commit real photos, database files, logs, or reports to GitHub.
echo.
pause
exit /b 0

:MKDIR
if not exist %1 (
    mkdir %1
    if errorlevel 1 (
        echo [ERROR] Failed to create folder: %~1
        exit /b 1
    ) else (
        echo [OK] Created folder: %~1
    )
) else (
    echo [SKIP] Folder exists: %~1
)
exit /b 0

:TOUCH
if not exist %1 (
    type nul > %1
    if errorlevel 1 (
        echo [WARN] Failed to create placeholder: %~1
    ) else (
        echo [OK] Created placeholder: %~1
    )
)
exit /b 0
