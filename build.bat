@echo off
chcp 65001 >nul
echo ====================================
echo   Vosk 语音识别程序打包脚本
echo ====================================
echo.

:: 创建打包目录
echo [1/4] 创建打包目录...
if not exist "build\dist\VoskASR\bin" mkdir "build\dist\VoskASR\bin"
if not exist "build\dist\VoskASR\model" mkdir "build\dist\VoskASR\model"

:: 复制 FFmpeg
echo [2/4] 复制 FFmpeg...
if exist "D:\Prom\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe" (
    copy "D:\Prom\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe" "build\dist\VoskASR\bin\" >nul
    echo       FFmpeg 复制完成
) else (
    echo       警告: 未找到 FFmpeg，音频转换功能可能不可用
)

:: 复制 Vosk 模型
echo [3/4] 复制 Vosk 模型（约2GB，可能需要几分钟）...
if exist "D:\Prom\vosk-model-cn-0.22" (
    xcopy "D:\Prom\vosk-model-cn-0.22" "build\dist\VoskASR\model\vosk-model-cn-0.22\" /E /I /Q /Y >nul
    echo       Vosk 模型复制完成
) else (
    echo       警告: 未找到 Vosk 模型
)

:: 使用 PyInstaller 打包
echo [4/4] 使用 PyInstaller 打包...
echo       这可能需要几分钟...
pyinstaller ^
    --name VoskASR ^
    --distpath build\dist ^
    --workpath build\build ^
    --specpath build ^
    --noconfirm ^
    --onedir ^
    --console ^
    --hidden-import vosk ^
    --hidden-import pyaudio ^
    --collect-all vosk ^
    "import tkinter as tk.py"

if %errorlevel% equ 0 (
    echo.
    echo ====================================
    echo   打包完成！
    echo ====================================
    echo.
    echo 输出目录: build\dist\VoskASR\
    echo.
    echo 下一步:
    echo 1. 运行 build\dist\VoskASR\VoskASR.exe 测试
    echo 2. 使用 Inno Setup 编译 setup.iss 生成安装程序
    echo.
) else (
    echo.
    echo 打包失败，请检查错误信息
)

pause
