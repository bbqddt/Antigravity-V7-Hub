# -*- coding: utf-8 -*-
"""
补充双色球历史数据至最新开奖期
数据来源: 自动检测可用数据文件
"""

import os
from pathlib import Path

# ─── 相对路径 ─────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent

# 自动查找数据文件
_CANDIDATES = [
    _PROJECT_ROOT / "data" / "lottery_history.csv",
    _PROJECT_ROOT / "data" / "ssq_history.csv",
    _PROJECT_ROOT / "data" / "ssq_history_full.csv",
]

CSV_PATH = None
for c in _CANDIDATES:
    if c.exists():
        CSV_PATH = str(c)
        break

if CSV_PATH is None:
    print(f"❌ 未找到数据文件，请在 data/ 目录下放置彩票历史数据")
    print(f"   已搜索: {[str(c) for c in _CANDIDATES]}")
    CSV_PATH = str(_CANDIDATES[0])  # 使用第一个作为默认


def main():
    if not os.path.exists(CSV_PATH):
        print(f"❌ 数据文件不存在: {CSV_PATH}")
        return

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 解析已有期号
    existing = set()
    for line in lines[1:]:  # 跳过 header
        parts = line.strip().split(",")
        if parts and parts[0]:
            try:
                existing.add(int(parts[0]))
            except ValueError:
                continue

    print(f"Existing data: {len(lines) - 1} rows (latest: {max(existing) if existing else 'N/A'})")

    print("\n✅ 数据更新脚本就绪。")
    print(f"   数据文件: {CSV_PATH}")
    print(f"   请使用 data_updater_v2.py 进行自动数据同步。")


if __name__ == "__main__":
    main()
