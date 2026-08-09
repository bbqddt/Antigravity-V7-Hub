"""
Antigravity Commander Bot Sync Helper V1.0
"""
# 这个文件用于从开发目录同步 commander_bot.py 到当前工作目录

import os
import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = str(_PROJECT_ROOT / 'Antigravity_Work' / 'commander_bot.py')
DST = str(_PROJECT_ROOT / 'commander_bot.py')

if os.path.exists(SRC):
    shutil.copy2(SRC, DST)
    print(f"✅ commander_bot.py 已同步到 {DST}")
else:
    print(f"❌ 源文件不存在: {SRC}")
    sys.exit(1)
