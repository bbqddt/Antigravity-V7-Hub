# -*- coding: utf-8 -*-
"""
Antigravity 公式语法 V1.0

核心理念:
- 公式不是随机拼接原子函数，而是用语义化组合算子
- 组合算子有明确的数学含义: resonance(共振), cascade(级联), phase_align(相位对齐)
- 每个组合算子都产生一个"公式"，可以对33个号码打分

用法:
    from formula_lang.primitive import PeriodicEcho, RecencyGradient
    from formula_lang.grammar import FormulaGrammar

    p1 = PeriodicEcho()
    p2 = RecencyGradient()

    # 共振组合: 两个原语的分数相乘（强调两者都高的号码）
    f = FormulaGrammar.resonance(p1, p2, weight1=0.6, weight2=0.4)

    # 级联组合: p1筛选 → p2 refinement
    f2 = FormulaGrammar.cascade(p1, p2, threshold=0.3)

    # 相位对齐: 考虑两个原语的"相位偏移"
    f3 = FormulaGrammar.phase_align(p1, p2, offset=0.5)
"""
import math
from typing import List, Dict, Tuple, Optional, Any
from formula_lang.primitive import Primitive


# ═══════════════════════════════════════════════════════════
# 公式 — 原语的组合
# ═══════════════════════════════════════════════════════════

class Formula:
    """
    公式 — 由原语通过组合算子构成的可打分实体。

    每个公式有:
    - name: 公式名称
    - operators: 组合算子列表
    - primitives: 参与的原语列表
    - parameters: 公式参数
    """

    def __init__(self, name: str, primitives: List[Primitive],
                 operators: List[str], parameters: Optional[Dict] = None):
        self.name = name
        self.primitives = primitives
        self.operators = operators
        self.parameters = parameters or {}
        self.score_cache: Optional[Dict[int, float]] = None

    def evaluate_for_all_numbers(self, draws: Any) -> Dict[int, float]:
        """对33个号码打分"""
        if self.score_cache is not None:
            return self.score_cache

        scores = {}
        for n in range(1, 34):
            scores[n] = self._score_number(n, draws)

        self.score_cache = scores
        return scores

    def _score_number(self, n: int, draws: Any) -> float:
        """对单个号码打分"""
        # 计算每个原语的分数
        raw_scores = [p.score_number(n, draws) for p in self.primitives]

        # 应用组合算子
        result = raw_scores[0] if raw_scores else 0.0

        for i, op in enumerate(self.operators):
            if i + 1 >= len(raw_scores):
                break
            next_score = raw_scores[i + 1]

            if op == "resonance":
                # 共振: 加权乘积 — 两个原语都高的号码得分极高
                w1 = self.parameters.get(f"weight_{i}", 0.5)
                w2 = 1.0 - w1
                result = result ** w1 * max(next_score, 0.01) ** w2

            elif op == "cascade":
                # 级联: 如果原语i分数高于阈值，用原语i+1 refinement
                threshold = self.parameters.get("cascade_threshold", 0.3)
                if result > threshold:
                    result = 0.7 * result + 0.3 * next_score
                # 否则保持原样

            elif op == "phase_align":
                # 相位对齐: 加权平均，考虑相位偏移
                phase = self.parameters.get("phase_offset", 0.5)
                result = phase * result + (1 - phase) * next_score

            elif op == "sum":
                result = result + next_score

            elif op == "max":
                result = max(result, next_score)

            elif op == "min":
                result = min(result, next_score)

        # V3.0: 不再 clamp 到 0-1，保留原始分数的区分度
        # clamp 会抹杀不同公式之间的细微差异
        return result

    def rank_top_6(self, draws: Any) -> List[int]:
        """返回Top-6号码"""
        scores = self.evaluate_for_all_numbers(draws)
        sorted_nums = sorted(scores.items(), key=lambda x: -x[1])
        return [n for n, _ in sorted_nums[:6]]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "primitives": [p.uuid for p in self.primitives],
            "operators": self.operators,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, d: Dict, primitives: Dict[str, Primitive]) -> "Formula":
        prim_list = [primitives[pid] for pid in d["primitives"] if pid in primitives]
        return cls(d["name"], prim_list, d["operators"], d.get("parameters", {}))


# ═══════════════════════════════════════════════════════════
# 公式语法 — 组合算子
# ═══════════════════════════════════════════════════════════

class FormulaGrammar:
    """
    公式语法 — 提供语义化的组合算子。

    每个组合算子接受原语列表，返回一个Formula对象。
    """

    @staticmethod
    def resonance(primitives: List[Primitive],
                  weights: Optional[List[float]] = None,
                  name: str = "resonance") -> Formula:
        """
        共振组合: 加权乘积

        原理: 如果一个号码在多个原语上都得分高，那么它的综合得分
        应该远高于只在单个原语上得分高的号码。

        例如: PeriodicEcho(周期性强) × RecencyGradient(近期趋势强)
        = 既有周期性又有近期趋势的号码

        Args:
            primitives: 参与共振的原语列表
            weights: 各原语的权重（可选，默认等权）
            name: 公式名称
        """
        if weights is None:
            weights = [1.0 / len(primitives)] * len(primitives)

        params = {f"weight_{i}": weights[i] for i in range(len(primitives) - 1)}
        return Formula(
            name=f"{name}_resonance",
            primitives=primitives,
            operators=["resonance"] * (len(primitives) - 1),
            parameters=params,
        )

    @staticmethod
    def cascade(primitives: List[Primitive],
                thresholds: Optional[List[float]] = None,
                name: str = "cascade") -> Formula:
        """
        级联组合: 筛选 → 精炼

        原理: 第一个原语做粗筛，第二个原语做精炼，以此类推。
        适合"漏斗式"筛选。

        例如: BinaryTopology(筛选二进制特征匹配的)
             → CooccurrenceAffinity(在筛选结果中找共现强的)
             → PeriodicEcho(再筛选有周期性的)

        Args:
            primitives: 参与级联的原语列表（按优先级排序）
            thresholds: 各级的阈值（可选）
            name: 公式名称
        """
        if thresholds is None:
            thresholds = [0.3] * (len(primitives) - 1)

        params = {f"cascade_threshold_{i}": thresholds[i] for i in range(len(thresholds))}
        params["cascade_threshold"] = thresholds[0] if thresholds else 0.3

        return Formula(
            name=f"{name}_cascade",
            primitives=primitives,
            operators=["cascade"] * (len(primitives) - 1),
            parameters=params,
        )

    @staticmethod
    def phase_align(primitives: List[Primitive],
                    offsets: Optional[List[float]] = None,
                    name: str = "phase_align") -> Formula:
        """
        相位对齐组合: 加权平均

        原理: 不同原语可能有不同的"相位"（偏好不同的号码集合）。
        相位对齐就是把它们对齐到同一个参考系中，然后加权平均。

        例如: SpectralPower(频域视角) 和 SphereProjection(几何视角)
        的相位对齐 = 综合考虑频域和几何结构的号码

        Args:
            primitives: 参与相位对齐的原语列表
            offsets: 各原语的相位偏移（0-1，默认0.5）
            name: 公式名称
        """
        if offsets is None:
            offsets = [0.5] * (len(primitives) - 1)

        params = {f"phase_offset_{i}": offsets[i] for i in range(len(offsets))}
        params["phase_offset"] = offsets[0] if offsets else 0.5

        return Formula(
            name=f"{name}_phasealign",
            primitives=primitives,
            operators=["phase_align"] * (len(primitives) - 1),
            parameters=params,
        )

    @staticmethod
    def weighted_sum(primitives: List[Primitive],
                     weights: Optional[List[float]] = None,
                     name: str = "weighted_sum") -> Formula:
        """
        加权和组合: 线性加权

        最简单的组合方式，适合快速原型。

        Args:
            primitives: 参与组合的原语列表
            weights: 权重（如果不提供，自动归一化）
            name: 公式名称
        """
        if weights is None:
            weights = [1.0] * len(primitives)
        total = sum(weights)
        weights = [w / total for w in weights]

        params = {f"weight_{i}": weights[i] for i in range(len(weights))}
        return Formula(
            name=name,
            primitives=primitives,
            operators=["sum"] * (len(primitives) - 1),
            parameters=params,
        )

    @staticmethod
    def ensemble(formulas: List[Formula],
                 weights: Optional[List[float]] = None,
                 name: str = "ensemble") -> Formula:
        """
        公式集成: 多个公式的加权平均

        原理: 每个公式代表一种"世界观"，集成就是投票。

        Args:
            formulas: 参与集成的公式列表
            weights: 各公式的权重
            name: 集成名称
        """
        # 展开所有原语
        all_primitives = []
        for f in formulas:
            all_primitives.extend(f.primitives)
        all_primitives = list(set(all_primitives))  # 去重

        if weights is None:
            weights = [1.0 / len(formulas)] * len(formulas)

        # 创建一个"超级公式"
        return Formula(
            name=name,
            primitives=all_primitives,
            operators=[],  # 集成不需要组合算子
            parameters={"formula_weights": dict(zip([f.name for f in formulas], weights))},
        )
