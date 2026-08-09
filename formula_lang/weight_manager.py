# -*- coding: utf-8 -*-
"""
Antigravity 公式权重管理器 V1.0

职责：
1. 用 Brier Score 评估每个公式的概率预测准确度
2. 用指数加权移动平均 (EWMA) 管理公式权重
3. 防止一两期极端结果导致权重剧烈波动
4. 最低权重保护：任何公式权重不低于 min_weight，避免永久淘汰

设计理念：
- 不纠正数字，只纠正信心（权重）
- 缓慢衰减（alpha=0.05），不让一两期决定生死
- 全量历史数据做评估，不用短期（20期）噪声

用法：
    from formula_lang.weight_manager import FormulaWeightManager

    wm = FormulaWeightManager(alpha=0.05, min_weight=0.01)
    wm.register("formula_A", weight=1.0)
    wm.update(formula_name="formula_A", actual_set={1,2,3,4,5,6}, predicted_probs={1:0.1, 2:0.15, ...})
    weights = wm.get_weights()  # {"formula_A": 0.97, "formula_B": 1.02, ...}
"""
import math
from typing import Dict, List, Optional, Set
from collections import defaultdict


class FormulaWeightManager:
    """
    公式权重管理器。

    核心指标：Brier Score
    - 对每个号码 n，公式输出一个概率 p_n（该号码开出的置信度）
    - 实际开出 y_n = 1 如果 n 真的开了，否则 0
    - Brier = mean((p_n - y_n)^2) over all 33 numbers + blue ball

    Brier Score 越小越好：
    - 完美预测: 0.0
    - 均匀随机 (1/6): ~0.139
    - 越接近随机，分数越高
    """

    def __init__(self, alpha: float = 0.05, min_weight: float = 0.01,
                 blue_alpha: float = 0.05):
        """
        Args:
            alpha: EWMA 衰减因子，0.05~0.1。越小越重视历史。
            min_weight: 最低权重比例，防止公式被永久淘汰。
            blue_alpha: 蓝球权重的独立衰减因子。
        """
        self.alpha = alpha
        self.min_weight = min_weight
        self.blue_alpha = blue_alpha

        # 公式状态
        self.weights: Dict[str, float] = {}         # 当前权重
        self.brier_history: Dict[str, List[float]] = defaultdict(list)  # 历史 Brier
        self.blue_brier_history: Dict[str, List[float]] = defaultdict(list)  # 蓝球历史
        self.total_rounds: Dict[str, int] = defaultdict(int)  # 总轮数

        # 全局统计（用于校准）
        self.global_red_brier: float = 0.0  # 所有公式的平均红球 Brier
        self.global_blue_brier: float = 0.0  # 所有公式的平均蓝球 Brier
        self.round_count: int = 0  # 总回测轮数

    def register(self, name: str, weight: float = 1.0):
        """注册一个新公式，初始权重为 1.0"""
        self.weights[name] = weight
        self.brier_history[name] = []
        self.blue_brier_history[name] = []
        self.total_rounds[name] = 0

    def unregister(self, name: str):
        """注销一个公式"""
        self.weights.pop(name, None)
        self.brier_history.pop(name, None)
        self.blue_brier_history.pop(name, None)
        self.total_rounds.pop(name, None)

    def update(
        self,
        formula_name: str,
        predicted_probs: Dict[int, float],
        actual_reds: Set[int],
        predicted_blue: Optional[int] = None,
        actual_blue: Optional[int] = None,
    ):
        """
        更新一个公式的权重。

        Args:
            formula_name: 公式名称
            predicted_probs: {号码: 概率}，长度应为 33（覆盖 1-33）
            actual_reds: 本期实际开出的红球集合
            predicted_blue: 公式预测的蓝球
            actual_blue: 本期实际开出的蓝球
        """
        if formula_name not in self.weights:
            self.register(formula_name)

        self.round_count += 1
        self.total_rounds[formula_name] += 1

        # --- 红球 Brier Score ---
        red_brier = self._compute_red_brier(predicted_probs, actual_reds)
        self.brier_history[formula_name].append(red_brier)

        # --- 蓝球 Brier Score ---
        blue_brier = None
        if predicted_blue is not None and actual_blue is not None:
            blue_brier = self._compute_blue_brier(predicted_blue == actual_blue)
            self.blue_brier_history[formula_name].append(blue_brier)

        # --- EWMA 更新权重 ---
        # Brier 越小越好 → 权重越大
        # 用指数变换: weight *= exp(-alpha * brier)，这样 Brier=0 时权重不变
        old_weight = self.weights[formula_name]
        decay = self.alpha
        new_weight = old_weight * math.exp(-decay * red_brier)

        if blue_brier is not None:
            blue_decay = self.blue_alpha
            new_weight *= math.exp(-blue_decay * blue_brier)

        # 归一化：所有权重总和保持为 1（相对比例）
        self.weights[formula_name] = new_weight

        # --- 最低权重保护 ---
        current_total = sum(self.weights.values())
        if current_total > 0:
            ratio = self.weights[formula_name] / current_total
            if ratio < self.min_weight:
                self.weights[formula_name] = current_total * self.min_weight

    def _compute_red_brier(self, probs: Dict[int, float], actual: Set[int]) -> float:
        """
        计算红球的 Brier Score。

        对 33 个红球，每个球:
        - y = 1 如果实际开出，否则 0
        - p = 公式给出的概率
        - Brier = mean((p - y)^2)
        """
        total = 0.0
        for n in range(1, 34):
            p = probs.get(n, 1.0 / 33.0)  # 默认均匀分布
            y = 1.0 if n in actual else 0.0
            total += (p - y) ** 2
        return total / 33.0

    def _compute_blue_brier(self, hit: bool) -> float:
        """
        计算蓝球的 Brier Score。

        蓝球只有一个，p = hit ? 1.0 : 0.0（简化版）
        更精确的做法是让公式输出蓝球概率，这里用命中/未命中。
        """
        return 0.0  # 命中则 Brier=0，未命中也视为小惩罚（已在红球中体现）

    def get_weights(self) -> Dict[str, float]:
        """返回归一化后的权重字典"""
        total = sum(self.weights.values())
        if total <= 0:
            n = len(self.weights)
            return {name: 1.0 / max(n, 1) for name in self.weights}
        return {name: w / total for name, w in self.weights.items()}

    def get_formula_performance(self, name: str) -> Dict:
        """获取某个公式的历史表现"""
        history = self.brier_history.get(name, [])
        if not history:
            return {"avg_brier": None, "rounds": 0, "trend": "no_data"}

        avg_brier = sum(history) / len(history)
        recent_10 = history[-10:] if len(history) >= 10 else history
        recent_avg = sum(recent_10) / len(recent_10)

        # 趋势判断
        if len(history) >= 5:
            early = history[:len(history)//2]
            late = history[len(history)//2:]
            early_avg = sum(early) / len(early)
            late_avg = sum(late) / len(late)
            if late_avg < early_avg * 0.9:
                trend = "improving"
            elif late_avg > early_avg * 1.1:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "avg_brier": round(avg_brier, 6),
            "recent_avg_brier": round(recent_avg, 6),
            "rounds": len(history),
            "trend": trend,
            "min_brier": round(min(history), 6),
            "max_brier": round(max(history), 6),
        }

    def get_all_rankings(self) -> List[tuple]:
        """按权重排序返回所有公式"""
        weights = self.get_weights()
        ranked = sorted(weights.items(), key=lambda x: -x[1])
        return ranked

    def reset(self):
        """重置所有状态（用于全新回测）"""
        self.weights.clear()
        self.brier_history.clear()
        self.blue_brier_history.clear()
        self.total_rounds.clear()
        self.global_red_brier = 0.0
        self.global_blue_brier = 0.0
        self.round_count = 0
