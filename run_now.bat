@echo off
echo [1/3] 正在检查/安装自动化插件 (Playwright)...
python -m pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple

echo [2/3] 正在检查浏览器内核...
python -m playwright install chromium

echo [3/3] 环境已就绪，正在启动自动化脚本...
echo --------------------------------------------------
python auto_op.py

pause