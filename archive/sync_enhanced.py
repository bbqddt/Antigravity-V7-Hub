"""
Antigravity 增强版预测引擎 V2.0 - 活跃开发目录版本
"""
import os
import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = str(_PROJECT_ROOT / 'Antigravity_Work' / 'enhanced_predictor.py')
DST = str(_PROJECT_ROOT / 'enhanced_predictor.py')

if os.path.exists(SRC):
    shutil.copy2(SRC, DST)
    print(f"✅ enhanced_predictor.py 已同步到 {DST}")
else:
    print(f"❌ 源文件不存在: {SRC}")
    sys.exit(1)
