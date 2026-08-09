"""
Antigravity 增强版预测引擎 V2.0
================================
集成多维度策略 + 自动回测调优 + 多引擎融合

新增策略:
  - HotCore: 热号骨架 + 冷号回补
  - ColdStrike: 冷号反击
  - Balanced: 热冷均衡
  - ZoneControl: 区间控制 (一区1-11, 二区12-22, 三区23-33)
  - Consecutive: 连号策略
  - Omission: 遗漏值策略
  - WeightedEnsemble: 多策略加权投票

用法:
    python enhanced_predictor.py              # 单次预测
    python enhanced_predictor.py --train      # 训练+预测
    python enhanced_predictor.py --backtest   # 仅回测
"""

import json
import os
import random
import sys
import time
import logging
import numpy as np
from collections import Counter
from typing import List
from datetime import datetime
from pathlib import Path

# ─── 项目根目录（禁止硬编码盘符）──────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志配置

# 自定义 StreamHandler，过滤 emoji 避免 GBK 编码崩溃
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # 移除非 ASCII 字符（emoji 等）
            msg = "".join(c for c in msg if ord(c) < 128)
            self.stream.write(msg + self.terminator)
            self.stream.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "enhanced_predictor.log"), encoding="utf-8"),
        SafeStreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("EnhancedPredictor")

# ---------------------------------------------------------------------------
# 数据路径
# ---------------------------------------------------------------------------
DATA_FILE = _PROJECT_ROOT / "data" / "lottery_history.csv"
OUTPUT_FILE = _PROJECT_ROOT / "latest_decision_enhanced.json"
STATE_FILE = _PROJECT_ROOT / "enhanced_state.json"

# ─── CausalAnalyzer 集成 ─────────────────────────────────
_CAUSAL_ANALYZER = None

def _get_causal_analyzer():
    global _CAUSAL_ANALYZER
    if _CAUSAL_ANALYZER is None:
        try:
            from core.causal_reasoning import CausalAnalyzer
            _CAUSAL_ANALYZER = CausalAnalyzer()
        except ImportError:
            _CAUSAL_ANALYZER = None
    return _CAUSAL_ANALYZER


def _validate_with_causal(reds: List[int], blue: int) -> tuple:
    """
    用 CausalAnalyzer 验证一组预测。
    Returns: (valid: bool, multiplier: float)
    """
    analyzer = _get_causal_analyzer()
    if analyzer is None:
        return True, 1.0
    reds_str = ", ".join(str(r) for r in reds)
    result = analyzer.evaluate_causality(reds_str, str(blue))
    mult = result.get("confidence_multiplier", 1.0)
    valid = result.get("status") != "failed"
    return valid, mult


def load_data():
    """加载历史数据，自动清洗脏行"""
    import pandas as pd
    filepath = str(DATA_FILE) if isinstance(DATA_FILE, Path) else DATA_FILE
    df = pd.read_csv(filepath)
    col_names = df.columns.tolist()

    # 统一格式: period,red,blue,date (4列)
    if len(col_names) >= 4 and "period" in col_names:
        df["period"] = pd.to_numeric(df["period"], errors="coerce")
        # red 列已经是逗号分隔的字符串，确保格式正确
        df["red"] = df["red"].apply(lambda x: ",".join(sorted(
            str(int(v)) for v in str(x).split(",") if v.strip().isdigit()
        )) if pd.notna(x) else "")
        df["blue"] = pd.to_numeric(df["blue"], errors="coerce").round().astype("Int64")
    else:
        # 旧格式兼容: 数字索引列
        period_col = col_names[0]
        red_cols = col_names[1:7]
        blue_col = col_names[7]
        df["period"] = pd.to_numeric(df[period_col], errors="coerce")

        def safe_red(row):
            vals = [row[c] for c in red_cols]
            nums = []
            for v in vals:
                if pd.notna(v):
                    try:
                        n = int(round(float(v)))
                        if 1 <= n <= 33:
                            nums.append(n)
                    except (ValueError, TypeError):
                        pass
            return ",".join(str(n) for n in nums) if len(nums) == 6 else ""
        df["red"] = df[red_cols].apply(safe_red, axis=1)
        df["blue"] = pd.to_numeric(df[blue_col], errors="coerce").round().astype("Int64")

    # 删除脏行
    df = df.dropna(subset=["period"]).copy()
    df = df[df["red"].str.len() >= 10].copy()
    df["period"] = df["period"].astype(int)
    df = df.sort_values("period", ascending=False).reset_index(drop=True)
    return df


def parse_reds(row):
    """解析红球列表"""
    if isinstance(row, dict) and "red" in row:
        return [int(x) for x in str(row["red"]).split(",")]
    if hasattr(row, "get") and "red" in row:
        return [int(x) for x in str(row["red"]).split(",")]
    # row 是 pandas Series，且有 'red' 列
    if hasattr(row, "red"):
        return [int(x) for x in str(row.red).split(",")]
    return [int(x) for x in str(row).split(",")]


# ---------------------------------------------------------------------------
# 策略模块
# ---------------------------------------------------------------------------

class HotCoreStrategy:
    """热号骨架 + 冷号回补 (带时间衰减加权)

    V2.1 改进：
    - lookback 从 30 提升到 60
    - 加入遗漏值加权：长期遗漏的号码有更高的回补概率
    - 加入连号偏好：约70%的双色球期数含连号
    """

    def __init__(self, df, lookback=60):
        self.df = df.head(lookback)
        self.lookback = lookback

    def generate(self):
        # 时间衰减加权: 最近的数据权重更高 (指数衰减 alpha=0.97)
        all_reds = []
        weights = []
        for i, (_, row) in enumerate(self.df.iterrows()):
            decay = 0.97 ** (len(self.df) - 1 - i)  # 更激进的衰减
            all_reds.extend(parse_reds(row))
            weights.extend([decay] * 6)

        freq = Counter()
        for num, w in zip(all_reds, weights):
            freq[num] += w

        # 计算遗漏值：最近未出现的号码
        latest = parse_reds(self.df.iloc[0]) if len(self.df) > 0 else []
        omission = {}
        for i in range(1, 34):
            if i in latest:
                omission[i] = 0
            else:
                # 计算加权遗漏期数
                omit_periods = 0.0
                for j, (_, row) in enumerate(self.df.iterrows()):
                    reds = parse_reds(row)
                    if i not in reds:
                        omit_periods += 0.95 ** j
                    else:
                        break
                omission[i] = omit_periods

        # 热号：加权频率最高的12个
        hot = sorted(freq.keys(), key=lambda x: freq.get(x, 0), reverse=True)[:12]
        # 冷号：遗漏值最大的12个（排除已在热号中的）
        cold = sorted(
            [i for i in range(1, 34) if i not in hot],
            key=lambda x: omission.get(x, 0),
            reverse=True
        )[:12]

        # 3热 + 2冷 + 1随机平衡号
        base = random.sample(hot, min(3, len(hot)))
        supplement = random.sample(cold, min(2, len(cold))) if cold else []
        reds = sorted(set(base + supplement))

        # 第6个号：从遗漏值中等但频率不低的号码中选
        mid_pool = [
            i for i in range(1, 34)
            if i not in reds and 0.5 < omission.get(i, 0) < 5.0
        ]
        if mid_pool:
            reds.append(random.choice(mid_pool))
        reds = sorted(set(reds))

        while len(reds) < 6:
            extra = random.choice([x for x in range(1, 34) if x not in reds])
            reds.append(extra)
            reds = sorted(set(reds))

        return reds[:6]


class ColdStrikeStrategy:
    """冷号反击 (带时间衰减加权)

    V2.1 改进：
    - 使用遗漏值而非简单频率阈值
    - lookback 从 30 提升到 60
    - 加入奇偶平衡约束
    """

    def __init__(self, df, lookback=60):
        self.df = df.head(lookback)
        self.lookback = lookback

    def generate(self):
        all_reds, weights = [], []
        for i, (_, row) in enumerate(self.df.iterrows()):
            decay = 0.97 ** (len(self.df) - 1 - i)
            all_reds.extend(parse_reds(row))
            weights.extend([decay] * 6)

        freq = Counter()
        for num, w in zip(all_reds, weights):
            freq[num] += w

        # 计算遗漏值
        omission = {}
        for i in range(1, 34):
            omit_periods = 0.0
            for j, (_, row) in enumerate(self.df.iterrows()):
                reds = parse_reds(row)
                if i not in reds:
                    omit_periods += 0.95 ** j
                else:
                    break
            omission[i] = omit_periods

        # 选遗漏值最大的15个号码作为冷号池
        cold = sorted(
            [i for i in range(1, 34)],
            key=lambda x: omission.get(x, 0),
            reverse=True
        )[:15]

        # 从冷号池中选4个，兼顾频率最低
        cold_freq = sorted(cold, key=lambda x: freq.get(x, 0))[:10]

        base = random.sample(cold_freq, min(4, len(cold_freq)))
        # 2个补充号：从遗漏值中等的号码中选
        mid_omit = [
            i for i in range(1, 34)
            if i not in base and 2.0 < omission.get(i, 0) < 8.0
        ]
        supplement = random.sample(mid_omit, min(2, len(mid_omit))) if mid_omit else []
        reds = sorted(set(base + supplement))

        while len(reds) < 6:
            extra = random.choice([x for x in range(1, 34) if x not in reds])
            reds.append(extra)
            reds = sorted(set(reds))

        return reds[:6]


class BalancedStrategy:
    """热冷均衡 (带时间衰减加权)"""

    def __init__(self, df, lookback=30):
        self.df = df.head(lookback)

    def generate(self):
        all_reds, weights = [], []
        for i, (_, row) in enumerate(self.df.iterrows()):
            decay = 0.95 ** (len(self.df) - 1 - i)
            all_reds.extend(parse_reds(row))
            weights.extend([decay] * 6)

        freq = Counter()
        for num, w in zip(all_reds, weights):
            freq[num] += w

        hot = [k for k, v in freq.most_common(10)]
        cold = [i for i in range(1, 34) if freq.get(i, 0) <= 1.5]

        # 3热 + 3冷
        sample_hot = random.sample(hot, min(3, len(hot))) if hot else []
        sample_cold = random.sample(cold, min(3, len(cold))) if cold else []
        reds = sorted(set(sample_hot + sample_cold))

        while len(reds) < 6:
            extra = random.choice([x for x in range(1, 34) if x not in reds])
            reds.append(extra)
            reds = sorted(set(reds))

        return reds[:6]


class ZoneControlStrategy:
    """区间控制策略 (带时间衰减加权)
    红球分为三区: 一区(1-11), 二区(12-22), 三区(23-33)
    每区出2球，保证分布均匀
    """

    def __init__(self, df, lookback=30):
        self.df = df.head(lookback)

    def generate(self):
        all_reds, weights = [], []
        for i, (_, row) in enumerate(self.df.iterrows()):
            decay = 0.95 ** (len(self.df) - 1 - i)
            all_reds.extend(parse_reds(row))
            weights.extend([decay] * 6)

        freq = Counter()
        for num, w in zip(all_reds, weights):
            freq[num] += w

        zone1 = sorted([k for k in range(1, 12)], key=lambda x: freq.get(x, 0), reverse=True)
        zone2 = sorted([k for k in range(12, 23)], key=lambda x: freq.get(x, 0), reverse=True)
        zone3 = sorted([k for k in range(23, 34)], key=lambda x: freq.get(x, 0), reverse=True)

        reds = []
        for zone in [zone1, zone2, zone3]:
            reds.extend(random.sample(zone, 2))

        return sorted(reds)


class ConsecutiveStrategy:
    """连号策略 (带时间衰减加权)
    双色球约70%的期数含有连号，此策略专门捕捉连号模式
    """

    def __init__(self, df, lookback=50):
        self.df = df.head(lookback)

    def generate(self):
        # 分析历史连号模式 (加权)
        consecutive_pairs = Counter()
        for i, (_, row) in enumerate(self.df.iterrows()):
            decay = 0.95 ** (len(self.df) - 1 - i)
            reds = parse_reds(row)
            for j in range(len(reds) - 1):
                if reds[j + 1] - reds[j] == 1:
                    consecutive_pairs[(reds[j], reds[j + 1])] += decay

        # 取最频繁的连号对
        if consecutive_pairs:
            pair = consecutive_pairs.most_common(1)[0][0]
            base = list(pair)
        else:
            base = random.sample(range(1, 34), 2)

        # 再选4个不与前两个相邻的号
        adjacent = set()
        for p in base:
            adjacent.add(p - 1)
            adjacent.add(p + 1)
        remaining = [x for x in range(1, 34) if x not in base and x not in adjacent]
        supplement = random.sample(remaining, min(4, len(remaining)))

        return sorted(set(base + supplement))[:6]


class OmissionStrategy:
    """遗漏值策略 (带时间衰减加权)
    关注长期未出现的号码（大遗漏回补）和短期频繁出现的号码（热号延续）
    """

    def __init__(self, df):
        self.df = df

    def generate(self):
        # 计算每个号码的最新遗漏期数 (加权)
        latest = self.df.iloc[0]
        all_reds = parse_reds(latest)

        omission = {}
        for i in range(1, 34):
            periods_missed = 0
            weight_sum = 0
            for j, (_, row) in enumerate(self.df.iterrows()):
                reds = parse_reds(row)
                if i not in reds:
                    decay = 0.95 ** j
                    periods_missed += decay
                    weight_sum += decay
                else:
                    break
            omission[i] = periods_missed / max(weight_sum, 1)

        # 选3个大遗漏 + 3个小遗漏
        sorted_by_omission = sorted(omission.items(), key=lambda x: x[1], reverse=True)
        high_omission = [x[0] for x in sorted_by_omission[:10]]
        low_omission = [x[0] for x in sorted_by_omission[-10:]]

        reds = random.sample(high_omission, 3) + random.sample(low_omission, 3)
        return sorted(reds)


class TrendStrategy:
    """趋势跟随策略 (带时间衰减加权)

    V2.1 改进：
    - 不只看均值，还看各区分布
    - 加入斜率检测：趋势加速/减速
    - lookback 从 10 提升到 20
    """

    def __init__(self, df, lookback=20):
        self.df = df.head(lookback)

    def generate(self):
        # 计算最近几期的加权均值
        means = []
        zone_means = {1: [], 2: [], 3: []}  # 一区、二区、三区

        for i, (_, row) in enumerate(self.df.iterrows()):
            decay = 0.97 ** (len(self.df) - 1 - i)
            reds = parse_reds(row)
            mean_val = sum(reds) / len(reds)
            means.append((mean_val, decay))

            # 分区统计
            for r in reds:
                if r <= 11:
                    zone_means[1].append((r, decay))
                elif r <= 22:
                    zone_means[2].append((r, decay))
                else:
                    zone_means[3].append((r, decay))

        if len(means) >= 5:
            # 计算趋势斜率
            recent = sum(m * d for m, d in means[-3:]) / sum(d for _, d in means[-3:])
            older = sum(m * d for m, d in means[:3]) / sum(d for _, d in means[:3])
            slope = recent - older

            # 计算各区加权密度
            zone_density = {}
            for z, entries in zone_means.items():
                total_decay = sum(d for _, d in entries)
                zone_density[z] = total_decay / max(len(entries), 1)

            if slope > 0.5:
                # 均值上移，偏向大号区
                pool = list(range(15, 34))
            elif slope < -0.5:
                # 均值下移，偏向小号区
                pool = list(range(1, 22))
            else:
                # 趋势平稳，按各区密度均衡选号
                pool = list(range(1, 34))
        else:
            pool = list(range(1, 34))

        # 从 pool 中选6个，但加入密度偏好
        if len(pool) >= 6:
            # 按密度加权选择
            weights = []
            for n in pool:
                if n <= 11:
                    w = zone_density.get(1, 0.1)
                elif n <= 22:
                    w = zone_density.get(2, 0.1)
                else:
                    w = zone_density.get(3, 0.1)
                weights.append(max(w, 0.01))

            total_w = sum(weights)
            probs = [w / total_w for w in weights]
            chosen = np.random.choice(pool, size=min(6, len(pool)), replace=False, p=probs)
            reds = sorted(chosen.tolist())
        else:
            reds = sorted(pool)

        while len(reds) < 6:
            extra = random.choice([x for x in range(1, 34) if x not in reds])
            reds.append(extra)
            reds = sorted(set(reds))

        return reds[:6]


class AutocorrelationStrategy:
    """自相关策略 (V2.2 新增)

    对每个号码计算其二进制出现序列的自相关 (lag 1-5)。
    正自相关 = 动号（出现后倾向于再出现），负自相关 = 反转号。
    根据自相关符号选择号码：正自相关的选高频号，负的选遗漏号。
    """

    def __init__(self, df, lookback=100):
        self.df = df.head(lookback)
        self.lookback = lookback
        self.autocorr = self._compute_autocorrelation()

    def _compute_autocorrelation(self):
        """计算每个号码的自相关系数"""
        autocorr = {}
        for num in range(1, 34):
            seq = [1 if num in parse_reds(row) else 0 for _, row in self.df.iterrows()]
            n = len(seq)
            if n < 10:
                autocorr[num] = 0.0
                continue
            mean = sum(seq) / n
            var = sum((x - mean)**2 for x in seq) / n
            if var < 1e-10:
                autocorr[num] = 0.0
                continue
            # 计算 lag-1 自相关
            cov = sum((seq[i] - mean) * (seq[i+1] - mean) for i in range(n-1)) / (n-1)
            autocorr[num] = cov / var
        return autocorr

    def generate(self):
        # 正自相关号码（动号）和负自相关号码（反转号）
        momentum_nums = sorted([n for n, ac in self.autocorr.items() if ac > 0.05],
                               key=lambda x: -self.autocorr[x])
        mean_revert_nums = sorted([n for n, ac in self.autocorr.items() if ac < -0.05],
                                  key=lambda x: self.autocorr[x])

        # 3个动号 + 3个反转号
        base = momentum_nums[:3] if momentum_nums else random.sample(range(1, 34), 3)
        supplement = mean_revert_nums[:3] if mean_revert_nums else []
        reds = sorted(set(base + supplement))

        while len(reds) < 6:
            extra = random.choice([x for x in range(1, 34) if x not in reds])
            reds.append(extra)
            reds = sorted(set(reds))

        return reds[:6]


class CooccurrenceStrategy:
    """共现配对策略 (V2.2 新增)

    构建最近 lookback 期的 33x33 共现矩阵。
    对每个号码计算其「最强关联邻居」。
    策略：随机选2个种子号 → 从它们的关联邻居中选4个。
    """

    def __init__(self, df, lookback=200):
        self.df = df.head(lookback)
        self.lookback = lookback
        self.neighbors = self._compute_neighbors()

    def _compute_neighbors(self):
        """计算每个号码的最强关联邻居"""
        # 共现计数
        cooccur = [[0]*34 for _ in range(34)]
        freq = Counter()
        for _, row in self.df.iterrows():
            reds = parse_reds(row)
            for n in reds:
                freq[n] += 1
            reds_sorted = sorted(reds)
            for i in range(6):
                for j in range(i+1, 6):
                    cooccur[reds_sorted[i]][reds_sorted[j]] += 1
                    cooccur[reds_sorted[j]][reds_sorted[i]] += 1

        total = len(self.df)
        expected = (6/33) * (5/32) * total

        neighbors = {}
        for i in range(1, 34):
            excess = []
            for j in range(1, 34):
                if i != j:
                    obs = cooccur[i][j]
                    exc = (obs - expected) / max(expected, 1)
                    excess.append((j, exc))
            # 按超额共现排序，取前5个
            excess.sort(key=lambda x: -x[1])
            neighbors[i] = [n for n, _ in excess[:5]]
        return neighbors

    def generate(self):
        # 随机选2个种子号
        seeds = random.sample(range(1, 34), 2)

        # 从种子的关联邻居中选4个
        neighbor_pool = []
        for seed in seeds:
            neighbor_pool.extend(self.neighbors.get(seed, []))
        neighbor_pool = sorted(set(neighbor_pool))

        reds = list(seeds)
        for n in neighbor_pool:
            if n not in reds:
                reds.append(n)
            if len(reds) >= 6:
                break

        while len(reds) < 6:
            extra = random.choice([x for x in range(1, 34) if x not in reds])
            reds.append(extra)
            reds = sorted(set(reds))

        return reds[:6]

def predict_blue_balanced(df, lookback=30):
    """蓝球均衡策略 (带时间衰减加权)"""
    blues = []
    weights = []
    for i, (_, row) in enumerate(df.head(lookback).iterrows()):
        decay = 0.95 ** (len(df.head(lookback)) - 1 - i)
        blues.append(int(row["blue"]))
        weights.append(decay)

    freq = Counter()
    for b, w in zip(blues, weights):
        freq[b] += w

    hot = [k for k, v in freq.most_common(5)]
    cold = [i for i in range(1, 17) if freq.get(i, 0) <= 1.5]
    return random.choice(cold) if cold else random.choice(hot)


def predict_blue_omission(df, position_prior=None):
    """蓝球遗漏策略 (加权遗漏)

    V2.2 改进: 加入 Hurst 均值回归校正。
    如果检测到蓝球强反持久性 (Hurst < 0.3)，遗漏策略的权重加倍。
    """
    all_blues = df["blue"].astype(int).tolist()

    omission = {}
    for i in range(1, 17):
        periods = 0.0
        weight_sum = 0.0
        for j, b in enumerate(all_blues):
            decay = 0.95 ** j
            if b != i:
                periods += decay
                weight_sum += decay
            else:
                break
        omission[i] = periods / max(weight_sum, 1)

    # V2.2: Hurst 校正 — 如果均值回归信号强，遗漏策略更有效
    if position_prior is not None:
        from signal_fusion import apply_hurst_correction_to_omission
        correction = apply_hurst_correction_to_omission(df, position_prior)
        if correction > 1.0:
            # 对遗漏值最高的3个号码给予额外权重
            sorted_omit = sorted(omission.items(), key=lambda x: -x[1])
            for idx in range(min(3, len(sorted_omit))):
                omission[sorted_omit[idx][0]] *= correction

    # 选加权遗漏最大的
    return max(omission, key=omission.get)


def predict_blue_markov(df, lookback=100):
    """蓝球马尔可夫转移策略 (V2.2 新增)

    构建 16x16 转移矩阵 P(下一期=j | 本期=i)，
    取最近一期蓝球，选转移概率最高的下期蓝球。
    """
    blues = df["blue"].astype(int).tolist()[:lookback]
    if len(blues) < 10:
        return random.randint(1, 16)

    # 构建转移计数矩阵
    counts = [[0]*17 for _ in range(17)]  # 索引 1-16
    for i in range(len(blues) - 1):
        counts[blues[i]][blues[i+1]] += 1

    # 最近一期蓝球
    last_blue = blues[-1]
    if last_blue < 1 or last_blue > 16:
        return random.randint(1, 16)

    # 选转移计数最高的
    row = counts[last_blue]
    # Laplace 平滑避免零概率
    smoothed = [c + 1 for c in row]
    smoothed[last_blue] += 0.5  # 轻微惩罚重复
    return max(range(1, 17), key=lambda x: smoothed[x])


# ---------------------------------------------------------------------------
# 多策略加权投票
# ---------------------------------------------------------------------------

class WeightedEnsemble:
    """多策略加权投票引擎"""

    def __init__(self, df, state_file=STATE_FILE):
        self.df = df
        self.state_file = state_file
        self.strategies = {
            "hot_core": HotCoreStrategy(df),
            "cold_strike": ColdStrikeStrategy(df),
            "balanced": BalancedStrategy(df),
            "zone_control": ZoneControlStrategy(df),
            "consecutive": ConsecutiveStrategy(df),
            "omission": OmissionStrategy(df),
            "trend": TrendStrategy(df),
            # V2.2 新增
            "autocorrelation": AutocorrelationStrategy(df),
            "cooccurrence": CooccurrenceStrategy(df),
        }
        self.weights = self._load_weights()

    def _load_weights(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                return {k: v.get("weight", 1.0) for k, v in state.get("strategies", {}).items()}
        return {name: 1.0 for name in self.strategies}

    def _save_weights(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({"strategies": {k: {"weight": v} for k, v in self.weights.items()}}, f, indent=2)

    def generate(self, num_groups=5):
        """生成多组预测（含 CausalAnalyzer 验证）

        V2.2 改进：
        - 默认使用 predict_blue_omission（遗漏策略），比 balanced 策略表现更好
        - 蓝球策略轮换：omission/markov/balanced
        - 注入 position_prior 信号到蓝球遗漏策略
        """
        names = list(self.strategies.keys())
        w = [max(0.1, self.weights.get(n, 1.0)) for n in names]
        selected_names = random.choices(names, weights=w, k=num_groups)

        # 蓝球策略轮换
        blue_strategies = [predict_blue_omission, predict_blue_markov, predict_blue_balanced]

        # 加载信号融合先验
        try:
            from signal_fusion import load_position_prior
            position_prior = load_position_prior()
        except ImportError:
            position_prior = None

        results = []
        for i, name in enumerate(selected_names, 1):
            strategy = self.strategies[name]
            reds = strategy.generate()
            # 轮换使用不同的蓝球策略
            # 索引0=omission, 1=markov, 2=balanced
            strategy_idx = i % len(blue_strategies)
            blue_fn = blue_strategies[strategy_idx]

            # 只有 omission 策略 (idx=0) 接收 position_prior 信号
            if strategy_idx == 0 and position_prior:
                blue = blue_fn(self.df, position_prior=position_prior)
            else:
                blue = blue_fn(self.df)

            # 因果验证
            valid, mult = _validate_with_causal(reds, blue)

            results.append({
                "group": i,
                "strategy": name,
                "reds": reds,
                "blue": blue,
                "causal_valid": valid,
                "causal_multiplier": round(mult, 4),
            })

        # 按因果有效性排序：先排 valid=True 的
        results.sort(key=lambda x: (not x["causal_valid"], -x["causal_multiplier"]))
        return results

    def evaluate_on_history(self, periods=50):
        """在历史数据上评估各策略表现 (t-1预测t, 避免数据泄露)

        V2.1 修复：
        - df 按 period 降序排列（最新在前），iloc[0] 是最新一期
        - 滚动窗口：用前i期(iloc[i:])训练，预测第i-1期(iloc[i-1])
        """
        eval_results = {}
        n = min(periods + 50, len(self.df) - 1)  # 至少50期预热 + periods轮回测

        # 策略类映射
        strategy_classes = {
            "hot_core": HotCoreStrategy,
            "cold_strike": ColdStrikeStrategy,
            "balanced": BalancedStrategy,
            "zone_control": ZoneControlStrategy,
            "consecutive": ConsecutiveStrategy,
            "omission": OmissionStrategy,
            "trend": TrendStrategy,
            "autocorrelation": AutocorrelationStrategy,
            "cooccurrence": CooccurrenceStrategy,
        }

        for name, strategy_cls in strategy_classes.items():
            total_hits = 0
            total_rounds = 0

            for i in range(50, n):
                train_df = self.df.iloc[i:]
                test_draw = self.df.iloc[i - 1]

                temp_strategy = strategy_cls(train_df)
                actual_reds = set(parse_reds(test_draw))
                pred_reds = set(temp_strategy.generate())
                hit = len(actual_reds & pred_reds)
                total_hits += hit
                total_rounds += 1

            eval_results[name] = {
                "avg_hits": total_hits / max(1, total_rounds),
                "rounds": total_rounds,
            }
        return eval_results

    def update_weights(self, evaluation_results):
        """根据评估结果更新权重 — V2.1 使用 softmax 分配"""
        # 收集所有策略的平均命中数
        hits = []
        for name in self.strategies:
            h = evaluation_results.get(name, {}).get("avg_hits", 0)
            hits.append(h)

        if not hits or max(hits) <= 0:
            # 如果没有有效数据，保持等权
            for name in self.strategies:
                self.weights[name] = 1.0 / len(self.strategies)
        else:
            # 使用 softmax 分配权重，温度参数 2.0
            raw = np.array(hits)
            raw = np.maximum(raw, 0.01)  # 避免零权重
            softmax = np.exp(raw * 2.0)
            softmax /= softmax.sum()
            for i, name in enumerate(self.strategies):
                self.weights[name] = float(softmax[i])

        self._save_weights()


# ---------------------------------------------------------------------------
# 回测引擎
# ---------------------------------------------------------------------------

def backtest_strategy(strategy_class, df, periods=50):
    """单策略回测"""
    strategy = strategy_class(df)
    correct_reds = 0
    total_reds = 0

    for i in range(1, min(periods, len(df))):
        actual_reds = set(parse_reds(df.iloc[i - 1]))
        pred_reds = set(strategy.generate())
        correct_reds += len(actual_reds & pred_reds)
        total_reds += 6

    accuracy = correct_reds / max(1, total_reds)
    return accuracy


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def run_prediction(num_groups=5, mode="normal"):
    """运行预测"""
    logger.info(f">>> 启动增强版预测引擎 V2.0 (模式: {mode}, 组数: {num_groups})")

    df = load_data()
    latest_period = int(df.iloc[0]["period"])
    target_period = latest_period + 1

    logger.info(f"📊 数据量: {len(df)} 期 | 最新期号: {latest_period} | 目标期号: {target_period}")

    # 初始化引擎
    ensemble = WeightedEnsemble(df)

    if mode == "train":
        # 训练模式：先评估再预测
        logger.info("🔬 进入训练模式 - 评估各策略...")
        eval_results = ensemble.evaluate_on_history(periods=50)
        for name, metrics in eval_results.items():
            logger.info(f"  {name}: 平均命中={metrics['avg_hits']:.2f}/6 ({metrics['rounds']}轮)")

        ensemble.update_weights(eval_results)
        logger.info("✅ 权重已更新")

    # 生成预测
    predictions = ensemble.generate(num_groups)

    # 格式化输出
    logger.info(f"\n{'='*50}")
    logger.info(f"      Antigravity 增强版预测 - 第 {target_period} 期")
    logger.info(f"{'='*50}\n")

    output = {
        "period": str(target_period),
        "predictions": [],
        "engine": "Enhanced Predictor V2.0 (Multi-Strategy Ensemble)",
        "timestamp": datetime.now().isoformat(),
    }

    for p in predictions:
        red_str = ", ".join([f"{r:02d}" for r in p["reds"]])
        causal_tag = "✅" if p.get("causal_valid", True) else "❌"
        logger.info(f"组别 {p['group']} [{p['strategy']}] {causal_tag}:")
        logger.info(f"  🔴 红球: [{red_str}]")
        logger.info(f"  🔵 蓝球: {p['blue']:02d}")
        if not p.get("causal_valid", True):
            logger.info(f"  ⚠️ 因果验证未通过 (乘数: {p.get('causal_multiplier', '?')})")
        logger.info("")

        output["predictions"].append({
            "group": p["group"],
            "strategy": p["strategy"],
            "reds": p["reds"],
            "blue": p["blue"],
            "causal_valid": p.get("causal_valid", True),
            "causal_multiplier": p.get("causal_multiplier", 1.0),
        })

    # 保存结果
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 预测已保存至: {OUTPUT_FILE}")
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Antigravity Enhanced Predictor V2.0")
    parser.add_argument("--groups", type=int, default=5, help="预测组数")
    parser.add_argument("--mode", choices=["normal", "train", "backtest"], default="normal")
    parser.add_argument("--periods", type=int, default=30, help="回测期数")
    args = parser.parse_args()

    if args.mode == "backtest":
        logger.info(">>> 回测模式")
        df = load_data()
        strategies = {
            "HotCore": HotCoreStrategy,
            "ColdStrike": ColdStrikeStrategy,
            "Balanced": BalancedStrategy,
            "ZoneControl": ZoneControlStrategy,
            "Consecutive": ConsecutiveStrategy,
            "Omission": OmissionStrategy,
            "Trend": TrendStrategy,
        }
        results = {}
        for name, cls in strategies.items():
            acc = backtest_strategy(cls, df, args.periods)
            results[name] = acc
            logger.info(f"  {name}: {acc:.2%}")

        best = max(results, key=results.get)
        logger.info(f"\n🏆 最佳策略: {best} ({results[best]:.2%})")

        # 保存回测结果
        with open(_PROJECT_ROOT / "backtest_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
    else:
        run_prediction(args.groups, args.mode)
