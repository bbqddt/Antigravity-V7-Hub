# -*- coding: utf-8 -*-
"""
Antigravity 公式语言 — 公式评估器 V2.0 (修复版)

修复的问题:
- V1.0 将命中数归一化为比例 (0-1)，导致 random_baseline=1.09 永远无法超过
- V2.0 直接使用绝对命中数 (0-6)，与 walkforward_backtest_v2.py 体系一致
- 增加独立测试集验证机制，防止跨代数据泄露
- 增加公式存活/淘汰决策支持

核心理念:
- 每个公式都必须通过 walk-forward 交叉验证
- 指标: 绝对命中数 (0-6) vs 随机基线 1.09
- 评估结果直接用于公式的存活/淘汰决策
- 独立测试集保证验证的公正性

用法:
    from formula_lang.evaluator import FormulaEvaluator

    evaluator = FormulaEvaluator()
    result = evaluator.evaluate(formula, draws, n_windows=10, window_size=500, step=50)
    # result = {"avg_hits": 2.3, "std": 0.5, "p_value": 0.03, ...}
"""
import math
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from collections import Counter

_PROJECT_ROOT = Path(__file__).resolve().parent


class FormulaEvaluator:
    """公式评估器 V2.0 — walk-forward 交叉验证 (绝对命中数体系)"""

    # 双色球理论随机基线: 每期6个号码，33选6，期望命中 = 6 * 6/33 ≈ 1.09
    # 默认测试窗口10期，所以基线 = 1.09 * 10 = 10.9
    RANDOM_BASELINE_PER_ROUND = 1.09

    def __init__(self, random_baseline_per_round: float = None, test_window: int = 10):
        """
        Args:
            random_baseline_per_round: 每轮随机期望命中数 = 1.09 * test_window
            test_window: 测试窗口大小（默认10期）
        """
        self.test_window = test_window
        self.random_baseline = (random_baseline_per_round or 1.09) * test_window

    def evaluate(self, formula: Any, draws: Any,
                 n_windows: int = 10, window_size: int = 500,
                 step: int = 50) -> Dict:
        """
        评估一个公式的准确率。

        使用前向滚动窗口：
        - 训练集: draws[:train_end] — 公式在此窗口上"学习"
        - 测试集: draws[test_start:test_end] — 公式在此窗口上"考试"
        - 两者严格隔离，间隔10期

        Args:
            formula: 公式对象（有 rank_top_6(draws) 方法）
            draws: 历史开奖数据
            n_windows: 验证窗口数
            window_size: 初始训练窗口大小
            step: 窗口步进

        Returns:
            {
                "avg_hits": 平均绝对命中数 (0-6),
                "std": 标准差,
                "max_hits": 最大命中数,
                "min_hits": 最小命中数,
                "p_value": t检验p值,
                "rounds": 验证轮数,
                "beats_random": 是否优于随机基线,
                "stable": 稳定性评分 (avg - std),
                "per_round": [每轮绝对命中数列表],
                "formula_name": 公式名称,
            }
        """
        per_round_hits = []

        for w in range(n_windows):
            train_end = window_size + w * step
            test_start = train_end + 10  # 间隔10期确保隔离
            test_end = test_start + 10

            if test_end > len(draws):
                break

            try:
                # 用训练集预测
                pred_top6 = formula.rank_top_6(draws[:train_end])

                # 在测试集上验证 — 计算绝对命中数
                actual_hits = 0
                for draw in draws[test_start:test_end]:
                    actual_reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
                    actual_hits += len(set(pred_top6) & set(actual_reds))

                per_round_hits.append(actual_hits)
            except Exception:
                per_round_hits.append(0)

        if not per_round_hits:
            return self._empty_result(formula)

        avg = sum(per_round_hits) / len(per_round_hits)
        std = math.sqrt(sum((h - avg) ** 2 for h in per_round_hits) / max(len(per_round_hits) - 1, 1))
        max_h = max(per_round_hits)
        min_h = min(per_round_hits)

        # t检验: H0 = 公式效果 = 随机基线 (1.09)
        se = std / math.sqrt(len(per_round_hits)) if std > 0 else 1
        t_stat = (avg - self.random_baseline) / se if se > 0 else 0
        p_value = self._t_to_pvalue(t_stat, len(per_round_hits))

        return {
            "avg_hits": round(avg, 4),
            "std": round(std, 4),
            "max_hits": max_h,
            "min_hits": min_h,
            "p_value": round(p_value, 4),
            "t_stat": round(t_stat, 4),
            "rounds": len(per_round_hits),
            "beats_random": avg > self.random_baseline,
            "stable": round(avg - std, 4),
            "per_round": per_round_hits,
            "formula_name": getattr(formula, "name", "unknown"),
        }

    def evaluate_with_holdout(self, formula: Any, draws: Any,
                               train_ratio: float = 0.7,
                               n_windows: int = 10) -> Dict:
        """
        带独立测试集验证的评估。

        将数据分为训练集(70%)和独立测试集(30%)，
        在训练集上做walk-forward，在独立测试集上验证泛化能力。
        """
        n_train = int(len(draws) * train_ratio)
        train_data = draws[:n_train]
        test_data = draws[n_train:]

        # 训练集评估
        train_result = self.evaluate(formula, train_data, n_windows=n_windows)

        # 独立测试集验证
        test_hits = []
        for draw in test_data:
            actual_reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            pred_top6 = formula.rank_top_6(train_data)
            test_hits.append(len(set(pred_top6) & set(actual_reds)))

        test_avg = sum(test_hits) / max(len(test_hits), 1)

        train_result["holdout_test_avg"] = round(test_avg, 4)
        train_result["holdout_test_rounds"] = len(test_hits)
        train_result["generalization_gap"] = round(train_result["avg_hits"] - test_avg, 4)
        train_result["overfitting_risk"] = "HIGH" if (train_result["avg_hits"] - test_avg) > 0.5 else \
                                            "MEDIUM" if (train_result["avg_hits"] - test_avg) > 0.2 else \
                                            "LOW"

        return train_result

    def _empty_result(self, formula: Any) -> Dict:
        return {
            "avg_hits": 0, "std": 1, "max_hits": 0, "min_hits": 0,
            "p_value": 1.0, "t_stat": 0, "rounds": 0,
            "beats_random": False, "stable": -1,
            "per_round": [],
            "formula_name": getattr(formula, "name", "unknown"),
        }

    def evaluate_batch(self, formulas: List[Any], draws: Any,
                       **kwargs) -> Dict[str, Dict]:
        """批量评估多个公式"""
        results = {}
        for f in formulas:
            name = getattr(f, 'name', str(f))
            result = self.evaluate(f, draws, **kwargs)
            results[name] = result
        return results

    def select_survivors(self, results: Dict[str, Dict],
                         min_beats_random: int = 3,
                         min_stable: float = 0.0) -> List[str]:
        """
        存活/淘汰决策。

        公式存活条件:
        1. beats_random >= min_beats_random (至少N轮优于随机)
        2. stable >= min_stable (稳定得分非负)

        Args:
            results: evaluate_batch 返回的结果字典
            min_beats_random: 最少优于随机基线的轮数
            min_stable: 最低稳定得分

        Returns:
            存活公式名称列表
        """
        survivors = []
        eliminated = []

        for name, r in results.items():
            beats_count = sum(1 for h in r.get("per_round", []) if h > self.random_baseline)
            stable = r.get("stable", -1)

            if beats_count >= min_beats_random and stable >= min_stable:
                survivors.append(name)
            else:
                eliminated.append(name)

        return {
            "survivors": survivors,
            "eliminated": eliminated,
            "survival_rate": round(len(survivors) / max(len(results), 1), 4),
        }

    def _t_to_pvalue(self, t: float, df: int) -> float:
        """简化t检验p值计算（正态近似）"""
        x = abs(t) / math.sqrt(2)
        try:
            erf_x = self._erf(x)
            p_one_tail = 0.5 * (1 - erf_x)
            return min(1.0, 2 * p_one_tail)
        except:
            return 1.0

    @staticmethod
    def _erf(x: float) -> float:
        """误差函数近似 (Abramowitz and Stegun)"""
        sign = 1 if x >= 0 else -1
        x = abs(x)
        a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
        p = 0.3275911
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        return sign * y


def evaluate_formula_against_draws(formula, draws, n_rounds=30, seed=42) -> Dict:
    """便捷函数: 用一个公式在历史数据上回测"""
    evaluator = FormulaEvaluator()
    return evaluator.evaluate(formula, draws, n_windows=n_rounds, window_size=300, step=30)
