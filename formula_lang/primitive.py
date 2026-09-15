# -*- coding: utf-8 -*-
"""
Antigravity 公式语言 — 原语系统 V1.0

核心理念:
- 公式不是"设计"的，而是"生长"出来的
- 原语是一等公民：有名字、来源、类别、可突变参数
- 不是排列组合已知的数学函数，而是发明全新的原语
- 每个原语代表一种"对号码结构的假设"

六大原语类别:
1. 时序 (temporal) — 号码在时间序列中的记忆和回声
2. 关系 (relational) — 号码之间的结构性关系
3. 结构 (structural) — 号码内在结构特征
4. 频谱 (spectral) — 从频域角度理解号码
5. 几何 (geometric) — 号码在多维空间的几何关系
6. 混沌 (chaotic) — 混沌系统中的结构信号

用法:
    from formula_lang import Primitive, FormulaGrammar

    # 创建原语
    p1 = Primitive.temporal.periodic_echo(window=28, decay=0.95)
    p2 = Primitive.relational.cooccurrence_affinity(threshold=0.15)

    # 组合公式
    f = FormulaGrammar.resonance(p1, p2, phase=0.5)

    # 评估
    scores = f.evaluate_for_all_numbers(draws)  # 33个号码的分数
    top6 = f.rank_top_6()  # 返回 Top-6 号码
"""
import json
import math
import random
import copy
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from collections import Counter

_PROJECT_ROOT = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════
# 原语基类
# ═══════════════════════════════════════════════════════════

class Primitive:
    """
    公式原语 — 对33个号码打分的一等公民。

    每个原语代表一种"对号码结构的假设"。
    原语有完整的生命周期：诞生 → 验证 → 存活/淘汰 → 变异 → 重生

    参数:
        name: 原语名称
        category: 类别 (temporal/relational/structural/spectral/geometric/chaotic)
        description: 人类可读描述
        parameters: 可调参数
        origin: 来源 (manual/auto/gemini)
        uuid: 唯一标识
    """

    _registry: Dict[str, "Primitive"] = {}  # 全局注册表
    _counter = 0

    def __init__(self, name: str, category: str, description: str,
                 parameters: Optional[Dict] = None, origin: str = "manual",
                 uuid: Optional[str] = None):
        self.name = name
        self.category = category
        self.description = description
        self.parameters = parameters or {}
        self.origin = origin
        self.uuid = uuid or self._next_uuid()
        self.birth_time = datetime.now().isoformat()
        self.performance_history: List[Dict] = []  # 性能记录
        self.children: List[str] = []  # 变异后代UUID
        self.parents: List[str] = []  # 父原语UUID

        Primitive._registry[self.uuid] = self

    @classmethod
    def _next_uuid(cls) -> str:
        Primitive._counter += 1
        return f"prim_{Primitive._counter:06d}"

    @classmethod
    def registry(cls) -> Dict[str, "Primitive"]:
        return dict(cls._registry)

    @classmethod
    def clear_registry(cls):
        cls._registry.clear()
        cls._counter = 0

    def score_number(self, n: int, draws: Any) -> float:
        """
        对单个号码n打分。子类必须实现。

        Args:
            n: 号码 (1-33)
            draws: 历史开奖数据 (Draw列表)
        Returns:
            分数 (float)，越高表示该号码越可能被选中
        """
        raise NotImplementedError

    def score_all(self, draws: Any) -> Dict[int, float]:
        """对33个号码全部打分"""
        return {n: self.score_number(n, draws) for n in range(1, 34)}

    def mutate(self, draws: Any, rng: Optional[random.Random] = None) -> "Primitive":
        """
        变异这个原语 — 逻辑级变异（换内部操作）或参数级变异（调参数值）。

        子类可以重写以实现特定的变异策略。
        """
        rng = rng or random.Random()
        mutated = copy.deepcopy(self)

        # 参数级变异
        if rng.random() < 0.6:
            for key in mutated.parameters:
                if isinstance(mutated.parameters[key], (int, float)):
                    mutated.parameters[key] = mutated.parameters[key] * (1 + rng.gauss(0, 0.2))

        # 逻辑级变异（子类实现）
        mutated = self._logical_mutate(mutated, rng, draws)

        mutated.parents = [self.uuid]
        mutated.birth_time = datetime.now().isoformat()
        mutated.origin = "evolved"

        return mutated

    def _logical_mutate(self, mutated: "Primitive", rng: random.Random, draws: Any) -> "Primitive":
        """逻辑级变异 — 换内部操作。子类重写。"""
        return mutated

    def to_dict(self) -> Dict:
        """序列化"""
        return {
            "uuid": self.uuid,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "parameters": self.parameters,
            "origin": self.origin,
            "birth_time": self.birth_time,
            "performance_history": self.performance_history[-10:],  # 只保留最近10条
            "children": self.children,
            "parents": self.parents,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Primitive":
        """反序列化"""
        prim = cls(
            name=d["name"],
            category=d["category"],
            description=d["description"],
            parameters=d.get("parameters", {}),
            origin=d.get("origin", "manual"),
            uuid=d.get("uuid"),
        )
        prim.performance_history = d.get("performance_history", [])
        prim.children = d.get("children", [])
        prim.parents = d.get("parents", [])
        return prim

    def __repr__(self):
        return f"<Primitive[{self.category}] {self.name} ({self.uuid})>"


# ═══════════════════════════════════════════════════════════
# 类别1: 时序原语 (Temporal Primitives)
# ═══════════════════════════════════════════════════════════

class PeriodicEcho(Primitive):
    """
    周期性回声原语

    核心假设: 如果时间不存在，号码的出现模式会有周期性回声。
    某个号码在t期出现，可能在t+k期再次出现（k是某个周期）。

    计算方法: 对每个号码n，计算它在历史中出现的时间间隔序列，
    检测这些间隔是否有周期性。有周期的号码得分高。
    """

    def __init__(self, window: int = 28, decay: float = 0.95, min_periods: int = 3):
        super().__init__(
            name="periodic_echo",
            category="temporal",
            description="检测号码出现间隔的周期性 — 有周期性的号码得分高",
            parameters={"window": window, "decay": decay, "min_periods": min_periods},
        )
        self.window = window
        self.decay = decay
        self.min_periods = min_periods

    def score_number(self, n: int, draws: Any) -> float:
        # 提取号码n的出现间隔
        intervals = []
        last_pos = -1
        for i, draw in enumerate(draws):
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            if n in reds:
                if last_pos >= 0:
                    intervals.append(i - last_pos)
                last_pos = i

        if len(intervals) < self.min_periods:
            return 0.0

        # 计算间隔的周期性：看间隔序列是否有重复模式
        if len(intervals) < 3:
            return 0.0

        # 用自相关检测周期性
        mean_interval = sum(intervals) / len(intervals)
        variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)

        if variance < 1e-10:
            return 1.0  # 间隔完全一致 = 强周期

        # 计算间隔的标准差/均值比（CV），越小越有周期
        cv = math.sqrt(variance) / max(mean_interval, 1)

        # 衰减加权：最近的周期权重更高
        weighted_cv = 0
        total_weight = 0
        for i, iv in enumerate(intervals):
            w = self.decay ** (len(intervals) - 1 - i)
            weighted_cv += (iv - mean_interval) ** 2 * w
            total_weight += w

        if total_weight > 0:
            weighted_cv = math.sqrt(weighted_cv / total_weight) / max(mean_interval, 1)

        # V3.0 修复：CV 不一定都 > 0.5，用线性映射到 0-1
        # CV=0 → score=1, CV=1 → score=0
        return max(0, min(1, 1.0 - cv))


class RecencyGradient(Primitive):
    """
    近期梯度原语

    核心假设: 号码的出现倾向不是均匀的，而是随时间变化的。
    近期（近N期）的表现比远期更有预测价值。

    计算方法: 对每个号码，计算近期出现频率 vs 远期出现频率的梯度。
    梯度大的号码（近期趋势明显）得分高。
    """

    def __init__(self, recent_window: int = 50, far_window: int = 200, decay: float = 0.97):
        super().__init__(
            name="recency_gradient",
            category="temporal",
            description="计算号码近期vs远期的频率梯度 — 趋势明显的号码得分高",
            parameters={"recent_window": recent_window, "far_window": far_window, "decay": decay},
        )
        self.recent_window = recent_window
        self.far_window = far_window
        self.decay = decay

    def score_number(self, n: int, draws: Any) -> float:
        recent_count = 0
        far_count = 0
        recent_weight = 0
        far_weight = 0

        for i, draw in enumerate(draws):
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            decay = self.decay ** i  # 越近权重越大

            if n in reds:
                if i < self.recent_window:
                    recent_count += decay
                    recent_weight += decay
                elif i < self.far_window:
                    far_count += decay
                    far_weight += decay

        recent_freq = recent_count / max(recent_weight, 1)
        far_freq = far_count / max(far_weight, 1)

        # 梯度 = 近期频率 - 远期频率
        gradient = recent_freq - far_freq

        # 梯度越大（近期越热），得分越高
        # 梯度越小（近期越冷），也有一定得分（回补预期）
        return abs(gradient)


class SeasonalResonance(Primitive):
    """
    季节共振原语

    核心假设: 号码的出现可能有季节性模式（以50期为一个小周期）。

    计算方法: 将历史数据分成多个"季节"窗口，检测号码在每个季节的表现是否一致。
    一致的号码 = 有季节性共振。
    """

    def __init__(self, season_size: int = 50, n_seasons: int = 10):
        super().__init__(
            name="seasonal_resonance",
            category="temporal",
            description="检测号码的季节性共振模式 — 跨季节表现一致的号码得分高",
            parameters={"season_size": season_size, "n_seasons": n_seasons},
        )
        self.season_size = season_size
        self.n_seasons = n_seasons

    def score_number(self, n: int, draws: Any) -> float:
        n_draws = len(draws)
        if n_draws < self.season_size * 2:
            return 0.5

        # 分成多个季节窗口
        season_freqs = []
        for s in range(min(self.n_seasons, n_draws // self.season_size)):
            start = s * self.season_size
            end = start + self.season_size
            count = sum(1 for d in draws[start:end]
                       if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
            season_freqs.append(count / 6)  # 归一化到0-1

        if len(season_freqs) < 2:
            return 0.5

        # 计算频率的一致性（标准差越小越一致）
        mean_f = sum(season_freqs) / len(season_freqs)
        variance = sum((f - mean_f) ** 2 for f in season_freqs) / len(season_freqs)

        # 一致性越高，得分越高
        return max(0, 1.0 - math.sqrt(variance) * 3)


# ═══════════════════════════════════════════════════════════
# 类别2: 关系原语 (Relational Primitives)
# ═══════════════════════════════════════════════════════════

class CooccurrenceAffinity(Primitive):
    """
    共现亲和度原语

    核心假设: 号码之间存在结构性共现关系。某些号码"天生"倾向于一起出现。
    这种关系不是随机的，而是由场的结构决定的。

    计算方法: 对每个号码n，计算它与最近开奖中6个号码的共现强度。
    共现强度高的号码得分高。
    """

    def __init__(self, lookback: int = 100, threshold: float = 0.15):
        super().__init__(
            name="cooccurrence_affinity",
            category="relational",
            description="计算号码与共现强关联号码的亲和度 — 与近期号码共现强的得分高",
            parameters={"lookback": lookback, "threshold": threshold},
        )
        self.lookback = lookback
        self.threshold = threshold

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 构建共现矩阵
        cooccur = [[0] * 34 for _ in range(34)]
        freq = Counter()

        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for num in reds:
                freq[num] += 1
            reds_sorted = sorted(reds)
            for i in range(len(reds_sorted)):
                for j in range(i + 1, len(reds_sorted)):
                    cooccur[reds_sorted[i]][reds_sorted[j]] += 1
                    cooccur[reds_sorted[j]][reds_sorted[i]] += 1

        total = len(recent_draws)
        expected = (6 / 33) * (5 / 32) * total

        # 计算n与其他号码的超额共现
        affinity = 0
        for m in range(1, 34):
            if m == n:
                continue
            obs = cooccur[n][m]
            exc = (obs - expected) / max(expected, 1)
            if exc > self.threshold:
                affinity += exc

        return max(0, affinity / 10)  # 归一化


class MutualExclusionScore(Primitive):
    """
    互斥评分原语

    核心假设: 有些号码对"互斥"——它们很少同时出现。
    如果最近出现了其中一个，另一个可能即将出现（互补关系）。

    计算方法: 对每个号码n，计算它与最近开奖中号码的互斥强度。
    互斥强度高的号码（与近期号码互斥）得分高 — 因为它们可能即将"回补"。
    """

    def __init__(self, lookback: int = 100):
        super().__init__(
            name="mutual_exclusion",
            category="relational",
            description="计算号码的互斥回补潜力 — 与近期号码互斥的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 计算n与每个其他号码的互斥度
        cooccur = Counter()
        freq = Counter()

        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for num in reds:
                freq[num] += 1
            reds_sorted = sorted(reds)
            for i in range(len(reds_sorted)):
                for j in range(i + 1, len(reds_sorted)):
                    cooccur[(reds_sorted[i], reds_sorted[j])] += 1

        total = len(recent_draws)
        expected = (6 / 33) * (5 / 32) * total

        # 计算n的互斥得分
        exclusion = 0
        for m in range(1, 34):
            if m == n:
                continue
            key = (min(n, m), max(n, m))
            obs = cooccur.get(key, 0)
            # 观测 << 期望 = 强互斥
            deficit = (expected - obs) / max(expected, 1)
            if deficit > 0:
                exclusion += deficit

        return max(0, exclusion / 20)


class PairOrbit(Primitive):
    """
    配对轨道原语

    核心假设: 号码对（如[1,33]、[8,24]）在历史中有固定的"轨道"——
    它们交替出现，形成一个周期性的舞蹈。

    计算方法: 对每个号码n，找到它最常配对的其他号码，
    然后看这些配对当前的"轨道相位"——如果配对很久没出现了，
    说明轨道即将回到n。
    """

    def __init__(self, lookback: int = 200):
        super().__init__(
            name="pair_orbit",
            category="relational",
            description="检测号码对的轨道相位 — 久未配对的号码对即将回归",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 找n的最佳配对
        pair_last_seen = {}  # (n, m) -> 距离上次共现的期数
        pair_freq = Counter()

        for i, draw in enumerate(reversed(recent_draws)):
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for m in reds:
                if m != n:
                    pair_freq[(n, m)] += 1

        if not pair_freq:
            return 0.5

        # 找n的前3个最强配对
        top_pairs = pair_freq.most_common(3)

        # 计算这些配对多久没出现了
        orbit_score = 0
        for (a, b), _ in top_pairs:
            for i, draw in enumerate(reversed(recent_draws)):
                reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
                if a in reds and b in reds:
                    orbit_score += 1.0 / (i + 1)  # 越久没出现，权重越大
                    break

        return min(orbit_score, 1.0)


# ═══════════════════════════════════════════════════════════
# 类别3: 结构原语 (Structural Primitives)
# ═══════════════════════════════════════════════════════════

class BinaryTopology(Primitive):
    """
    二进制拓扑原语

    核心假设: 号码的二进制表示不是随机的，它们在二进制空间中
    有特定的拓扑结构。某些二进制模式与开奖结果相关。

    计算方法: 对每个号码，计算其二进制表示的拓扑特征：
    - 二进制中1的分布（高位vs低位）
    - 二进制回文性
    - 二进制与历史模式的匹配度
    """

    def __init__(self, lookback: int = 100):
        super().__init__(
            name="binary_topology",
            category="structural",
            description="分析号码二进制表示的拓扑特征 — 与历史模式匹配的得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def _binary_features(self, n: int) -> Dict:
        """提取号码n的二进制特征"""
        bits = bin(n)[2:]
        return {
            "weight": bits.count('1'),
            "length": len(bits),
            "palindrome": bits == bits[::-1],
            "high_bits": bits[:len(bits)//2].count('1'),
            "low_bits": bits[len(bits)//2:].count('1'),
            "leading_zeros": 5 - len(bits),  # 5-bit representation
        }

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 统计近期开奖中各二进制特征的分布
        feature_counts = Counter()
        total_bits = 0

        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                feats = self._binary_features(r)
                for k, v in feats.items():
                    feature_counts[(k, v)] += 1
                    total_bits += 1

        # 计算n的二进制特征与历史模式的匹配度
        n_feats = self._binary_features(n)
        score = 0
        for k, v in n_feats.items():
            freq = feature_counts.get((k, v), 0) / max(total_bits, 1)
            score += freq

        return min(score / len(n_feats), 1.0)


class DigitManifold(Primitive):
    """
    数位流形原语

    核心假设: 号码的数位（十进制）不是独立的，它们在数位空间中
    形成了某种"流形"结构。某些数位组合模式与开奖相关。

    计算方法: 对每个号码，计算其数位特征与历史数位模式的匹配度。
    """

    def __init__(self, lookback: int = 100):
        super().__init__(
            name="digit_manifold",
            category="structural",
            description="分析号码数位特征的流形结构 — 与历史数位模式匹配的得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def _digit_features(self, n: int) -> Dict:
        s = str(n)
        return {
            "sum": sum(int(d) for d in s),
            "product": eval('*'.join(s)) if '0' not in s else 0,
            "unique_digits": len(set(s)),
            "sorted_digits": ''.join(sorted(s)),
            "reverse": int(s[::-1]) if len(s) > 1 else n,
            "diff_max_min": max(int(d) for d in s) - min(int(d) for d in s),
        }

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        feature_freq = Counter()
        total = 0

        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                feats = self._digit_features(r)
                for k, v in feats.items():
                    feature_freq[(k, v)] += 1
                    total += 1

        n_feats = self._digit_features(n)
        score = sum(feature_freq.get((k, v), 0) / max(total, 1) for k, v in n_feats.items())

        return min(score / len(n_feats), 1.0)


class PositionSignature(Primitive):
    """
    位置签名原语

    核心假设: 双色球红球排序后有6个位置，每个位置上的号码有特定的分布。
    号码n在位置i的"签名"（历史出现频率、遗漏、趋势）可以用来预测它
    在下期出现在哪个位置。

    计算方法: 对每个号码n，计算它在6个位置上的历史分布，
    然后与最近开奖的模式比较，匹配度高的得分高。
    """

    def __init__(self, lookback: int = 100):
        super().__init__(
            name="position_signature",
            category="structural",
            description="分析号码在6个位置上的历史分布签名 — 与近期位置模式匹配的得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 统计n在6个位置上的频率
        pos_freq = Counter()
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for i, r in enumerate(reds):
                if r == n:
                    pos_freq[i] += 1

        if not pos_freq:
            return 0.5

        # 找n最常出现的位置
        dominant_pos = pos_freq.most_common(1)[0][0]

        # 计算n在主导位置上的频率
        total = sum(pos_freq.values())
        dominant_freq = pos_freq[dominant_pos] / max(total, 1)

        return dominant_freq


# ═══════════════════════════════════════════════════════════
# 类别4: 频谱原语 (Spectral Primitives)
# ═══════════════════════════════════════════════════════════

class SpectralPower(Primitive):
    """
    频谱功率原语

    核心假设: 号码的出现序列在频域中有特定的功率分布。
    某些号码在特定频率上有显著的功率峰值。

    计算方法: 对每个号码，构建其二进制出现序列，做FFT，
    看在哪些频率上有功率峰值。有峰值的号码得分高。
    """

    def __init__(self, lookback: int = 200, min_peaks: int = 1):
        super().__init__(
            name="spectral_power",
            category="spectral",
            description="分析号码出现序列的频谱功率 — 有显著频率峰值的得分高",
            parameters={"lookback": lookback, "min_peaks": min_peaks},
        )
        self.lookback = lookback
        self.min_peaks = min_peaks

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 构建二进制序列
        seq = [1 if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))) else 0
               for d in recent_draws]

        n_seq = len(seq)
        if n_seq < 20:
            return 0.5

        # 简单FFT（不用numpy，避免依赖）
        # 计算各频率的功率
        powers = []
        for k in range(2, n_seq // 2):
            re = sum(seq[i] * math.cos(2 * math.pi * k * i / n_seq) for i in range(n_seq))
            im = sum(seq[i] * math.sin(2 * math.pi * k * i / n_seq) for i in range(n_seq))
            power = (re ** 2 + im ** 2) / (n_seq ** 2)
            powers.append((k, power))

        if not powers:
            return 0.5

        # 找功率峰值
        mean_power = sum(p for _, p in powers) / len(powers)
        std_power = math.sqrt(sum((p - mean_power) ** 2 for _, p in powers) / len(powers))

        peaks = [(freq, power) for freq, power in powers if power > mean_power + 2 * std_power]

        if len(peaks) < self.min_peaks:
            return 0.3

        # 峰值功率越高，得分越高
        peak_power_sum = sum(power for _, power in peaks)
        return min(peak_power_sum / (mean_power * len(powers)), 1.0)


class WaveletCoherence(Primitive):
    """
    小波相干性原语

    核心假设: 号码的出现模式在不同尺度（短期/中期/长期）上
    有不同的相干性。某些号码在多个尺度上都表现出相干性。

    计算方法: 对每个号码，计算其在不同尺度窗口内的出现密度变化。
    多尺度相干的号码得分高。
    """

    def __init__(self, scales: List[int] = None):
        super().__init__(
            name="wavelet_coherence",
            category="spectral",
            description="分析号码在多尺度上的出现相干性 — 多尺度一致的得分高",
            parameters={"scales": scales or [10, 30, 60, 120]},
        )
        self.scales = scales or [10, 30, 60, 120]

    def score_number(self, n: int, draws: Any) -> float:
        n_draws = len(draws)

        # 对每个尺度计算出现密度
        densities = []
        for scale in self.scales:
            if scale >= n_draws:
                continue
            windows = n_draws // scale
            window_densities = []
            for w in range(windows):
                start = w * scale
                count = sum(1 for d in draws[start:start + scale]
                           if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
                window_densities.append(count / 6)
            if window_densities:
                densities.append(window_densities)

        if len(densities) < 2:
            return 0.5

        # 计算各尺度的密度稳定性（标准差越小越稳定）
        stabilities = []
        for window_dens in densities:
            mean_d = sum(window_dens) / len(window_dens)
            var_d = sum((d - mean_d) ** 2 for d in window_dens) / len(window_dens)
            stabilities.append(1.0 / (1.0 + math.sqrt(var_d)))

        # 多尺度一致性 = 稳定性的相关性
        if len(stabilities) < 2:
            return max(stabilities) if stabilities else 0.5

        mean_s = sum(stabilities) / len(stabilities)
        cov = sum((s - mean_s) ** 2 for s in stabilities) / len(stabilities)

        return max(0, 1.0 - math.sqrt(cov))


# ═══════════════════════════════════════════════════════════
# 类别5: 几何原语 (Geometric Primitives)
# ═══════════════════════════════════════════════════════════

class SphereProjection(Primitive):
    """
    球面投影原语

    核心假设: 33个号码可以在球面上均匀分布（类似黄金角度分布）。
    每个号码在球面上有一个固定位置。开奖结果对应球面上的一个"构型"。
    如果时间不存在，这个构型不是随机的，而是由球的几何结构决定的。

    计算方法: 将33个号码映射到球面上，计算每个号码与近期开奖
    "质心"的距离。距离近的号码得分高。
    """

    def __init__(self, lookback: int = 50):
        super().__init__(
            name="sphere_projection",
            category="geometric",
            description="将球面投影分析 — 靠近近期开奖质心的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    @staticmethod
    def _sphere_coords(n: int) -> Tuple[float, float, float]:
        """用黄金角度将球面上的点均匀分布"""
        golden_angle = math.pi * (3 - math.sqrt(5))
        i = n - 1
        y = 1 - (i / 32) * 2
        radius = math.sqrt(max(0, 1 - y * y))
        theta = golden_angle * i
        return (math.cos(theta) * radius, y, math.sin(theta) * radius)

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 计算近期开奖的球面质心
        centroid = [0.0, 0.0, 0.0]
        count = 0
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                cx, cy, cz = self._sphere_coords(r)
                centroid[0] += cx
                centroid[1] += cy
                centroid[2] += cz
                count += 1

        if count == 0:
            return 0.5
        centroid = [c / count for c in centroid]

        # 计算n到质心的距离
        nx, ny, nz = self._sphere_coords(n)
        dist = math.sqrt((nx - centroid[0]) ** 2 + (ny - centroid[1]) ** 2 + (nz - centroid[2]) ** 2)

        # 距离越小，得分越高
        return max(0, 1.0 - dist / 2.0)


class DistanceCluster(Primitive):
    """
    距离聚类原语

    核心假设: 号码之间的欧氏距离（在某种特征空间中）不是随机的。
    某些号码对在历史上倾向于以特定距离出现。

    计算方法: 对每个号码n，计算它与近期开奖中号码的平均距离，
    然后看这个距离是否与历史平均距离一致。
    """

    def __init__(self, lookback: int = 100):
        super().__init__(
            name="distance_cluster",
            category="geometric",
            description="分析号码的距离聚类模式 — 与历史聚类结构一致的得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 计算n与每个其他号码的历史平均距离（基于共现模式）
        # 这里用简单的"共同出现频率"作为距离的反比
        cooccur_freq = Counter()
        freq = Counter()

        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                freq[r] += 1
            reds_sorted = sorted(reds)
            for i in range(len(reds_sorted)):
                for j in range(i + 1, len(reds_sorted)):
                    cooccur_freq[(reds_sorted[i], reds_sorted[j])] += 1

        # 计算n的聚类得分
        cluster_score = 0
        for m in range(1, 34):
            if m == n:
                continue
            key = (min(n, m), max(n, m))
            score = cooccur_freq.get(key, 0) / max(freq[m], 1)
            cluster_score += score

        return min(cluster_score / 33, 1.0)


# ═══════════════════════════════════════════════════════════
# 类别6: 混沌原语 (Chaotic Primitives)
# ═══════════════════════════════════════════════════════════

class AttractorDistance(Primitive):
    """
    吸引子距离原语

    核心假设: 如果开奖过程是混沌的（确定性但有初始条件敏感性），
    那么状态空间中存在"吸引子"——某些状态倾向于被系统返回。

    计算方法: 用相空间重构（embedding）找到近期的状态，
    对每个号码n，计算如果n出现在下期，它距离吸引子有多近。
    距离近的得分高。
    """

    def __init__(self, dim: int = 3, tau: int = 5, lookback: int = 500):
        super().__init__(
            name="attractor_distance",
            category="chaotic",
            description="分析混沌吸引子距离 — 靠近吸引子的号码得分高",
            parameters={"dim": dim, "tau": tau, "lookback": lookback},
        )
        self.dim = dim
        self.tau = tau
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < self.dim * self.tau + 10:
            return 0.5

        # 用多特征序列做相空间重构（不只是和值，用更多统计量）
        features = []
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            s = sum(reds)
            odd_count = sum(1 for r in reds if r % 2 == 1)
            min_r = min(reds)
            max_r = max(reds)
            features.append([s, odd_count, min_r, max_r])

        # 构建嵌入向量
        embeddings = []
        for i in range(0, len(features) - (self.dim - 1) * self.tau, self.tau):
            vec = []
            for j in range(self.dim):
                idx = i + j * self.tau
                if idx < len(features):
                    vec.extend(features[idx])
            embeddings.append(vec)

        if len(embeddings) < 3:
            return 0.5

        # 计算最近K个嵌入向量的质心
        k = min(10, len(embeddings))
        latest_k = embeddings[-k:]
        dim_len = len(latest_k[0])
        centroid = [sum(e[j] for e in latest_k) / k for j in range(dim_len)]

        # 对每个号码n，计算如果n出现在下期，特征向量会如何变化
        # 用n替换近期开奖中的一个随机号码，看新特征距离质心多远
        last_draw = recent_draws[0]
        last_reds = last_draw.reds if hasattr(last_draw, 'reds') else sorted(list(last_draw.red))

        # 模拟：用n替换last_reds中的最小号码，计算新特征
        sim_reds = list(last_reds)
        removed = min(sim_reds)
        sim_reds[sim_reds.index(removed)] = n
        sim_reds.sort()

        new_s = sum(sim_reds)
        new_odd = sum(1 for r in sim_reds if r % 2 == 1)
        new_min = min(sim_reds)
        new_max = max(sim_reds)

        # 欧氏距离
        dist = math.sqrt((new_s - centroid[0])**2 + (new_odd - centroid[1])**2 +
                         (new_min - centroid[2])**2 + (new_max - centroid[3])**2)

        # 距离越小，得分越高
        return max(0, 1.0 - dist / 100.0)


class LyapunovSignal(Primitive):
    """
    李雅普诺夫信号原语

    核心假设: 混沌系统的特征是李雅普诺夫指数为正——
    邻近轨迹指数发散。但如果我们能检测到"收敛"的时刻，
    那就是预测的好时机。

    计算方法: 对和值序列计算局部李雅普诺夫指数，
    检测"收敛窗口"。在收敛窗口内，号码的预测更可靠。
    """

    def __init__(self, lookback: int = 200, window: int = 30):
        super().__init__(
            name="lyapunov_signal",
            category="chaotic",
            description="分析李雅普诺夫信号 — 在收敛窗口内的号码得分高",
            parameters={"lookback": lookback, "window": window},
        )
        self.lookback = lookback
        self.window = window

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < self.window * 2:
            return 0.5

        sums = [sum(d.reds if hasattr(d, 'reds') else sorted(list(d.red))) for d in recent_draws]

        # 计算最近窗口的和值变化率
        window_sums = sums[-self.window:]
        changes = [abs(window_sums[i + 1] - window_sums[i]) for i in range(len(window_sums) - 1)]

        if not changes:
            return 0.5

        # 变化率越小 = 越收敛 = 越可预测
        avg_change = sum(changes) / len(changes)
        convergence = max(0, 1.0 - avg_change / 30.0)  # 归一化

        # 号码n在收敛窗口中的频率
        n_in_window = sum(1 for d in recent_draws[-self.window:]
                         if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
        n_freq = n_in_window / self.window

        # 收敛 × 近期频率
        return convergence * (0.5 + n_freq)


# ═══════════════════════════════════════════════════════════
# 新增原语类别7: 序列模式 (Sequence Pattern Primitives)
# ═══════════════════════════════════════════════════════════

class SumRangeTracker(Primitive):
    """
    和值区间追踪原语

    核心假设: 每期6个红球的和值(6-198)不是均匀分布的，
    而是在一个狭窄区间内震荡。和值区间的变化携带预测信号。

    计算方法: 对每个号码n，计算当和值处于不同区间时，
    n的出现频率。在和值即将进入高频率区间的号码得分高。
    """

    def __init__(self, lookback: int = 200, n_bins: int = 6):
        super().__init__(
            name="sum_range_tracker",
            category="sequence_pattern",
            description="分析和值区间变化中的号码频率 — 和值即将进入高频率区的号码得分高",
            parameters={"lookback": lookback, "n_bins": n_bins},
        )
        self.lookback = lookback
        self.n_bins = n_bins

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < 20:
            return 0.5

        # 计算每期号码集合的特征
        sum_features = []
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            s = sum(reds)
            avg = s / 6
            n_count = sum(1 for r in reds if r == n)
            sum_features.append((s, avg, n_count))

        # 按和值分箱
        sums = [sf[0] for sf in sum_features]
        bin_edges = [min(sums) + i * (max(sums) - min(sums)) / self.n_bins
                     for i in range(self.n_bins + 1)]

        # 计算每个箱中n的出现频率
        bin_freq = []
        for i in range(self.n_bins):
            count = sum(1 for sf in sum_features
                       if bin_edges[i] <= sf[0] < bin_edges[i + 1] and sf[2] > 0)
            total = sum(1 for sf in sum_features
                       if bin_edges[i] <= sf[0] < bin_edges[i + 1])
            bin_freq.append(count / max(total, 1))

        if not bin_freq:
            return 0.5

        # 找n频率最高的箱
        max_bin_idx = max(range(len(bin_freq)), key=lambda i: bin_freq[i])

        # 看和值序列的趋势：最近5期和值是上升还是下降？
        recent_sums = [sf[0] for sf in sum_features[-5:]]
        if len(recent_sums) >= 3:
            slope = recent_sums[-1] - recent_sums[0]
            trend = 1 if slope > 0 else -1
        else:
            trend = 0

        # 如果趋势指向高频率箱，得分高
        bin_center = (bin_edges[max_bin_idx] + bin_edges[max_bin_idx + 1]) / 2
        current_sum = recent_sums[-1] if recent_sums else 100

        if trend > 0 and current_sum < bin_center:
            return bin_freq[max_bin_idx] * 1.5  # 趋势向上，向高频率区移动
        elif trend < 0 and current_sum > bin_center:
            return bin_freq[max_bin_idx] * 1.5  # 趋势向下，向高频率区移动
        else:
            return bin_freq[max_bin_idx]


class GapPatternAnalyzer(Primitive):
    """
    间隔模式分析原语

    核心假设: 号码之间的间隔(差值)不是随机的。
    某些间隔模式(如3-5-7-9-11-13)在历史上反复出现。

    计算方法: 对每个号码n，计算它与其他号码的间隔频率，
    找那些在历史上"经常一起出现"的间隔模式。
    """

    def __init__(self, lookback: int = 200):
        super().__init__(
            name="gap_pattern",
            category="sequence_pattern",
            description="分析号码间隔模式 — 与历史常见间隔模式匹配的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < 20:
            return 0.5

        # 统计所有号码对的间隔
        gap_freq = Counter()
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for i in range(len(reds)):
                for j in range(i + 1, len(reds)):
                    gap = reds[j] - reds[i]
                    gap_freq[gap] += 1

        # 计算n的"间隔得分" — n与周围号码的间隔是否在高频间隔中
        if not gap_freq:
            return 0.5

        total_gaps = sum(gap_freq.values())
        n_score = 0
        for gap, count in gap_freq.items():
            # 如果n-gap或n+gap在1-33范围内，说明n参与了这种间隔
            if 1 <= n - gap <= 33:
                n_score += count / total_gaps
            if 1 <= n + gap <= 33:
                n_score += count / total_gaps

        return min(n_score / 2, 1.0)  # 归一化


class TrendReversalDetector(Primitive):
    """
    趋势反转检测原语

    核心假设: 号码的出现频率有趋势性 — 热号会转冷，冷号会转热。
    趋势反转点是最佳预测时机。

    计算方法: 对每个号码，计算其近期频率趋势，
    检测是否即将发生反转（从热转冷或从冷转热的拐点）。
    """

    def __init__(self, lookback: int = 100, reversal_window: int = 20):
        super().__init__(
            name="trend_reversal",
            category="sequence_pattern",
            description="检测号码频率趋势反转点 — 即将反转的号码得分高",
            parameters={"lookback": lookback, "reversal_window": reversal_window},
        )
        self.lookback = lookback
        self.reversal_window = reversal_window

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < 40:
            return 0.5

        # 计算每期内n的出现情况
        appearances = []
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            appearances.append(1 if n in reds else 0)

        # 计算滚动窗口内的出现率
        window = self.reversal_window
        if len(appearances) < window * 2:
            return 0.5

        rolling_rates = []
        for i in range(0, len(appearances) - window, window // 2):
            rate = sum(appearances[i:i + window]) / window
            rolling_rates.append(rate)

        if len(rolling_rates) < 3:
            return 0.5

        # 检测趋势反转
        recent = rolling_rates[-3:]
        older = rolling_rates[:3]

        recent_trend = recent[-1] - recent[0]
        older_trend = older[-1] - older[0]

        # 如果趋势反转（之前上升现在下降，或反之），得分高
        if recent_trend * older_trend < 0:
            # 反转确认
            return 0.5 + abs(recent_trend) * 2
        else:
            # 趋势延续，得分较低
            return 0.3


# ═══════════════════════════════════════════════════════════
# 新增原语类别8: 组合特征 (Combinatorial Feature Primitives)
# ═══════════════════════════════════════════════════════════

class ModuloClassDistribution(Primitive):
    """
    模类分布原语

    核心假设: 号码除以某个数后的余数分布不是均匀的。
    例如号码除以7，余数为0-6的号码在开奖中有不同的出现倾向。

    计算方法: 对每个号码n，计算它在各个模类下的历史表现，
    在近期开奖中表现好的模类对应的号码得分高。
    """

    def __init__(self, moduli: List[int] = None, lookback: int = 200):
        super().__init__(
            name="modulo_distribution",
            category="combinatorial",
            description="分析号码模类分布 — 在近期表现好的模类号码得分高",
            parameters={"moduli": moduli or [3, 5, 7, 11, 13], "lookback": lookback},
        )
        self.moduli = moduli or [3, 5, 7, 11, 13]
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < 20:
            return 0.5

        # 计算n在各个模类下的余数
        mod_scores = []
        for mod in self.moduli:
            remainder = n % mod
            # 统计该余数在近期开奖中的出现频率
            freq = sum(1 for d in recent_draws[-50:]
                      if remainder in [r % mod for r in
                              (d.reds if hasattr(d, 'reds') else sorted(list(d.red)))]) / 50
            mod_scores.append(freq)

        return sum(mod_scores) / max(len(mod_scores), 1)


class DigitPairFrequency(Primitive):
    """
    数位对频率原语

    核心假设: 两位数的号码（如12, 23, 31）的数位组合（如1-2, 2-3, 3-1）
    在开奖中有特定的出现频率模式。

    计算方法: 对每个号码n，提取其数位对，
    计算这些数位对在历史中的共现频率。
    """

    def __init__(self, lookback: int = 200):
        super().__init__(
            name="digit_pair_freq",
            category="combinatorial",
            description="分析号码数位对的共现频率 — 数位对高频共现的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 提取n的数位对
        s = str(n)
        if len(s) < 2:
            return 0.5
        digit_pairs = [(int(s[i]), int(s[i + 1])) for i in range(len(s) - 1)]

        if not digit_pairs:
            return 0.5

        # 统计数位对在历史中的共现频率
        pair_freq = Counter()
        total = 0
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                rs = str(r)
                if len(rs) >= 2:
                    for i in range(len(rs) - 1):
                        pair_freq[(int(rs[i]), int(rs[i + 1]))] += 1
                        total += 1

        # 计算n的数位对频率
        score = sum(pair_freq.get(dp, 0) for dp in digit_pairs) / max(total, 1)
        return min(score * 10, 1.0)  # 归一化


class AdjacentNumberBias(Primitive):
    """
    邻号偏置原语

    核心假设: 双色球开奖中，相邻号码（如12和13）经常同时出现。
    如果上期开了12，下期11或13出现的概率会偏高。

    计算方法: 对每个号码n，计算它与上期开奖号码的邻号关系，
    以及历史中邻号共现的频率。
    """

    def __init__(self, lookback: int = 100):
        super().__init__(
            name="adjacent_bias",
            category="combinatorial",
            description="分析邻号偏置 — 与近期开奖号码相邻的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < 5:
            return 0.5

        # 计算n与最近5期开奖号码的邻号关系
        adjacent_count = 0
        for draw in recent_draws[-5:]:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                if abs(n - r) == 1:
                    adjacent_count += 1
                    break

        return adjacent_count / 5.0


# ═══════════════════════════════════════════════════════════
# 新增原语类别9: 高阶统计 (Higher-order Statistical Primitives)
# ═══════════════════════════════════════════════════════════

class SkewnessSignal(Primitive):
    """
    偏度信号原语

    核心假设: 号码出现频率的分布不是对称的，而是有偏度的。
    偏度的方向和大小携带预测信号。

    计算方法: 对每个号码，计算其在近期开奖中的频率相对于
    全体频率分布的偏度位置。偏度极端的号码得分高。
    """

    def __init__(self, lookback: int = 200):
        super().__init__(
            name="skewness_signal",
            category="higher_order",
            description="分析号码频率分布的偏度 — 位于偏度极端的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 计算每个号码的频率
        freq = Counter()
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                freq[r] += 1

        freq_values = [freq.get(i, 0) for i in range(1, 34)]
        mean_f = sum(freq_values) / 33
        var_f = sum((v - mean_f) ** 2 for v in freq_values) / 33
        std_f = math.sqrt(var_f) if var_f > 0 else 1

        # 计算偏度
        skew = sum((v - mean_f) ** 3 for v in freq_values) / (33 * std_f ** 3) if std_f > 0 else 0

        # n的频率相对于偏度极端值的位置
        n_freq = freq.get(n, 0)
        z_score = (n_freq - mean_f) / std_f if std_f > 0 else 0

        # 如果偏度为正（右偏），高频号码得分高
        # 如果偏度为负（左偏），低频号码得分高
        if skew > 0:
            return max(0, min(1, 0.5 + z_score * 0.3))
        else:
            return max(0, min(1, 0.5 - z_score * 0.3))


class KurtosisSignal(Primitive):
    """
    峰度信号原语

    核心假设: 号码频率分布的峰度（尖峭程度）反映了
    号码出现的"集中度"。高峰度 = 少数号码主导，
    低峰度 = 号码均匀分布。

    计算方法: 计算频率分布的峰度，
    在高峰度时期选主导号码，低峰度时期选冷门号码。
    """

    def __init__(self, lookback: int = 200):
        super().__init__(
            name="kurtosis_signal",
            category="higher_order",
            description="分析号码频率分布的峰度 — 根据峰度自适应选择主导或冷门号码",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        freq = Counter()
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                freq[r] += 1

        freq_values = [freq.get(i, 0) for i in range(1, 34)]
        mean_f = sum(freq_values) / 33
        var_f = sum((v - mean_f) ** 2 for v in freq_values) / 33
        std_f = math.sqrt(var_f) if var_f > 0 else 1

        # 峰度
        kurt = sum((v - mean_f) ** 4 for v in freq_values) / (33 * std_f ** 4) if std_f > 0 else 0

        n_freq = freq.get(n, 0)
        z_score = (n_freq - mean_f) / std_f if std_f > 0 else 0

        # 高峰度(kurt>3): 选主导号码(z>0)
        # 低峰度(kurt<3): 选冷门号码(z<0)
        if kurt > 3:
            return max(0, min(1, 0.5 + z_score * 0.25))
        else:
            return max(0, min(1, 0.5 - z_score * 0.25))


class TailRiskSignal(Primitive):
    """
    尾部风险信号原语

    核心假设: 号码出现频率的尾部（极端值）携带重要信号。
    长期未出现的号码（左尾）和频繁出现的号码（右尾）
    都有特殊的预测价值。

    计算方法: 对每个号码，计算其频率在历史分布中的尾部位置，
    尾部号码得分高。
    """

    def __init__(self, lookback: int = 200, tail_threshold: float = 0.9):
        super().__init__(
            name="tail_risk",
            category="higher_order",
            description="分析号码频率的尾部风险 — 极端频率号码得分高",
            parameters={"lookback": lookback, "tail_threshold": tail_threshold},
        )
        self.lookback = lookback
        self.tail_threshold = tail_threshold

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        freq = Counter()
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                freq[r] += 1

        freq_values = sorted([freq.get(i, 0) for i in range(1, 34)])
        n_freq = freq.get(n, 0)

        # 计算n的频率在排序中的百分位
        percentile = sum(1 for v in freq_values if v <= n_freq) / 33

        # 尾部号码（百分位>0.9或<0.1）得分高
        if percentile > self.tail_threshold or percentile < (1 - self.tail_threshold):
            return 0.5 + abs(percentile - 0.5)
        else:
            return 0.3


# ═══════════════════════════════════════════════════════════
# 新增原语类别10: 跨期记忆 (Cross-period Memory Primitives)
# ═══════════════════════════════════════════════════════════

class LagCorrelation(Primitive):
    """
    滞后相关原语

    核心假设: 号码在t期的出现与t-k期（k=1,2,3...）的出现
    存在滞后相关性。这种相关性不是简单的自相关，
    而是条件概率 — 如果号码n在k期前出现过，
    它在当前期出现的概率是多少？

    计算方法: 对每个号码n，计算不同滞后阶数k的条件概率，
    选择最优滞后阶数。
    """

    def __init__(self, max_lag: int = 5, lookback: int = 200):
        super().__init__(
            name="lag_correlation",
            category="cross_period_memory",
            description="分析号码的滞后相关性 — 最优滞后阶数条件概率高的号码得分高",
            parameters={"max_lag": max_lag, "lookback": lookback},
        )
        self.max_lag = max_lag
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < 20:
            return 0.5

        # 构建n的出现序列
        seq = [1 if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))) else 0
               for d in recent_draws]

        best_corr = 0
        for lag in range(1, self.max_lag + 1):
            if len(seq) < lag + 5:
                continue
            # 条件概率 P(Xt=1 | Xt-lag=1)
            n11 = sum(1 for i in range(lag, len(seq)) if seq[i] == 1 and seq[i - lag] == 1)
            n_lag1 = sum(1 for i in range(lag, len(seq)) if seq[i - lag] == 1)
            if n_lag1 > 0:
                cond_prob = n11 / n_lag1
                # 无条件概率
                base_prob = sum(seq) / len(seq)
                # 相关性 = 条件概率 - 基础概率
                corr = cond_prob - base_prob
                best_corr = max(best_corr, corr)

        return max(0, 0.5 + best_corr * 2)


class PeriodicGap(Primitive):
    """
    周期间隔原语

    核心假设: 号码的出现间隔不是随机的，而是有周期性的。
    某些号码每隔k期出现一次，形成固定的"节拍"。

    计算方法: 对每个号码n，计算其历史出现间隔序列，
    检测间隔序列的周期性。周期性强的号码得分高。
    """

    def __init__(self, lookback: int = 300):
        super().__init__(
            name="periodic_gap",
            category="cross_period_memory",
            description="分析号码出现间隔的周期性 — 间隔周期稳定的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 找n的出现位置（从最新到最旧）
        positions = [i for i, d in enumerate(reversed(recent_draws))
                    if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red)))]

        if len(positions) < 2:
            # 极少出现的号码给一个基于历史总频率的基础分
            total_freq = sum(1 for d in draws
                           if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
            return 0.3 + (total_freq / len(draws)) * 3

        # 计算间隔
        gaps = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]

        if not gaps:
            return 0.5

        # 计算间隔的变异系数（CV）
        mean_gap = sum(gaps) / len(gaps)
        var_gap = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
        std_gap = math.sqrt(var_gap)

        cv = std_gap / max(mean_gap, 1)

        # CV越小，周期越稳定，得分越高
        periodicity_score = max(0, 1.0 - cv * 2)

        # 加上"即将到期"信号：当前遗漏接近平均间隔
        current_omission = positions[0] if positions else 0
        proximity_to_due = max(0, 1.0 - abs(current_omission - mean_gap) / (mean_gap * 2))

        # 综合：周期性 + 即将到期
        return 0.4 * periodicity_score + 0.6 * proximity_to_due


class RecurrenceWindow(Primitive):
    """
    重现窗口原语

    核心假设: 号码n上一次出现距今已经k期，
    根据历史统计，号码n在出现后第k+m期再次出现的概率
    有一个"重现窗口"模式。

    计算方法: 对每个号码n，计算其历史重现窗口，
    当前遗漏期数接近重现窗口峰值的号码得分高。
    """

    def __init__(self, lookback: int = 500):
        super().__init__(
            name="recurrence_window",
            category="cross_period_memory",
            description="分析号码的重现窗口 — 当前遗漏接近历史重现峰值的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]

        # 找n的所有出现位置
        positions = [i for i, d in enumerate(reversed(recent_draws))
                    if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red)))]

        if len(positions) < 3:
            return 0.5

        # 计算重现间隔
        gaps = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]

        # 当前遗漏期数
        current_omission = positions[0] if positions else 0

        # 找重现间隔的众数
        from collections import Counter
        gap_counts = Counter(gaps)
        most_common_gap = gap_counts.most_common(1)[0][0] if gap_counts else 0

        # 如果当前遗漏接近历史重现间隔的众数，得分高
        if most_common_gap > 0:
            proximity = 1.0 - abs(current_omission - most_common_gap) / max(most_common_gap * 3, 1)
            return max(0, proximity)

        return 0.5


# ═══════════════════════════════════════════════════════════
# 新增原语类别11: 多尺度分析 (Multi-scale Analysis Primitives)
# ═══════════════════════════════════════════════════════════

class MultiScaleFrequency(Primitive):
    """
    多尺度频率原语

    核心假设: 号码的频率在不同时间尺度（短期/中期/长期）
    有不同的表现。某些号码在短期热但在长期冷，
    这种多尺度不一致性携带预测信号。

    计算方法: 对每个号码，计算其在3个尺度（10/50/200期）的频率，
    找尺度间频率差异最大的号码。
    """

    def __init__(self, scales: List[int] = None):
        super().__init__(
            name="multi_scale_frequency",
            category="multi_scale",
            description="分析号码的多尺度频率 — 尺度间频率差异大的号码得分高",
            parameters={"scales": scales or [10, 50, 200]},
        )
        self.scales = scales or [10, 50, 200]

    def score_number(self, n: int, draws: Any) -> float:
        freqs = []
        for scale in self.scales:
            recent = draws[-min(scale, len(draws)):]
            count = sum(1 for d in recent
                       if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
            freqs.append(count / max(len(recent) * 6, 1))

        if len(freqs) < 2:
            return 0.5

        # 频率的标准差 = 多尺度不一致性
        mean_f = sum(freqs) / len(freqs)
        std_f = math.sqrt(sum((f - mean_f) ** 2 for f in freqs) / len(freqs))

        # 标准差越大，多尺度差异越大，得分越高
        return min(1.0, std_f * 10)


class ScaleTransition(Primitive):
    """
    尺度转换原语

    核心假设: 号码的频率在不同尺度之间有"转换"模式。
    例如从短期到中期频率上升的号码，可能正处于"升温"阶段。

    计算方法: 对每个号码，计算相邻尺度间的频率变化率，
    变化率方向一致的号码得分高。
    """

    def __init__(self, scales: List[int] = None):
        super().__init__(
            name="scale_transition",
            category="multi_scale",
            description="分析号码的频率尺度转换 — 频率趋势一致的号码得分高",
            parameters={"scales": scales or [10, 30, 100, 300]},
        )
        self.scales = scales or [10, 30, 100, 300]

    def score_number(self, n: int, draws: Any) -> float:
        freqs = []
        for scale in self.scales:
            recent = draws[-min(scale, len(draws)):]
            count = sum(1 for d in recent
                       if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
            freqs.append(count / max(len(recent) * 6, 1))

        if len(freqs) < 3:
            return 0.5

        # 计算相邻尺度的变化率
        changes = [freqs[i + 1] - freqs[i] for i in range(len(freqs) - 1)]

        # 如果所有变化率同号（都上升或都下降），得分高
        if all(c > 0 for c in changes):
            return sum(changes) / len(changes) * 5  # 单调上升
        elif all(c < 0 for c in changes):
            return sum(abs(c) for c in changes) / len(changes) * 5  # 单调下降
        else:
            return 0.3  # 方向不一致


# ═══════════════════════════════════════════════════════════
# 新增原语类别12: 环境感知 (Environment-aware Primitives)
# ═══════════════════════════════════════════════════════════

class EnvironmentAware(Primitive):
    """
    环境感知原语

    核心假设: 号码的预测价值取决于"环境"——即近期开奖的整体特征。
    例如在和值高、奇偶比失衡的环境下，某些号码的表现会更好。

    计算方法: 对每个号码，计算它在不同环境条件下的表现，
    然后根据当前环境选择最合适的号码。
    """

    def __init__(self, lookback: int = 100):
        super().__init__(
            name="environment_aware",
            category="environment_aware",
            description="分析号码的环境适应性 — 在当前环境下表现最好的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < 20:
            return 0.5

        # 定义环境特征
        env_features = []
        for draw in recent_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            env_features.append({
                "sum": sum(reds),
                "odd_count": sum(1 for r in reds if r % 2 == 1),
                "max": max(reds),
                "min": min(reds),
            })

        # 当前环境（最近一期）
        current = env_features[0]

        # 找历史中环境相似的情况
        similar_hits = 0
        similar_total = 0
        for i in range(1, len(env_features)):
            prev = env_features[i]
            # 环境相似度
            sim = 1.0 - (abs(prev["sum"] - current["sum"]) / 100.0 +
                        abs(prev["odd_count"] - current["odd_count"]) / 6.0)
            if sim > 0.7:
                similar_total += 1
                if n in (draws[-(i + 1)].reds if hasattr(draws[-(i + 1)], 'reds')
                        else sorted(list(draws[-(i + 1)].red))):
                    similar_hits += 1

        if similar_total == 0:
            return 0.5
        return similar_hits / similar_total


class PhaseDetector(Primitive):
    """
    相位检测原语

    核心假设: 开奖过程像一个振荡系统，有"相位"概念。
    在某些相位（如"热相位"、"冷相位"、"过渡相位"），
    号码的表现模式不同。

    计算方法: 用和值序列的相位（通过Hilbert变换近似）
    检测当前所处的相位，然后选择在当前相位表现好的号码。
    """

    def __init__(self, lookback: int = 200):
        super().__init__(
            name="phase_detector",
            category="environment_aware",
            description="检测开奖系统的相位 — 在当前相位表现好的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < 30:
            return 0.5

        # 计算和值序列
        sums = [sum(d.reds if hasattr(d, 'reds') else sorted(list(d.red)))
                for d in recent_draws]

        # 简单相位检测：用和值的滚动均值和标准差
        window = 20
        rolling_mean = sum(sums[-window:]) / window
        rolling_std = math.sqrt(sum((s - rolling_mean) ** 2 for s in sums[-window:]) / window)

        # 当前和值偏离均值的程度 = 相位
        current_sum = sums[0]
        phase = (current_sum - rolling_mean) / max(rolling_std, 1)

        # 计算n在历史不同相位下的表现
        n_scores = []
        for i in range(10, len(sums) - 10, 5):
            window_sums = sums[max(0, i - 10):i + 10]
            wm = sum(window_sums) / len(window_sums)
            ws = math.sqrt(sum((s - wm) ** 2 for s in window_sums) / len(window_sums))
            p = (sums[i] - wm) / max(ws, 1)

            # 相位相近
            if abs(p - phase) < 0.5:
                draw = recent_draws[len(recent_draws) - i - 1]
                reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
                n_scores.append(1 if n in reds else 0)

        if not n_scores:
            return 0.5
        return sum(n_scores) / len(n_scores)


class RegimeSwitch(Primitive):
    """
    制度转换原语

    核心假设: 开奖过程在不同"制度"（regime）之间切换。
    例如"热号制度"（高频号集中出现）和"冷号制度"（冷门号集中出现）。
    检测当前制度并选择对应制度的最优号码。

    计算方法: 用和值的滚动标准差检测制度转换点，
    在制度稳定期选该制度的最优号码。
    """

    def __init__(self, lookback: int = 300, window: int = 30):
        super().__init__(
            name="regime_switch",
            category="environment_aware",
            description="检测开奖制度转换 — 在当前制度下最优的号码得分高",
            parameters={"lookback": lookback, "window": window},
        )
        self.lookback = lookback
        self.window = window

    def score_number(self, n: int, draws: Any) -> float:
        recent_draws = draws[-min(self.lookback, len(draws)):]
        if len(recent_draws) < 60:
            return 0.5

        # 计算制度特征（和值的滚动标准差）
        sums = [sum(d.reds if hasattr(d, 'reds') else sorted(list(d.red)))
                for d in recent_draws]

        regime_std = []
        for i in range(0, len(sums) - self.window, self.window // 2):
            window_sums = sums[i:i + self.window]
            mean_s = sum(window_sums) / len(window_sums)
            std_s = math.sqrt(sum((s - mean_s) ** 2 for s in window_sums) / len(window_sums))
            regime_std.append(std_s)

        if not regime_std:
            return 0.5

        # 当前制度（最近一期）
        current_regime = regime_std[-1]

        # 找历史中制度相似的时期
        similar_freqs = []
        for i, rs in enumerate(regime_std[:-1]):
            if abs(rs - current_regime) < 0.5:
                # 该时期的号码频率
                start = i * self.window // 2
                end = start + self.window
                freq = Counter()
                for d in recent_draws[max(0, len(recent_draws) - end):max(0, len(recent_draws) - start)]:
                    reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
                    for r in reds:
                        freq[r] += 1

                if freq:
                    total = sum(freq.values())
                    similar_freqs.append(freq.get(n, 0) / total)

        if not similar_freqs:
            return 0.5
        return sum(similar_freqs) / len(similar_freqs)

class PhysicalBiasDetector(Primitive):
    """
    物理偏差检测原语 — 贝叶斯估计版

    核心: 用Beta(k+1, N-k+1)后验均值估计每个号码的真实概率，
    不依赖卡方检验的二元判断。即使卡方不显著也能给出合理分布。
    """

    def __init__(self, lookback: int = None):
        super().__init__(
            name="physical_bias",
            category="statistical",
            description="贝叶斯估计号码频率偏差 — 给出每个号码的概率估计",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: Any) -> float:
        # 计算所有号码的出现频率
        freq = Counter()
        for draw in draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                freq[r] += 1

        total_draws = len(draws)
        total_reds = total_draws * 6  # 总红球数

        # 贝叶斯估计: Beta(k+1, N-k+1) 的后验均值
        k = freq.get(n, 0)  # n号出现的次数
        posterior_mean = (k + 1) / (total_reds + 2)

        # 理论均匀概率
        uniform_prob = 1.0 / 33.0

        # 偏差 = 估计概率 - 均匀概率
        deviation = posterior_mean - uniform_prob

        # 线性映射到 [0, 1]
        # 最大可能偏差约 +/- 0.09
        score = 0.5 + deviation * 10  # 放大10倍让区分度更好
        return max(0.0, min(1.0, score))


# ═══════════════════════════════════════════════════════════
# V3.2 新增原语 — 高信息量信号
# ═══════════════════════════════════════════════════════════

class MutualInformationPair(Primitive):
    """
    互信息配对原语

    核心假设: 当前原语 (CooccurrenceAffinity) 用的是超额共现 (observed - expected)，
    这是线性差异度量，对稀有模式不敏感。互信息 MI = log(P(ab|a)/P(b)) 能捕捉
    "在已知a的情况下b有多意外"——这才是预测价值所在。

    计算方法: 对每个号码n，计算它与近期开奖中6个号码的互信息总和。
    MI(n, m) = log[ P(n∧m) / (P(n)*P(m)) ] / log(max_freq_pairs)
    归一化到 [0, 1]。

    优势: MI 对强关联（即使低频）敏感，而共现频率只看到高频。
    """

    def __init__(self, lookback: int = 200, min_samples: int = 5):
        super().__init__(
            name="mutual_information_pair",
            category="information_theory",
            description="计算号码对的互信息 — 条件意外性高的配对得分高",
            parameters={"lookback": lookback, "min_samples": min_samples},
        )
        self.lookback = lookback
        self.min_samples = min_samples

    def score_number(self, n: int, draws: Any) -> float:
        recent = draws[-min(self.lookback, len(draws)):]
        if len(recent) < 30:
            return 0.5

        # 统计频率 — 对无序对只计一次
        freq = Counter()
        pair_freq = Counter()  # key=(a,b) where a<b, count occurrences together
        total = len(recent)

        for draw in recent:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for r in reds:
                freq[r] += 1
            # 无序对，a < b
            for i in range(len(reds)):
                for j in range(i + 1, len(reds)):
                    pair_freq[(reds[i], reds[j])] += 1

        p_n = freq.get(n, 0) / total
        if p_n < self.min_samples / total:
            return 0.3

        mi_sum = 0.0
        count = 0
        for m in range(1, 34):
            if m == n:
                continue
            p_m = freq.get(m, 0) / total
            if p_m < self.min_samples / total:
                continue

            # P(n and m) — 用无序对
            key = (min(n, m), max(n, m))
            p_nm = pair_freq.get(key, 0) / total

            # MI = log(P_nm / (p_n * p_m))
            if p_nm > 0 and p_n > 0 and p_m > 0:
                mi = math.log(p_nm / (p_n * p_m))
                if mi > 0:  # 只累加正互信息
                    mi_sum += mi
                    count += 1

        if count == 0:
            return 0.5

        # 归一化：除以最大可能的MI
        max_mi = math.log(total) if total > 1 else 1.0
        normalized_mi = mi_sum / (count * max_mi)

        # 映射到 [0, 1]
        return min(1.0, 0.3 + normalized_mi * 3.0)


class ResidualSignal(Primitive):
    """
    残差信号原语

    核心假设: 当前所有原语都在分析"绝对频率"或"相对趋势"。
    但真正携带信号的是"残差"——从均匀分布模型中减去后剩下的系统性偏差。

    计算方法:
    1. 建立基线模型：每个号码的理论出现概率 = 6/33，期望频率 = N*6/33
    2. 计算实际频率与期望频率的残差：r(n) = freq_observed(n) - expected(n)
    3. 关键创新：不只用残差的符号，还分析残差的**时间结构**
       - 如果残差从负转正且加速（二阶导>0），说明该号码正在"脱离随机"
       - 这种结构性偏离比静态频率偏差更有预测力

    信号来源: 不是"哪个号码热"，而是"哪个号码正在从冷变热的加速度"。
    """

    def __init__(self, lookback: int = 300, short_window: int = 30):
        super().__init__(
            name="residual_signal",
            category="information_theory",
            description="分析频率残差的时间结构 — 从冷变热的加速度号码得分高",
            parameters={"lookback": lookback, "short_window": short_window},
        )
        self.lookback = lookback
        self.short_window = short_window

    def score_number(self, n: int, draws: Any) -> float:
        recent = draws[-min(self.lookback, len(draws)):]
        if len(recent) < 60:
            return 0.5

        total = len(recent)
        expected_freq = total * 6 / 33  # 均匀模型的期望出现次数

        # 计算三个时间窗口的出现次数
        # 窗口1: 最远 (t-3w ~ t-2w)
        # 窗口2: 中间 (t-2w ~ t-w)
        # 窗口3: 最近 (t-w ~ t)
        w = self.short_window
        if total < w * 3:
            return 0.5

        counts = []
        for seg in range(3):
            start = total - (seg + 1) * w
            end = total - seg * w
            if start < 0:
                start = 0
            c = sum(1 for d in recent[start:end]
                    if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
            counts.append(c)

        # 残差 = 观测 - 期望（按窗口比例缩放）
        seg_expected = w * 6 / 33
        residuals = [c - seg_expected for c in counts]

        # 一阶差分（趋势）
        if len(residuals) >= 2:
            delta1 = residuals[-1] - residuals[-2]  # 近期变化
        else:
            delta1 = 0

        # 二阶差分（加速度）
        if len(residuals) >= 3:
            accel = residuals[-1] - 2 * residuals[-2] + residuals[-3]
        else:
            accel = delta1

        # 评分逻辑：
        # 残差为正且加速度为正 → 正在加速脱离随机 → 高分
        # 残差为负但加速度为正 → 正在回暖 → 中等分
        # 残差为正但加速度为负 → 过热回调风险 → 低分
        score = 0.5
        score += accel * 0.3   # 加速度权重最高
        score += delta1 * 0.2   # 趋势次之
        score += residuals[-1] * 0.1  # 当前残差最低

        # 归一化到 [0, 1]
        return max(0.0, min(1.0, score))


class ConditionalProbabilityMatrix(Primitive):
    """
    条件概率矩阵原语

    核心假设: 当前原语都是"单号码视角"——只看号码n自身的历史。
    但双色球是组合事件：P(n出现 | 完整的历史向量) ≠ P(n出现)。
    条件概率 P(n | 过去k期的全部6*2=12个号码) 包含远超单号码频率的信息。

    计算方法:
    1. 构建特征向量：过去k期共6*k个号码的one-hot编码 + 统计摘要
    2. 对每个号码n，估计 P(n appears next | recent_history)
    3. 使用朴素贝叶斯：P(n|h) ∝ P(h|n) * P(n)，其中h是近期历史特征

    特征设计（轻量级，避免过拟合）：
    - 过去3期各号码是否出现过（binary feature）
    - 过去3期的和值、奇偶比、跨度
    - 过去3期的区段分布（1-11, 12-22, 23-33）
    - 遗漏值（n距离上次出现多少期）

    用这些特征做加权投票，权重通过历史数据拟合。
    """

    def __init__(self, lookback: int = 200, history_depth: int = 5):
        super().__init__(
            name="conditional_probability_matrix",
            category="information_theory",
            description="基于条件概率矩阵 — P(n|完整历史向量) 直接建模",
            parameters={"lookback": lookback, "history_depth": history_depth},
        )
        self.lookback = lookback
        self.history_depth = history_depth

    def _extract_features(self, draws_slice, target_idx):
        """
        从 draws_slice[:target_idx] 提取特征向量。
        返回一个字典，描述 target_idx 这期的"环境"。
        """
        if target_idx < self.history_depth + 5:
            return None

        recent = draws_slice[target_idx - self.history_depth:target_idx]

        features = {}

        # 特征1: 过去每期各号码是否出现 (binary vector of length 33)
        appeared = set()
        for d in recent:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            appeared.update(reds)
        features['appeared_count'] = len(appeared) / 33.0

        # 特征2: 最近一期的6个号码
        last_reds = recent[0].reds if hasattr(recent[0], 'reds') else sorted(list(recent[0].red))
        features['last_reds'] = last_reds

        # 特征3: 过去history_depth期的统计摘要
        all_sums = []
        all_odd_counts = []
        for d in recent:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            all_sums.append(sum(reds))
            all_odd_counts.append(sum(1 for r in reds if r % 2 == 1))

        features['sum_mean'] = sum(all_sums) / len(all_sums)
        features['sum_std'] = (sum((s - features['sum_mean']) ** 2 for s in all_sums) / len(all_sums)) ** 0.5
        features['odd_mean'] = sum(all_odd_counts) / len(all_odd_counts)

        # 特征4: 号码n的遗漏值
        for d in recent:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            if 1 not in reds:  # placeholder, will be overridden per-n
                pass

        return features

    def score_number(self, n: int, draws: Any) -> float:
        recent = draws[-min(self.lookback, len(draws)):]
        if len(recent) < self.history_depth + 20:
            return 0.5

        # 方法：leave-one-out 交叉验证式估计
        # 对于每个可能的"训练点"i，用 draws[:i] 训练，看n是否在draws[i+1]中出现
        # 收集 (features_i, label_i=n_appears) 样本对
        # 然后用简单计数法估计 P(n appears | feature_pattern)

        # 简化版：直接计算条件频率
        # 特征：遗漏值 + 近期是否出现 + 和值区间 + 奇偶区间

        current_omission = 0
        for d in recent:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            if n not in reds:
                current_omission += 1
            else:
                break

        # 构建近期上下文
        last_draws = recent[:min(self.history_depth, len(recent))]
        last_reds_flat = []
        for d in last_draws:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            last_reds_flat.extend(reds)

        last_freq = Counter(last_reds_flat)
        n_in_last = last_freq.get(n, 0)

        # 和值
        sums = [sum(d.reds if hasattr(d, 'reds') else sorted(list(d.red))) for d in last_draws]
        current_sum = sums[0] if sums else 102

        # 条件频率表：(omission_bucket, appeared_in_last, sum_bucket) -> P(n appears next)
        # 桶化
        omi_bucket = min(current_omission // 5, 10)
        appeared_bucket = 1 if n_in_last > 0 else 0
        sum_bucket = int((current_sum - 60) / 20)  # 60-180 → 0-6

        # 在全量历史上统计这个条件下的出现率
        hist = draws  # full history
        cond_hits = 0
        cond_total = 0

        for i in range(self.history_depth, len(hist) - 1):
            # 检查i期的特征桶
            h_omission = 0
            for d in hist[i:i - min(self.history_depth, i):-1] if i >= self.history_depth else []:
                pass  # skip complex traversal

            # 简化：直接看过去history_depth期的特征
            window = hist[max(0, i - self.history_depth):i]
            if len(window) < 3:
                continue

            w_omission = 0
            w_n_count = 0
            w_sums = []
            for d in window:
                reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
                if n not in reds:
                    w_omission += 1
                else:
                    w_n_count += 1
                w_sums.append(sum(reds))

            if not w_sums:
                continue

            w_omi_b = min(w_omission // 5, 10)
            w_appeared_b = 1 if w_n_count > 0 else 0
            w_sum_b = int((sum(w_sums) / len(w_sums) - 60) / 20)

            if w_omi_b == omi_bucket and w_appeared_b == appeared_bucket and w_sum_b == sum_bucket:
                cond_total += 1
                next_reds = hist[i + 1].reds if hasattr(hist[i + 1], 'reds') else sorted(list(hist[i + 1].red))
                if n in next_reds:
                    cond_hits += 1

        if cond_total < 5:
            # 条件太稀疏，退化为无条件频率
            total_hits = sum(1 for d in hist if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
            return 0.3 + (total_hits / len(hist)) * 3

        cond_prob = cond_hits / cond_total

        # 映射到 [0, 1]，放大区分度
        # 理论先验 P = 6/33 ≈ 0.18
        deviation = cond_prob - 6 / 33
        score = 0.5 + deviation * 5
        return max(0.0, min(1.0, score))


# ═══════════════════════════════════════════════════════════
# 原语工厂 — 方便创建常用原语
# ═══════════════════════════════════════════════════════════

class PrimitiveFactory:
    """原语工厂 — 快速创建各类原语"""

    @staticmethod
    def temporal_echo(**kwargs) -> PeriodicEcho:
        return PeriodicEcho(**kwargs)

    @staticmethod
    def recency_gradient(**kwargs) -> RecencyGradient:
        return RecencyGradient(**kwargs)

    @staticmethod
    def seasonal_resonance(**kwargs) -> SeasonalResonance:
        return SeasonalResonance(**kwargs)

    @staticmethod
    def cooccurrence_affinity(**kwargs) -> CooccurrenceAffinity:
        return CooccurrenceAffinity(**kwargs)

    @staticmethod
    def mutual_exclusion(**kwargs) -> MutualExclusionScore:
        return MutualExclusionScore(**kwargs)

    @staticmethod
    def pair_orbit(**kwargs) -> PairOrbit:
        return PairOrbit(**kwargs)

    @staticmethod
    def binary_topology(**kwargs) -> BinaryTopology:
        return BinaryTopology(**kwargs)

    @staticmethod
    def digit_manifold(**kwargs) -> DigitManifold:
        return DigitManifold(**kwargs)

    @staticmethod
    def position_signature(**kwargs) -> PositionSignature:
        return PositionSignature(**kwargs)

    @staticmethod
    def spectral_power(**kwargs) -> SpectralPower:
        return SpectralPower(**kwargs)

    @staticmethod
    def wavelet_coherence(**kwargs) -> WaveletCoherence:
        return WaveletCoherence(**kwargs)

    @staticmethod
    def sphere_projection(**kwargs) -> SphereProjection:
        return SphereProjection(**kwargs)

    @staticmethod
    def distance_cluster(**kwargs) -> DistanceCluster:
        return DistanceCluster(**kwargs)

    @staticmethod
    def attractor_distance(**kwargs) -> AttractorDistance:
        return AttractorDistance(**kwargs)

    @staticmethod
    def lyapunov_signal(**kwargs) -> LyapunovSignal:
        return LyapunovSignal(**kwargs)

    # ─── 新增原语工厂方法 ───

    # 序列模式
    @staticmethod
    def sum_range_tracker(**kwargs) -> SumRangeTracker:
        return SumRangeTracker(**kwargs)

    @staticmethod
    def gap_pattern(**kwargs) -> GapPatternAnalyzer:
        return GapPatternAnalyzer(**kwargs)

    @staticmethod
    def trend_reversal(**kwargs) -> TrendReversalDetector:
        return TrendReversalDetector(**kwargs)

    # 组合特征
    @staticmethod
    def modulo_distribution(**kwargs) -> ModuloClassDistribution:
        return ModuloClassDistribution(**kwargs)

    @staticmethod
    def digit_pair_freq(**kwargs) -> DigitPairFrequency:
        return DigitPairFrequency(**kwargs)

    @staticmethod
    def adjacent_bias(**kwargs) -> AdjacentNumberBias:
        return AdjacentNumberBias(**kwargs)

    # 高阶统计
    @staticmethod
    def skewness_signal(**kwargs) -> SkewnessSignal:
        return SkewnessSignal(**kwargs)

    @staticmethod
    def kurtosis_signal(**kwargs) -> KurtosisSignal:
        return KurtosisSignal(**kwargs)

    @staticmethod
    def tail_risk(**kwargs) -> TailRiskSignal:
        return TailRiskSignal(**kwargs)

    # 跨期记忆
    @staticmethod
    def lag_correlation(**kwargs) -> LagCorrelation:
        return LagCorrelation(**kwargs)

    @staticmethod
    def periodic_gap(**kwargs) -> PeriodicGap:
        return PeriodicGap(**kwargs)

    @staticmethod
    def recurrence_window(**kwargs) -> RecurrenceWindow:
        return RecurrenceWindow(**kwargs)

    # 多尺度分析
    @staticmethod
    def multi_scale_frequency(**kwargs) -> MultiScaleFrequency:
        return MultiScaleFrequency(**kwargs)

    @staticmethod
    def scale_transition(**kwargs) -> ScaleTransition:
        return ScaleTransition(**kwargs)

    # 环境感知
    @staticmethod
    def environment_aware(**kwargs) -> EnvironmentAware:
        return EnvironmentAware(**kwargs)

    @staticmethod
    def phase_detector(**kwargs) -> PhaseDetector:
        return PhaseDetector(**kwargs)

    @staticmethod
    def regime_switch(**kwargs) -> RegimeSwitch:
        return RegimeSwitch(**kwargs)

    # ─── V3.2 新原语 ───

    @staticmethod
    def mutual_information(**kwargs) -> MutualInformationPair:
        return MutualInformationPair(**kwargs)

    @staticmethod
    def residual_signal(**kwargs) -> ResidualSignal:
        return ResidualSignal(**kwargs)

    @staticmethod
    def conditional_probability(**kwargs) -> ConditionalProbabilityMatrix:
        return ConditionalProbabilityMatrix(**kwargs)

    @staticmethod
    def create_all() -> List[Primitive]:
        """
        创建所有预定义原语的实例 — 完整版 (36个原语)。

        覆盖7大类别:
        - temporal (时序): PeriodicEcho, RecencyGradient, SeasonalResonance
        - relational (关系): CooccurrenceAffinity, MutualExclusionScore, PairOrbit
        - structural (结构): BinaryTopology, DigitManifold, PositionSignature
        - spectral (频谱): SpectralPower, WaveletCoherence
        - geometric (几何): SphereProjection, DistanceCluster
        - chaotic (混沌): AttractorDistance, LyapunovSignal
        - sequence_pattern (序列模式): SumRangeTracker, GapPatternAnalyzer, TrendReversalDetector
        - combinatorial (组合特征): ModuloClassDistribution, DigitPairFrequency, AdjacentNumberBias
        - higher_order (高阶统计): SkewnessSignal, KurtosisSignal, TailRiskSignal
        - cross_period_memory (跨期记忆): LagCorrelation, PeriodicGap, RecurrenceWindow
        - multi_scale (多尺度分析): MultiScaleFrequency, ScaleTransition
        - environment_aware (环境感知): EnvironmentAware, PhaseDetector, RegimeSwitch
        - statistical (统计): PhysicalBiasDetector
        - information_theory (信息论): MutualInformationPair, ResidualSignal, ConditionalProbabilityMatrix
        """
        return [
            # ═══ 时序类 (temporal) ═══
            PeriodicEcho(),
            RecencyGradient(),
            SeasonalResonance(),

            # ═══ 关系类 (relational) ═══
            CooccurrenceAffinity(),
            MutualExclusionScore(),
            PairOrbit(),

            # ═══ 结构类 (structural) ═══
            BinaryTopology(),
            DigitManifold(),
            PositionSignature(),

            # ═══ 频谱类 (spectral) ═══
            SpectralPower(),
            WaveletCoherence(),

            # ═══ 几何类 (geometric) ═══
            SphereProjection(),
            DistanceCluster(),

            # ═══ 混沌类 (chaotic) ═══
            AttractorDistance(),
            LyapunovSignal(),

            # ═══ 序列模式 (sequence_pattern) ═══
            SumRangeTracker(),
            GapPatternAnalyzer(),
            TrendReversalDetector(),

            # ═══ 组合特征 (combinatorial) ═══
            ModuloClassDistribution(),
            DigitPairFrequency(),
            AdjacentNumberBias(),

            # ═══ 高阶统计 (higher_order) ═══
            SkewnessSignal(),
            KurtosisSignal(),
            TailRiskSignal(),

            # ═══ 跨期记忆 (cross_period_memory) ═══
            LagCorrelation(),
            PeriodicGap(),
            RecurrenceWindow(),

            # ═══ 多尺度分析 (multi_scale) ═══
            MultiScaleFrequency(),
            ScaleTransition(),

            # ═══ 环境感知 (environment_aware) ═══
            EnvironmentAware(),
            PhaseDetector(),
            RegimeSwitch(),

            # ═══ 统计 (statistical) ═══
            PhysicalBiasDetector(),

            # ═══ 信息论 (information_theory) — V3.2新增 ═══
            MutualInformationPair(),
            ResidualSignal(),
            ConditionalProbabilityMatrix(),
        ]


# ═══════════════════════════════════════════════════════════
# 便捷入口
# ═══════════════════════════════════════════════════════════

# 预注册的常用原语实例 — 使用工厂创建，避免缓存旧版本
def get_default_primitives() -> List[Primitive]:
    """获取默认原语集合（每次都从工厂创建，确保最新版本）"""
    return PrimitiveFactory.create_all()
