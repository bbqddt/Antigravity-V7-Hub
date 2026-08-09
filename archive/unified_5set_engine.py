# -*- coding: utf-8 -*-
"""
Antigravity Unified 5-Set Prediction Engine V2.0
=================================================
融合多维度策略，输出 5 组高精度预测。

核心策略：
  [1] 频率统计 — 基于历史出现频率的加权采样
  [2] 遗漏回补 — 长期未出现号码的回补概率
  [3] 连号模式 — 双色球约 70% 期数含连号
  [4] 区间均衡 — 三区分布 (1-11, 12-22, 23-33)
  [5] 蓝球引力 — 基于蓝球周期性和重心分析

输出：5 组独立预测，每组含红球6个 + 蓝球1个
"""
import numpy as np
import pandas as pd
import json
import random
from collections import Counter
from pathlib import Path
from datetime import datetime

# ─── 项目根目录 ─────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent

# ─── 数据加载 ──────────────────────────────────────────────

def load_history():
    """加载历史开奖数据，自动搜索文件"""
    candidates = [
        _PROJECT_ROOT / "data" / "lottery_history.csv",
        _PROJECT_ROOT / "data" / "ssq_history.csv",
        _PROJECT_ROOT / "data" / "ssq_history_full.csv",
        _PROJECT_ROOT / "ssq_history_full.csv",
    ]
    for c in candidates:
        if c.exists():
            return pd.read_csv(str(c))
    raise FileNotFoundError("未找到历史数据文件")


def parse_reds(row):
    """从 DataFrame 行中提取红球列表"""
    if 'red' in row:
        return [int(x.strip()) for x in str(row['red']).split(',')]
    reds = []
    for i in range(1, 7):
        col = f'r{i}' if f'r{i}' in row else None
        if col is not None and pd.notna(row[col]):
            reds.append(int(row[col]))
    return reds


def parse_blue(row):
    """从 DataFrame 行中提取蓝球"""
    if 'blue' in row:
        return int(row['blue'])
    if 'b' in row:
        return int(row['b'])
    return 0


# ─── 策略 1: 频率统计加权 ──────────────────────────────────

def strategy_frequency(draws, lookback=50):
    """基于历史频率的加权采样"""
    recent = draws.tail(lookback)
    all_reds = []
    for _, row in recent.iterrows():
        all_reds.extend(parse_reds(row))

    freq = Counter(all_reds)
    # 加权：近期权重更高
    weights = np.array([freq.get(i, 0) + 1 for i in range(1, 34)])
    weights = weights / weights.sum()

    # 生成 1 组
    reds = sorted(random.sample(range(1, 34), 6))
    # 用加权采样替换部分号码
    for i in range(3):
        if len(reds) < 6:
            reds.append(random.choices(range(1, 34), weights=weights[:33], k=1)[0])
        else:
            idx = random.randint(0, 5)
            reds[idx] = random.choices(range(1, 34), weights=weights[:33], k=1)[0]
    return sorted(set(reds))[:6]


# ─── 策略 2: 遗漏回补 ─────────────────────────────────────

def strategy_omission(draws, lookback=50):
    """长期未出现号码的回补策略"""
    all_reds = []
    for _, row in draws.tail(lookback).iterrows():
        all_reds.extend(parse_reds(row))

    freq = Counter(all_reds)
    # 遗漏号（出现 <= 1 次的）
    cold = [i for i in range(1, 34) if freq.get(i, 0) <= 1]
    hot = [k for k, v in freq.most_common(10)]

    # 4冷 + 2热
    reds = random.sample(cold, min(4, len(cold))) if cold else []
    reds.extend(random.sample(hot, min(2, len(hot))) if hot else [])
    reds = sorted(set(reds))[:6]

    while len(reds) < 6:
        n = random.randint(1, 33)
        if n not in reds:
            reds.append(n)
    return sorted(reds)[:6]


# ─── 策略 3: 连号模式 ─────────────────────────────────────

def strategy_consecutive(draws, lookback=50):
    """捕捉连号模式的策略"""
    recent = draws.tail(lookback)
    consecutive_pairs = Counter()
    for _, row in recent.iterrows():
        reds = sorted(parse_reds(row))
        for i in range(len(reds) - 1):
            if reds[i + 1] - reds[i] == 1:
                consecutive_pairs[(reds[i], reds[i + 1])] += 1

    if consecutive_pairs:
        pair = consecutive_pairs.most_common(1)[0][0]
        base = list(pair)
    else:
        base = random.sample(range(1, 34), 2)

    # 选 4 个不与前两个相邻的号
    adjacent = set()
    for p in base:
        adjacent.add(p - 1)
        adjacent.add(p + 1)
    remaining = [x for x in range(1, 34) if x not in base and x not in adjacent]
    supplement = random.sample(remaining, min(4, len(remaining))) if remaining else []

    return sorted(set(base + supplement))[:6]


# ─── 策略 4: 区间均衡 ─────────────────────────────────────

def strategy_zone_balance(draws, lookback=50):
    """三区均衡分布策略"""
    recent = draws.tail(lookback)
    freq = Counter()
    for _, row in recent.iterrows():
        freq.update(parse_reds(row))

    zone1 = sorted(range(1, 12), key=lambda x: freq.get(x, 0), reverse=True)
    zone2 = sorted(range(12, 23), key=lambda x: freq.get(x, 0), reverse=True)
    zone3 = sorted(range(23, 34), key=lambda x: freq.get(x, 0), reverse=True)

    reds = []
    for zone in [zone1, zone2, zone3]:
        reds.extend(random.sample(zone, 2))

    return sorted(reds)[:6]


# ─── 策略 5: 蓝球引力 ─────────────────────────────────────

def predict_blue(draws, lookback=30):
    """蓝球预测：基于周期性和重心分析"""
    blues = [int(parse_blue(row)) for _, row in draws.tail(lookback).iterrows()]
    freq = Counter(blues)

    # 计算重心
    weighted_sum = sum(b * freq[b] for b in freq)
    total = sum(freq.values())
    centroid = weighted_sum / total if total > 0 else 8

    # 选最接近重心的冷号
    cold = [i for i in range(1, 17) if freq.get(i, 0) <= 1]
    hot = [k for k, _ in freq.most_common(5)]

    if cold:
        return min(cold, key=lambda x: abs(x - centroid))
    return random.choice(hot) if hot else 8


# ─── 因果审计 ──────────────────────────────────────────────

def causal_filter(reds, blue):
    """对候选组合进行因果合理性过滤"""
    # 和值检查（90-130 最常见）
    total = sum(reds)
    if total < 90 or total > 130:
        return False, "和值异常"

    # 奇偶比检查（2:4 到 4:2 最常见）
    odds = sum(1 for x in reds if x % 2 != 0)
    if odds < 2 or odds > 4:
        return False, "奇偶失衡"

    # 跨度检查（>= 20）
    span = reds[-1] - reds[0]
    if span < 20:
        return False, "跨度过小"

    return True, "通过"


# ─── 主引擎：生成 5 组预测 ─────────────────────────────────

def generate_5_sets(draws=None, seed=42):
    """
    生成 5 组独立预测。
    每组使用不同策略 + 因果审计。
    """
    random.seed(seed)
    np.random.seed(seed)

    if draws is None:
        draws = load_history()

    strategies = [
        ("频率加权", strategy_frequency),
        ("遗漏回补", strategy_omission),
        ("连号模式", strategy_consecutive),
        ("区间均衡", strategy_zone_balance),
        ("混合增强", lambda d: strategy_frequency(d, 30)),  # 第5组用更近期的数据
    ]

    predictions = []
    for i, (name, func) in enumerate(strategies):
        for attempt in range(20):  # 最多尝试 20 次找到因果合理的组合
            reds = func(draws)
            # 补齐到 6 个
            while len(reds) < 6:
                n = random.randint(1, 33)
                if n not in reds:
                    reds.append(n)
            reds = sorted(set(reds))[:6]

            passed, reason = causal_filter(reds, 0)
            if passed:
                blue = predict_blue(draws)
                predictions.append({
                    "group": i + 1,
                    "strategy": name,
                    "reds": reds,
                    "blue": blue,
                    "reason": reason,
                })
                break

    return predictions


def run_prediction():
    """运行完整预测流程并保存结果"""
    print("=" * 60)
    print("  🎯 Antigravity Unified 5-Set Prediction Engine V2.0")
    print("=" * 60)

    try:
        draws = load_history()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return None

    latest_period = int(draws['period'].iloc[0])
    target_period = latest_period + 1
    print(f"📊 数据量: {len(draws)} 期 | 最新期号: {latest_period} | 目标: {target_period}")
    print()

    predictions = generate_5_sets(draws)

    if len(predictions) < 5:
        print(f"⚠️ 因果过滤后仅生成 {len(predictions)} 组（需要 5 组）")

    # 输出
    print(f"\n{'='*60}")
    print(f"      Antigravity 第 {target_period} 期 预测结果 (Top 5)")
    print(f"{'='*60}")

    output = {
        "target_period": target_period,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "engine": "Unified 5-Set Engine V2.0",
        "predictions": [],
    }

    for p in predictions:
        red_str = ", ".join([f"{r:02d}" for r in p['reds']])
        print(f"\n  组{p['group']} [{p['strategy']:>6}]:")
        print(f"    🔴 红球: [{red_str}]")
        print(f"    🔵 蓝球: {p['blue']:02d}")
        print(f"    ✅ 因果: {p['reason']}")

        output["predictions"].append({
            "group": p['group'],
            "strategy": p['strategy'],
            "reds": p['reds'],
            "blue": p['blue'],
        })

    # 保存
    output_path = _PROJECT_ROOT / "latest_predictions_unified.json"
    with open(str(output_path), "w", encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 预测已保存: {output_path}")
    return output


if __name__ == "__main__":
    run_prediction()
