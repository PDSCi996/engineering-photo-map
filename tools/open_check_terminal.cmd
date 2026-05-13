@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
cmd /k tools\check_all.cmd
