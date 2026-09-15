# -*- coding: utf-8 -*-
"""
Antigravity V15: 学习型多维预测引擎 (Learning Multidimensional Predictor)

核心创新：
V14 的 7 个维度是静态的——它们永远用同样的权重。
V15 让引擎从每次开奖中学习：

1. 每个维度都有动态权重，根据历史表现自适应调整
2. 融合不是简单共振，而是加权共振
3. 引擎记录每一轮的"命中贡献"——哪个维度真正帮了忙
4. 权重通过指数加权移动平均（EWMA）更新
5. 连续失败会触发"探索模式"——增加随机性避免过拟合

哲学：
如果时间不存在，那么学习不是"从过去推未来"，
而是从场的整体结构中实时更新信念。
贝叶斯更新就是这种信念更新的数学表达。
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from collections import Counter, defaultdict
from typing import List, Tuple, Dict, Optional
from datetime import datetime

import numpy as np

from data_layer import load_history, Draw
from pathlib import Path

# ─── 共享先验加载 ──────────────────────────────────────────
_ANALYSIS_PRIOR = None

def _load_analysis_prior():
    """加载 NonrandomnessDetector 的共享先验"""
    global _ANALYSIS_PRIOR
    if _ANALYSIS_PRIOR is None:
        prior_file = Path(__file__).resolve().parent / "analysis_prior.json"
        if prior_file.exists():
            with open(prior_file, "r", encoding="utf-8") as f:
                _ANALYSIS_PRIOR = json.load(f)
        else:
            _ANALYSIS_PRIOR = {"has_structure": False}
    return _ANALYSIS_PRIOR


# ─── 学习状态 ─────────────────────────────────────────────
class LearningState:
    """
    引擎的学习记忆。

    每个维度维护：
    - weight: 当前融合权重（初始 1.0）
    - hit_contribution: 该维度对命中的贡献累计
    - recent_performance: 近期表现（EWMA）
    - streak: 连续失败计数（触发探索模式）
    """

    def __init__(self, dim_names: List[str]):
        self.dim_names = dim_names
        self.n_dims = len(dim_names)
        # 每个维度的权重
        self.weights = np.ones(self.n_dims) / self.n_dims
        # 每个维度的近期表现（EWMA，alpha=0.1）
        self.recent_perf = np.zeros(self.n_dims)
        # 每个维度的累计贡献
        self.cumulative_contribution = np.zeros(self.n_dims)
        # 连续失败计数
        self.streak = np.zeros(self.n_dims)
        # 总回合数
        self.total_rounds = 0
        # 探索模式开关（当连续失败 > 5 时激活）
        self.exploration_mode = False
        self.exploration_rate = 0.0  # 探索模式下随机采样的比例

        # 历史记录
        self.history: List[Dict] = []

    def update(self, round_hits: Dict[str, int], actual_red: List[int]):
        """
        更新学习状态。

        Args:
            round_hits: {dim_name: hit_count} 每个维度在该轮的命中数
            actual_red: 实际开奖的红球
        """
        actual_set = set(actual_red)
        alpha = 0.1  # EWMA 平滑因子

        for i, name in enumerate(self.dim_names):
            hits = round_hits.get(name, 0)
            # 该维度的即时表现（归一化到 0-1）
            perf = hits / 6.0

            # EWMA 更新
            self.recent_perf[i] = alpha * perf + (1 - alpha) * self.recent_perf[i]

            # 累计贡献
            self.cumulative_contribution[i] += perf

            # 连续失败
            if perf == 0:
                self.streak[i] += 1
            else:
                self.streak[i] = 0

        # 更新权重：基于近期表现的 softmax
        self._update_weights(alpha)

        # 检查探索模式
        avg_streak = np.mean(self.streak)
        self.exploration_mode = avg_streak > 5
        self.exploration_rate = min(0.3, avg_streak * 0.05)

        self.total_rounds += 1

        # 记录回合
        self.history.append({
            "round": self.total_rounds,
            "hits": round_hits,
            "weights": self.weights.tolist(),
            "exploration": bool(self.exploration_mode),
        })

    def _update_weights(self, alpha: float):
        """基于近期表现更新融合权重"""
        # 表现好的维度获得更高权重
        raw_weights = np.maximum(self.recent_perf, 0.01)
        # 加入探索惩罚：连续失败的维度权重降低
        for i in range(self.n_dims):
            if self.streak[i] > 3:
                raw_weights[i] *= 0.5 ** (self.streak[i] - 3)

        # Softmax 归一化
        raw_weights = np.exp(raw_weights * 5)  # 温度系数 5
        self.weights = raw_weights / raw_weights.sum()

    def get_weighted_score(self, dim_votes: Dict[int, int],
                           dim_counts: Dict[int, int]) -> float:
        """
        计算加权共振分数。

        普通模式：权重 × 共振
        探索模式：混合随机权重
        """
        if not self.exploration_mode:
            # 标准加权
            total_weight = sum(self.weights[i] for i in range(self.n_dims)
                              if self.dim_names[i] in dim_votes)
            return total_weight / self.weights.sum()

        else:
            # 探索模式：混合均匀权重
            exploration_weight = self.exploration_rate
            standard_weight = 1.0 - exploration_weight
            standard_score = sum(self.weights[i] for i in range(self.n_dims)
                                if self.dim_names[i] in dim_votes)
            uniform_score = len(dim_votes) / self.n_dims
            return standard_weight * standard_score + exploration_weight * uniform_score

    def save(self, path: Optional[str] = None):
        """保存学习状态到 JSON（默认路径: learning_state.json）"""
        if path is None:
            path = str(Path(__file__).resolve().parent / "learning_state.json")
        state = {
            "dim_names": self.dim_names,
            "weights": self.weights.tolist(),
            "recent_perf": self.recent_perf.tolist(),
            "cumulative_contribution": self.cumulative_contribution.tolist(),
            "streak": self.streak.tolist(),
            "total_rounds": self.total_rounds,
            "exploration_mode": bool(self.exploration_mode),
            "exploration_rate": float(self.exploration_rate),
            "history": self.history[-100:],  # 只保留最近 100 轮
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "LearningState":
        """
        从 JSON 加载学习状态。
        如果文件不存在，返回一个新的 LearningState。
        V2.2 修复: 如果保存时的维度数与当前不同，自动适配。
        """
        if path is None:
            path = str(Path(__file__).resolve().parent / "learning_state.json")

        if not os.path.exists(path):
            # 文件不存在，返回新实例
            return cls(_DIM_NAMES)

        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)

        names = state.get("dim_names", _DIM_NAMES)
        obj = cls(names)

        saved_n = len(state.get("weights", []))
        current_n = len(_DIM_NAMES)

        if saved_n == current_n:
            # 维度数匹配，直接加载
            obj.weights = np.array(state["weights"])
            obj.recent_perf = np.array(state.get("recent_perf", [0.0] * current_n))
            obj.cumulative_contribution = np.array(state.get("cumulative_contribution", [0.0] * current_n))
            obj.streak = np.array(state.get("streak", [0.0] * current_n))
        else:
            # 维度数不匹配（新增了维度），保留旧维度数据，新维度初始化为等权
            print(f"[WARN] LearningState 维度数不匹配: 保存时={saved_n}, 当前={current_n}，自动适配")
            if saved_n > 0:
                obj.weights[:saved_n] = np.array(state["weights"])
                obj.recent_perf[:saved_n] = np.array(state.get("recent_perf", [0.0] * saved_n))
                obj.cumulative_contribution[:saved_n] = np.array(state.get("cumulative_contribution", [0.0] * saved_n))
                obj.streak[:saved_n] = np.array(state.get("streak", [0.0] * saved_n))
            # 新维度初始化为等权
            remaining = current_n - saved_n
            if remaining > 0:
                init_w = 1.0 / current_n
                obj.weights[saved_n:] = init_w
                # 已有的按等比例缩放
                if saved_n > 0:
                    existing_total = obj.weights[:saved_n].sum()
                    obj.weights[:saved_n] = obj.weights[:saved_n] / existing_total * (1.0 - init_w * remaining)
                    obj.weights /= obj.weights.sum()

        obj.total_rounds = state.get("total_rounds", 0)
        obj.exploration_mode = bool(state.get("exploration_mode", False))
        obj.exploration_rate = float(state.get("exploration_rate", 0.0))
        obj.history = state.get("history", [])
        return obj


# ─── 维度定义（复用 V14 的 7 个维度）────────────────────────
# 每个维度是一个类，有 generate_pool 方法

class Dim1_Statistics:
    name = "statistics"

    @staticmethod
    def generate_pool(draws: List[Draw], pool_size: int, rng: random.Random) -> List[Tuple[List[int], int]]:
        freq = Counter()
        omit = {i: 0 for i in range(1, 34)}
        for d in reversed(draws):
            for i in range(1, 34):
                if i not in d.red:
                    omit[i] = omit.get(i, 0) + 1
                else:
                    omit[i] = 0
            freq.update(d.red)

        total = len(draws)
        expected = total * 6 / 33
        scores = {}
        for n in range(1, 34):
            f = freq.get(n, 0)
            o = omit[n]
            scores[n] = (1.0 - f / max(expected, 1)) * 0.3 + (math.log1p(o) / math.log1p(25)) * 0.7

        pool = []
        for _ in range(pool_size):
            red = _weighted_sample(scores, 6, rng)
            blue = rng.randint(1, 16)
            pool.append((red, blue))
        return pool


class Dim2_Geometry:
    name = "geometry"

    @staticmethod
    def generate_pool(draws: List[Draw], pool_size: int, rng: random.Random) -> List[Tuple[List[int], int]]:
        coords = _sphere_coords(33)
        recent = draws[-min(50, len(draws)):]
        centers = [np.mean([coords[r - 1] for r in d.red], axis=0) for d in recent]

        avg_dist = {}
        for n in range(1, 34):
            if centers:
                avg_dist[n] = np.mean([np.linalg.norm(coords[n - 1] - c) for c in centers])
            else:
                avg_dist[n] = rng.random()

        pool = []
        for _ in range(pool_size):
            red = _weighted_sample(avg_dist, 6, rng)
            blue = rng.randint(1, 16)
            pool.append((red, blue))
        return pool


class Dim3_NumberTheory:
    name = "number_theory"
    PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31}
    SQUARES = {1, 4, 9, 16, 25}
    FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
    PERFECT = {6, 28}
    ALL_SPECIAL = PRIMES | SQUARES | FIBONACCI | PERFECT

    @staticmethod
    def generate_pool(draws: List[Draw], pool_size: int, rng: random.Random) -> List[Tuple[List[int], int]]:
        strategies = [
            lambda r: _nsample(Dim3_NumberTheory.PRIMES, r),
            lambda r: _nsample(Dim3_NumberTheory.FIBONACCI, r),
            lambda r: _nsample(Dim3_NumberTheory.ALL_SPECIAL, r),
            lambda r: _nsample(Dim3_NumberTheory.SQUARES, r),
            lambda r: _nsample(Dim3_NumberTheory.PERFECT, r),
        ]
        pool = []
        for _ in range(pool_size):
            red = strategies[rng.randint(0, 4)](rng)
            blue = rng.randint(1, 16)
            pool.append((red, blue))
        return pool


class Dim4_Modular:
    name = "modular"

    @staticmethod
    def generate_pool(draws: List[Draw], pool_size: int, rng: random.Random) -> List[Tuple[List[int], int]]:
        moduli = [3, 4, 5, 7, 11, 13]
        pool = []
        for _ in range(pool_size):
            mod = moduli[rng.randint(0, len(moduli) - 1)]
            classes = {r: Counter() for r in range(mod)}
            for d in draws[-min(100, len(draws)):]:
                for r in d.red:
                    classes[r % mod][r] += 1

            sorted_classes = sorted(
                {r: sum(cnt.values()) for r, cnt in classes.items()}.items(),
                key=lambda x: -x[1]
            )
            top_counter = classes[sorted_classes[0][0]]
            candidates = sorted(top_counter.keys())

            if len(candidates) >= 6:
                red = sorted(rng.sample(candidates, 6))
            elif len(sorted_classes) > 1:
                second_counter = classes[sorted_classes[1][0]]
                combined = dict(top_counter)
                for num, cnt in second_counter.items():
                    combined[num] = combined.get(num, 0) + cnt
                candidates = sorted(combined.keys())
                red = sorted(rng.sample(candidates, 6)) if len(candidates) >= 6 else sorted(rng.sample(range(1, 34), 6))
            else:
                red = sorted(rng.sample(range(1, 34), 6))

            pool.append((red, rng.randint(1, 16)))
        return pool


class Dim5_Chaos:
    name = "chaos"

    @staticmethod
    def generate_pool(draws: List[Draw], pool_size: int, rng: random.Random) -> List[Tuple[List[int], int]]:
        if len(draws) < 100:
            return Dim1_Statistics.generate_pool(draws, pool_size, rng)

        sums = [sum(d.red) for d in draws]
        dim, tau = 3, 5
        embeddings = [np.array(sums[i:i + (dim - 1) * tau + 1])
                      for i in range(0, len(sums) - (dim - 1) * tau, tau)]

        if embeddings:
            # Pad all embeddings to the same length for safe np.mean
            max_len = max(len(e) for e in embeddings)
            padded = [np.pad(e, (0, max_len - len(e)), constant_values=e[-1] if len(e) > 0 else 0)
                      for e in embeddings]
            center = np.mean(padded, axis=0)
            spread = np.std(padded, axis=0) + 1e-10
            pool = []
            for _ in range(pool_size):
                perturbed = center + rng.gauss(0, 1) * spread
                red = _perturb_to_numbers(perturbed, rng)
                pool.append((red, rng.randint(1, 16)))
            return pool
        return Dim1_Statistics.generate_pool(draws, pool_size, rng)


class Dim6_Information:
    name = "information"

    @staticmethod
    def generate_pool(draws: List[Draw], pool_size: int, rng: random.Random) -> List[Tuple[List[int], int]]:
        freq = Counter()
        for d in draws:
            freq.update(d.red)
        total = len(draws)

        entropy = {}
        for n in range(1, 34):
            p = freq.get(n, 0) / max(total, 1)
            entropy[n] = -math.log2(p) if p > 0 else math.log2(33)

        mutual_info = {}
        for i in range(1, 34):
            for j in range(i + 1, 34):
                co = sum(1 for d in draws if i in d.red and j in d.red)
                p_ij = co / max(total, 1)
                p_i = freq.get(i, 0) / max(total, 1)
                p_j = freq.get(j, 0) / max(total, 1)
                if p_ij > 0 and p_i > 0 and p_j > 0:
                    mutual_info[(i, j)] = math.log2(p_ij / (p_i * p_j))
                else:
                    mutual_info[(i, j)] = 0

        pool = []
        for _ in range(pool_size):
            red = []
            available = set(range(1, 34))
            while len(red) < 6 and available:
                best = {}
                for n in available:
                    ent = entropy.get(n, 0)
                    mi_pen = sum(mutual_info.get((min(n, r), max(n, r)), 0) for r in red)
                    best[n] = ent - 0.5 * mi_pen

                nums = list(best.keys())
                w = [max(best[n], 0.01) for n in nums]
                tw = sum(w)
                if tw <= 0:
                    chosen = rng.choice(nums)
                else:
                    r = rng.random() * tw
                    cum = 0
                    for i, nw in enumerate(w):
                        cum += nw
                        if cum >= r:
                            chosen = nums[i]
                            break
                    else:
                        chosen = nums[-1]

                red.append(chosen)
                available.discard(chosen)
            pool.append((sorted(red), rng.randint(1, 16)))
        return pool


class Dim7_PhysicalNoise:
    """
    维度7: 物理噪声残差分析 (替代原纯随机 Consciousness)

    核心思想: 如果摇奖机存在微小物理偏差(温度/气压/球重差异),
    残差序列会呈现结构化模式。通过分析各号码在历史中的"偏离程度",
    捕获可能的物理信号。
    """
    name = "physical_noise"

    @staticmethod
    def generate_pool(draws: List[Draw], pool_size: int, rng: random.Random) -> List[Tuple[List[int], int]]:
        if len(draws) < 50:
            # 数据不足时退化为频率加权
            return Dim1_Statistics.generate_pool(draws, pool_size, rng)

        # 计算每个号码的残差: 实际出现次数 vs 期望均匀分布
        freq = Counter()
        for d in draws:
            freq.update(d.red)

        total = len(draws)
        expected = total * 6 / 33  # 均匀分布期望

        residual = {}
        for n in range(1, 34):
            observed = freq.get(n, 0)
            # 标准化残差 (z-score近似)
            residual[n] = (observed - expected) / max(math.sqrt(expected), 1)

        # 选残差最高的号码(偏离均匀分布最显著的)
        sorted_nums = sorted(residual.keys(), key=lambda x: abs(residual[x]), reverse=True)

        # 选5个高残差 + 1个中等残差(探索)
        high_residual = sorted_nums[:15]
        mid_residual = sorted_nums[15:25]

        pool = []
        for _ in range(pool_size):
            reds = sorted(rng.sample(high_residual, 5))
            # 确保6个不重复
            while len(set(reds)) < 6:
                extra = rng.choice(mid_residual)
                if extra not in reds:
                    reds.append(extra)
                    reds = sorted(set(reds))
            pool.append((reds[:6], rng.randint(1, 16)))
        return pool


class Dim8_Cooccurrence:
    """
    维度8: 共现依赖分析

    核心思想: 双色球红球之间存在系统性共现依赖——某些号码对在历史上
    共同出现的频率显著高于独立事件的期望。此维度捕获这种成对关联结构。

    方法:
    1. 构建 33x33 共现矩阵
    2. 计算超额共现率: observed/(freq_i*freq_j) - 1
    3. 预测时: 先用频率选3个种子号, 再从超额共现最高的关联号中选3个
    """
    name = "cooccurrence"

    @staticmethod
    def generate_pool(draws: List[Draw], pool_size: int, rng: random.Random) -> List[Tuple[List[int], int]]:
        if len(draws) < 50:
            return Dim1_Statistics.generate_pool(draws, pool_size, rng)

        # 构建共现计数矩阵
        cooccur = [[0]*34 for _ in range(34)]
        freq = Counter()
        for d in draws:
            for n in d.red:
                freq[n] += 1
            reds = sorted(d.red)
            for i in range(6):
                for j in range(i+1, 6):
                    cooccur[reds[i]][reds[j]] += 1
                    cooccur[reds[j]][reds[i]] += 1

        total = len(draws)
        expected_cooccur = (6/33) * (5/32) * total  # 独立事件下的期望共现

        # 计算超额共现比率
        excess = {}
        for i in range(1, 34):
            excess[i] = {}
            for j in range(1, 34):
                if i != j:
                    obs = cooccur[i][j]
                    exp = expected_cooccur
                    excess[i][j] = (obs - exp) / max(exp, 1)

        # 为每个号码找最强的5个关联邻居
        neighbors = {}
        for i in range(1, 34):
            sorted_neighbors = sorted(excess[i].keys(), key=lambda x: -excess[i][x])[:5]
            neighbors[i] = sorted_neighbors

        pool = []
        for _ in range(pool_size):
            # 先用频率选3个种子号
            sorted_freq = sorted(range(1, 34), key=lambda x: -freq.get(x, 0))
            seeds = rng.sample(sorted_freq[:15], min(3, len(sorted_freq[:15])))

            # 从种子的关联邻居中选3个
            candidate_neighbors = []
            for seed in seeds:
                candidate_neighbors.extend(neighbors.get(seed, []))
            # 去重并排序
            candidate_neighbors = sorted(set(candidate_neighbors))

            reds = list(seeds)
            for n in candidate_neighbors:
                if n not in reds:
                    reds.append(n)
                if len(reds) >= 6:
                    break

            # 补齐
            while len(reds) < 6:
                extra = rng.randint(1, 33)
                if extra not in reds:
                    reds.append(extra)

            pool.append((sorted(reds[:6]), rng.randint(1, 16)))
        return pool


class Dim9_Positional:
    """
    维度9: 位置序列分析

    核心思想: 双色球红球排序后有6个位置（从小到大），每个位置的号码
    分布不均匀。例如号码33几乎总在位置6，号码1几乎总在位置1。
    这种位置特异性分布提供了预测信号。

    方法:
    1. 统计每个位置（1-6）上每个号码（1-33）的出现频率
    2. 预测时：从每个位置的 Top-5 中随机选1个，组成6个号的组合
    """
    name = "positional"

    @staticmethod
    def generate_pool(draws: List[Draw], pool_size: int, rng: random.Random) -> List[Tuple[List[int], int]]:
        if len(draws) < 50:
            return Dim1_Statistics.generate_pool(draws, pool_size, rng)

        # 统计每个位置的号码频率
        pos_freq = [Counter() for _ in range(6)]
        for d in draws:
            reds = sorted(d.red)
            for i, n in enumerate(reds):
                pos_freq[i][n] += 1

        # 每个位置取 Top-5
        pos_top5 = []
        for i in range(6):
            top = [n for n, _ in pos_freq[i].most_common(10)]
            pos_top5.append(top)

        pool = []
        for _ in range(pool_size):
            reds = []
            for i in range(6):
                if pos_top5[i]:
                    chosen = rng.choice(pos_top5[i])
                else:
                    chosen = rng.randint(1, 33)
                # 确保不重复
                while chosen in reds:
                    chosen = rng.randint(1, 33)
                reds.append(chosen)
            pool.append((sorted(reds), rng.randint(1, 16)))
        return pool


# ─── 工具函数 ─────────────────────────────────────────────
DIMENSIONS = [
    Dim1_Statistics, Dim2_Geometry, Dim3_NumberTheory,
    Dim4_Modular, Dim5_Chaos, Dim6_Information, Dim7_PhysicalNoise,
    Dim8_Cooccurrence, Dim9_Positional,
]

_DIM_NAMES = [d.name for d in DIMENSIONS]


def _sphere_coords(n: int) -> List[np.ndarray]:
    coords = []
    golden_angle = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - (i / max(n - 1, 1)) * 2
        radius = math.sqrt(max(0, 1 - y * y))
        theta = golden_angle * i
        coords.append(np.array([math.cos(theta) * radius, y, math.sin(theta) * radius]))
    return coords


def _weighted_sample(scores: Dict[int, float], k: int, rng: random.Random) -> List[int]:
    chosen = []
    available = list(range(1, 34))
    avail_w = [max(scores.get(n, 0.01), 0.001) for n in available]
    for _ in range(k):
        if not available:
            break
        total_w = sum(avail_w)
        if total_w <= 0 or len(available) == 1:
            chosen.append(available.pop(0))
            avail_w.pop(0)
            continue
        r = rng.random() * total_w
        cumulative = 0
        for i, ww in enumerate(avail_w):
            cumulative += ww
            if cumulative >= r:
                chosen.append(available[i])
                available.pop(i)
                avail_w.pop(i)
                break
        else:
            chosen.append(available[-1])
            available.pop()
            avail_w.pop()
    return sorted(chosen[:k])


def _nsample(special_set, rng):
    pool = sorted(special_set & set(range(1, 34)))
    reds = rng.sample(pool, min(3, len(pool)))
    while len(reds) < 6:
        n = rng.randint(1, 33)
        if n not in reds:
            reds.append(n)
    return sorted(reds)


def _perturb_to_numbers(vec, rng):
    n = len(vec)
    if n >= 6:
        indices = np.argsort(np.abs(vec))[-6:]
        nums = sorted(set(max(1, min(33, int(abs(vec[i]) * 33 / max(n, 1)) + 1)) for i in indices))
        if len(nums) >= 6:
            return nums[:6]
    return sorted(rng.sample(range(1, 34), 6))


# ─── CausalAnalyzer 集成 ─────────────────────────────────
# 延迟导入，避免循环依赖
_CAUSAL_ANALYZER = None

def _get_causal_analyzer():
    """懒加载 CausalAnalyzer"""
    global _CAUSAL_ANALYZER
    if _CAUSAL_ANALYZER is None:
        try:
            from core.causal_reasoning import CausalAnalyzer
            _CAUSAL_ANALYZER = CausalAnalyzer()
        except ImportError:
            _CAUSAL_ANALYZER = None
    return _CAUSAL_ANALYZER


def _causal_filter(scored_pool: list, top_k: int) -> list:
    """
    对预测池进行 CausalAnalyzer 验证。
    scored_pool 格式: [(red, blue, {score_dict}), ...] 或 [(red, blue, score, freq, reson), ...]
    """
    analyzer = _get_causal_analyzer()
    if analyzer is None:
        return scored_pool[:top_k]

    filtered = []
    for item in scored_pool:
        if len(item) == 3:
            # 已经是过滤后的格式: (red, blue, scores_dict)
            red, blue, scores = item
            freq = scores.get("frequency", 0)
            reson = scores.get("resonance", 0)
            score = scores.get("total_score", 0)
        elif len(item) == 5:
            red, blue, score, freq, reson = item
        else:
            continue

        reds_str = ", ".join(str(r) for r in red)
        result = analyzer.evaluate_causality(reds_str, str(blue))
        mult = result.get("confidence_multiplier", 1.0)
        valid = result.get("status") != "failed"

        adjusted_score = score * mult
        filtered.append((red, blue, adjusted_score, freq, reson, valid, mult))

    filtered.sort(key=lambda x: -x[2])

    final = []
    for red, blue, adj_score, freq, reson, valid, mult in filtered:
        final.append((red, blue, {
            "total_score": round(adj_score, 4),
            "frequency": round(freq, 4),
            "resonance": round(reson, 4),
            "causal_valid": valid,
            "causal_multiplier": round(mult, 4),
        }))
        if len(final) >= top_k:
            break

    return final


# ─── 核心预测引擎 ─────────────────────────────────────────
def predict_v15(
    draws: List[Draw],
    state: LearningState,
    top_k: int = 5,
    pool_per_dim: int = 200,
    seed: int = 42,
) -> Tuple[List[Tuple[List[int], int, Dict[str, float]]], List[Tuple[List[int], int, Dict[str, float]]]]:
    """
    V15 预测：加权融合 + 自适应学习 + CausalAnalyzer 后置过滤。

    Returns:
        (top_k_predictions, full_pool)
    """
    all_candidates: List[Tuple[str, List[int], int]] = []
    dim_votes: Dict[int, int] = defaultdict(int)
    dim_counts: Dict[int, int] = defaultdict(int)

    for i, dim_cls in enumerate(DIMENSIONS):
        dim_rng = random.Random(seed + i * 1000)
        pool = dim_cls.generate_pool(draws, pool_size=pool_per_dim, rng=dim_rng)
        for red, blue in pool:
            all_candidates.append((dim_cls.name, red, blue))
            for n in red:
                dim_counts[n] += 1
            for n in red:
                dim_votes[n] += 1

    # 加权打分 — V15.1 修复：分离频率和共振，避免系统性偏差
    scored = []
    for dim_name, red, blue in all_candidates:
        # 共振 = 该号码在多少不同维度中被选中（加权）
        resonance = 0.0
        for n in red:
            for j, dc in enumerate(DIMENSIONS):
                resonance += state.weights[j] * (dim_votes[n] / pool_per_dim)

        # 频率分数：号码在所有候选池中出现的加权频率
        freq_score = sum(dim_counts.get(n, 0) for n in red) / (pool_per_dim * len(DIMENSIONS))

        # V15.1 修复：不再混用频率和共振
        # 改为：共振为主（70%）+ 频率为辅（30%），避免高频号码总是胜出
        score = 0.3 * freq_score + 0.7 * (resonance / 6.0)

        # 加入多样性惩罚：如果红球组合中号码过于集中在热门区域，轻微降分
        # 这防止所有预测都是相同的"热门号码组合"
        span = max(red) - min(red)
        span_bonus = 0.0  # 跨度在合理范围内(20-32)不调整
        if span < 15:
            span_bonus = -0.05  # 跨度太小，可能是过度拟合
        elif span > 32:
            span_bonus = -0.02  # 极端跨度也少见

        scored.append((red, blue, score + span_bonus, freq_score, resonance / 6.0, dim_name))

    # 排序 + 多样性过滤
    scored.sort(key=lambda x: -x[2])

    # 如果检测到非随机结构，对高频维度加权 boosting
    prior = _load_analysis_prior()
    if prior.get("has_structure"):
        # 非随机信号存在 → 给信息论和混沌维度额外boost
        # 因为这两个维度对隐藏结构最敏感
        boost_factor = 1.2
        dim_boost = {"information": boost_factor, "chaos": boost_factor}
        boosted_scored = []
        for red, blue, score, freq, reson, dim_name in scored:
            # 从 dim_votes 中找出哪些维度贡献了这个组合
            dim_contributions = 0
            boosted_score = score
            for n in red:
                # 如果这个号码在信息论或混沌维度中被高频选中，加分
                if dim_votes.get(n, 0) > pool_per_dim * 0.3:
                    boosted_score *= dim_boost.get(dim_name, 1.0)
                    break
            boosted_scored.append((red, blue, boosted_score, freq, reson, dim_name))
        scored = boosted_scored
        scored.sort(key=lambda x: -x[2])

    # V15.1 多样性过滤：确保跨维度覆盖
    final_pool = []
    seen = set()
    dim_coverage = defaultdict(int)
    target_per_dim = max(top_k // len(DIMENSIONS), 1)

    # 第一轮：按分数从高到低选，但强制维度覆盖
    for red, blue, score, freq, reson, dim_name in scored:
        key = tuple(red)
        if key in seen:
            continue
        too_similar = any(len(set(red) & set(sk)) >= 4 for sk in seen)
        if too_similar:
            continue
        seen.add(key)
        dim_coverage[dim_name] += 1
        final_pool.append((list(red), blue, {
            "total_score": round(score, 4),
            "frequency": round(freq, 4),
            "resonance": round(reson, 4),
        }))
        if len(final_pool) >= top_k * 3:
            break

    # 第二轮：补充维度覆盖不足的
    if len(final_pool) < top_k * 3:
        for dim_name in _DIM_NAMES:
            if dim_coverage[dim_name] < target_per_dim:
                for red, blue, score, freq, reson, d in scored:
                    if d != dim_name:
                        continue
                    key = tuple(red)
                    if key in seen:
                        continue
                    too_similar = any(len(set(red) & set(sk)) >= 4 for sk in seen)
                    if too_similar:
                        continue
                    seen.add(key)
                    dim_coverage[dim_name] += 1
                    final_pool.append((list(red), blue, {
                        "total_score": round(score, 4),
                        "frequency": round(freq, 4),
                        "resonance": round(reson, 4),
                    }))
                    if dim_coverage[dim_name] >= target_per_dim:
                        break
                if len(final_pool) >= top_k * 3:
                    break

    return final_pool[:top_k], final_pool


def predict_v15_filtered(
    draws: List[Draw],
    state: LearningState,
    top_k: int = 5,
    pool_per_dim: int = 200,
    seed: int = 42,
) -> Tuple[List[Tuple[List[int], int, Dict[str, float]]], List[Tuple[List[int], int, Dict[str, float]]]]:
    """
    V15 预测 + CausalAnalyzer 过滤版。
    内部调用 predict_v15 然后用因果验证器过滤。
    """
    top_k_raw, full_pool = predict_v15(draws, state, top_k=top_k * 3, pool_per_dim=pool_per_dim, seed=seed)
    # top_k_raw 已经是过滤后的（因为内部用了 final_pool），再显式过滤一次
    filtered = _causal_filter(full_pool, top_k=top_k)
    return filtered, full_pool


def learn_from_round(
    state: LearningState,
    predictions: List[Tuple[List[int], int, Dict]],
    actual_red: List[int],
    draws: List[Draw] = None,
) -> Dict[str, int]:
    """
    从一轮预测中学习。

    方法：对于每个维度，用真实数据生成候选，统计其中有多少命中。
    V15.1 修复：需要传入 draws 参数，不能用空列表。
    """
    actual_set = set(actual_red)
    dim_hits: Dict[str, int] = {}

    for dim_cls in DIMENSIONS:
        dim_rng = random.Random(999 + hash(dim_cls.name))
        # V15.1 修复：必须有真实数据才能生成有意义的候选
        if draws is None or len(draws) < 10:
            dim_hits[dim_cls.name] = 0
            continue
        pool = dim_cls.generate_pool(draws, pool_size=200, rng=dim_rng)
        # 该维度候选中的最佳命中
        best = max((len(set(r) & actual_set) for r, _ in pool), default=0)
        dim_hits[dim_cls.name] = best

    return dim_hits


# ─── 主接口（兼容旧接口）───────────────────────────────────
def rank_candidates(
    draws: List[Draw],
    n_candidates: int = 1000,
    top_k: int = 5,
    persist: bool = True,
    actual_red: Optional[List[int]] = None,
    **kwargs,
) -> List[Tuple[List[int], int, Dict[str, float]]]:
    """
    兼容旧接口，使用持久化 LearningState。

    Args:
        persist: 是否从文件加载/保存学习状态
        actual_red: 可选的实际开奖红球，用于更新学习状态（回测时传入）
    """
    if persist:
        state = LearningState.load()
    else:
        state = LearningState(_DIM_NAMES)

    pool_per_dim = max(n_candidates // 7, 100)
    top_preds, full_pool = predict_v15(draws, state, top_k=top_k, pool_per_dim=pool_per_dim)
    filtered = _causal_filter(full_pool, top_k=top_k)
    result = filtered if filtered else top_preds

    # 如果有实际开奖数据，更新学习状态
    if actual_red is not None:
        actual_set = set(actual_red)
        round_hits = {}
        for dim_cls in DIMENSIONS:
            dim_hits = 0
            for item in full_pool[:100]:
                if isinstance(item, tuple) and len(item) >= 2:
                    red = item[0] if isinstance(item[0], list) else list(item[0])
                    dim_hits = max(dim_hits, len(set(red) & actual_set))
            round_hits[dim_cls.name] = dim_hits
        state.update(round_hits, actual_red)
        state.save()

    if persist and actual_red is None:
        state.save()

    return result


def predict_v14(draws: List[Draw], n_groups: int = 5, seed: int = 42):
    """兼容旧接口名"""
    state = LearningState(_DIM_NAMES)
    top_preds, _ = predict_v15(draws, state, top_k=n_groups, seed=seed)
    return top_preds


# ─── 兼容接口 ─────────────────────────────────────────────
def compute_field_potential(draws, recent_n=200):
    return {i: 1.0 for i in range(1, 34)}


def compute_blue_field_potential(draws, recent_n=30):
    return {i: 1.0 for i in range(1, 17)}


def compute_blue_transition_matrix(draws):
    return {i: {j: 1.0 / 16 for j in range(1, 17)} for i in range(1, 17)}


def generate_candidate_via_optimization(draws, field_pot, blue_pot, blue_trans, strategy="balanced"):
    rng = random.Random()
    return sorted(rng.sample(range(1, 34), 6)), rng.randint(1, 16)


def final_score(red, blue, history, prev_red=None, weights=None):
    return {"total_score": 0.5}


def similarity(a, b):
    return len(set(a) & set(b))


# ─── 测试 ─────────────────────────────────────────────────
if __name__ == "__main__":
    draws = load_history()
    actual = draws[-1]
    print(f"Period: #{actual.period}  Actual: {actual.red} + {actual.blue}")
    print()

    state = LearningState(_DIM_NAMES)

    # 30 轮回测
    all_hits = []
    for round_num in range(30):
        test_draws = draws[:-(round_num + 1)] if len(draws) > round_num + 1 else draws

        top_preds, full_pool = predict_v15(test_draws, state, top_k=5, seed=42 + round_num)

        best_hit = 0
        for red, blue, scores in full_pool[:100]:
            hits = len(set(red) & set(actual.red))
            if hits > best_hit:
                best_hit = hits

        all_hits.append(best_hit)
        print(f"Round {round_num + 1:2d}: best-of-100 hit = {best_hit}/6  top-5 best = {max(len(set(r) & set(actual.red)) for r,_,_ in top_preds)}/6")

        # 学习（虽然这里是离线测试，实际应该在线更新）
        dim_hits = learn_from_round(state, top_preds, actual.red)
        state.update(dim_hits, actual.red)

    print()
    print(f"Average best-of-100: {sum(all_hits) / len(all_hits):.2f}/6")
    print(f"Weights: {state.weights}")
    print(f"Exploration mode: {state.exploration_mode}")
