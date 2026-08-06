"""
Antigravity 增强版预测引擎 V2.0 - 活跃开发目录版本
"""
import os
import shutil
import sys

SRC = r"E:\Antigravity_Work\enhanced_predictor.py"
DST = r"E:\享中\enhanced_predictor.py"

if os.path.exists(SRC):
    shutil.copy2(SRC, DST)
    print(f"✅ enhanced_predictor.py 已同步到 {DST}")
else:
    print(f"❌ 源文件不存在: {SRC}")
    sys.exit(1)
