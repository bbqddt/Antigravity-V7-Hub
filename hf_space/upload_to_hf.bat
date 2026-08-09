@echo off
REM =============================================
REM Antigravity HF Spaces 部署向导
REM =============================================

echo.
echo ========================================
echo   Antigravity -> HF Spaces 部署向导
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

echo [1/4] 检查 huggingface_hub...
python -c "import huggingface_hub" >nul 2>&1
if errorlevel 1 (
    echo     未安装，正在安装...
    pip install huggingface_hub gradio --quiet
    if errorlevel 1 (
        echo [错误] 安装失败，请手动运行: pip install huggingface_hub
        pause
        exit /b 1
    )
    echo     安装完成
) else (
    echo     已安装
)

echo.
echo [2/4] 请输入你的 HF Token:
echo     (在 https://huggingface.co/settings/tokens 获取)
set /p HF_TOKEN="Token: "

if "%HF_TOKEN%"=="" (
    echo [错误] Token 不能为空
    pause
    exit /b 1
)

echo.
echo [3/4] 请输入你的 Space ID:
echo     (格式: username/Antigravity)
set /p HF_SPACE="Space ID: "

if "%HF_SPACE%"=="" (
    echo [错误] Space ID 不能为空
    pause
    exit /b 1
)

echo.
echo [4/4] 开始部署...
echo.

python "%~dp0deploy_hf.py" --space "%HF_SPACE%" --token "%HF_TOKEN%"

echo.
echo 部署完成!
echo 访问: https://huggingface.co/spaces/%HF_SPACE%
echo.
pause
