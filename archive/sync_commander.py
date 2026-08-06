"""
Antigravity Commander Bot V1.0 - 活跃开发目录版本
复制自 E:\Antigravity_Work\commander_bot.py
"""
# 这个文件是 E:\享中 目录下的快捷入口
# 实际代码位于 E:\Antigravity_Work\commander_bot.py

import os
import shutil
import sys

SRC = r"E:\Antigravity_Work\commander_bot.py"
DST = r"E:\享中\commander_bot.py"

if os.path.exists(SRC):
    shutil.copy2(SRC, DST)
    print(f"✅ commander_bot.py 已同步到 {DST}")
else:
    print(f"❌ 源文件不存在: {SRC}")
    sys.exit(1)
