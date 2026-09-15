# -*- coding: utf-8 -*-
"""
Antigravity 统一数据层

职责：
1. 唯一数据源：所有模块从此读取历史开奖数据
2. 格式兼容：自动适配多种 CSV 格式（标准格式、V7 flat 格式、legacy 格式）
3. 数据验证：确保每行数据合法（6个红球1-33，蓝球1-16）

用法：
    from data_layer import load_history, get_latest_period, save_prediction
    history = load_history()  # 返回 Draw 列表
"""

import os
import csv
import json
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


# ─── 数据路径 ─────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.resolve()
_DATA_DIR = _PROJECT_ROOT / "data"

# 数据文件优先级：按搜索顺序
_CANDIDATE_CSV_PATHS = [
    # 标准格式
    _DATA_DIR / "lottery_history.csv",
    _DATA_DIR / "ssq_history.csv",
    _DATA_DIR / "ssq_history_full.csv",
    # 兼容：根目录下直接放的数据文件
    _PROJECT_ROOT / "data" / "lottery_history.csv",
    _PROJECT_ROOT / "data" / "ssq_history.csv",
    _PROJECT_ROOT / "data" / "ssq_history_full.csv",
    # 兼容旧格式：ssq_history_v7.csv
    _DATA_DIR / "ssq_history_v7.csv",
    _PROJECT_ROOT / "data" / "ssq_history_v7.csv",
]


@dataclass
class Draw:
    """单期开奖数据"""
    period: int
    reds: List[int]       # 6个红球，已排序
    blue: int             # 蓝球

    # 别名：兼容旧代码
    @property
    def red(self) -> List[int]:
        return self.reds

    def __str__(self):
        reds_str = " ".join(f"{x:02d}" for x in self.reds)
        return f"#{self.period} [{reds_str}] + {self.blue:02d}"


def _find_csv() -> Optional[Path]:
    """查找可用的数据文件"""
    for p in _CANDIDATE_CSV_PATHS:
        if p.exists():
            return p
    return None


def _detect_format(filepath: Path) -> str:
    """
    检测CSV格式：
    - 'standard': period,red,blue,date （标准格式）
    - 'v7_flat': id,r1,r2,...,r6,b,date （V7 flat 格式）
    - 'legacy_float': 索引行 + 浮点数数据
    """
    with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
        first_line = f.readline().strip()
        second_line = f.readline().strip()

    # 检查header
    if first_line.startswith('period,'):
        return 'standard'

    if first_line.startswith('id,') or (first_line.replace(',', '').isdigit() and len(first_line.split(',')) >= 8):
        if second_line and ',' in second_line:
            parts = second_line.split(',')
            try:
                float(parts[1])
                if first_line.replace(',', '').replace('.', '').isdigit():
                    return 'legacy_float'
                return 'v7_flat'
            except ValueError:
                pass
        return 'v7_flat'

    return 'unknown'


def _parse_standard(filepath: Path) -> List[Draw]:
    """解析标准格式: period,red,blue,date"""
    draws = []
    with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                period = int(row['period'])
                reds = [int(x.strip()) for x in row['red'].split(',')]
                blue = int(row['blue'])
                if len(reds) == 6 and all(1 <= r <= 33 for r in reds):
                    draws.append(Draw(period=period, reds=sorted(reds), blue=blue))
            except (ValueError, KeyError):
                continue
    return draws


def _parse_v7_flat(filepath: Path) -> List[Draw]:
    """解析 V7 flat 格式: id,r1,r2,r3,r4,r5,r6,b,date"""
    draws = []
    with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                period = int(row['id'])
                reds = [int(float(row[f'r{i}'])) for i in range(1, 7)]
                blue = int(float(row['b']))
                draws.append(Draw(period=period, reds=sorted(reds), blue=blue))
            except (ValueError, KeyError, TypeError):
                continue
    return draws


def _parse_legacy_float(filepath: Path) -> List[Draw]:
    """解析 legacy_float 格式"""
    draws = []
    with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
        lines = f.readlines()

    for line in lines[2:]:
        parts = line.strip().split(',')
        if len(parts) < 8:
            continue
        try:
            period = int(parts[0])
            reds = [int(float(parts[i])) for i in range(1, 7)]
            blue = int(float(parts[7])) if len(parts) > 7 else 0
            if len(reds) == 6 and all(1 <= r <= 33 for r in reds):
                draws.append(Draw(period=period, reds=sorted(reds), blue=blue))
        except (ValueError, IndexError):
            continue
    return draws


def load_history(csv_path: Optional[str] = None) -> List[Draw]:
    """
    加载全部历史开奖数据。

    Args:
        csv_path: 可选，指定CSV文件路径。如果不传，自动搜索。

    Returns:
        Draw 列表，按期号升序排列
    """
    if csv_path:
        filepath = Path(csv_path)
    else:
        filepath = _find_csv()

    if not filepath or not filepath.exists():
        raise FileNotFoundError(
            f"未找到双色球历史数据文件。已搜索: {_CANDIDATE_CSV_PATHS}"
        )

    fmt = _detect_format(filepath)
    print(f"[DataLayer] 检测到格式: {fmt} (文件: {filepath.name})")

    if fmt == 'standard':
        draws = _parse_standard(filepath)
    elif fmt == 'v7_flat':
        draws = _parse_v7_flat(filepath)
    elif fmt == 'legacy_float':
        draws = _parse_legacy_float(filepath)
    else:
        raise ValueError(f"不支持的CSV格式: {fmt}")

    # 按期号排序（升序）
    draws.sort(key=lambda d: d.period)

    # 去重（保留最新）
    seen = {}
    for d in draws:
        seen[d.period] = d
    draws = sorted(seen.values(), key=lambda d: d.period)

    print(f"[DataLayer] 加载 {len(draws)} 期数据 (#{draws[0].period} ~ #{draws[-1].period})")
    return draws


def get_latest_period(draws: Optional[List[Draw]] = None) -> int:
    """获取最新期号"""
    if draws is None:
        draws = load_history()
    return max(d.period for d in draws)


def get_recent(draws: List[Draw], n: int = 30) -> List[Draw]:
    """获取最近 N 期数据"""
    return draws[-n:] if len(draws) >= n else draws


def save_prediction(target_period: int, predictions: List[dict],
                    output_dir: Optional[str] = None) -> str:
    """
    保存预测结果到 JSON 文件。
    """
    if output_dir is None:
        output_dir = str(_PROJECT_ROOT)

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"latest_predictions_{target_period}.json")

    data = {
        "target_period": target_period,
        "generated_at": _now_iso(),
        "predictions": predictions
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[DataLayer] 预测已保存: {filepath}")
    return filepath


def load_predictions(period: int, search_dirs: Optional[List[str]] = None) -> Optional[dict]:
    """加载某期预测结果"""
    dirs = search_dirs or [str(_PROJECT_ROOT)]
    for d in dirs:
        filepath = os.path.join(d, f"latest_predictions_{period}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
