@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo ================================
echo 激活项目 Python 虚拟环境
echo 当前目录：%cd%
echo ================================

if not exist ".venv\Scripts\activate.bat" (
    echo 未找到 .venv\Scripts\activate.bat
    echo 请确认项目根目录下是否有 .venv 文件夹。
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo.
echo 虚拟环境已激活。
echo 现在可以运行：
echo python --version
echo tools\check_all.cmd
echo.

cmd /k