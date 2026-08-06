#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
公式评估器 V2.0 — 多维度综合评估

改进:
1. 新增 NDCG (排序质量) — 不仅看命中几个，还看排得多靠前
2. 新增 夏普比率 — 收益/风险比
3. 新增 KL散度 — 衡量公式是否有"信息量"
4. 新增 滚动窗口 — 测试集扩大到50-100期
5. 新增 综合评分 — 多维度加权

核心: 一个公式不能只用"命中数"来判断好坏。
"""
import math
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from collections import Counter

_PROJECT_ROOT = Path(__file__).resolve().parent


class FormulaEvaluatorV2:
    """多维度公式评估器 V2.0"""

    def __init__(self, random_baseline: float = 1.09):
        self.random_baseline = random_baseline

    def evaluate_comprehensive(self, formula: Any, draws: Any,
                                n_windows: int = 10,
                                window_size: int = 500,
                                step: int = 50,
                                test_size: int = 50) -> Dict:
        """
        综合评估一个公式 — 多维度打分。

        Args:
            formula: 公式对象
            draws: 历史数据
            n_windows: 验证窗口数
            window_size: 训练窗口大小
            step: 窗口步进
            test_size: 每期测试的期数 (从10期扩大到50期)

        Returns:
            {
                'avg_hits': 平均命中数,
                'std_hits': 命中数标准差,
                'sharpe_ratio': 夏普比率 (收益/风险),
                'ndcg': NDCG排序质量得分,
                'kl_divergence': KL散度 (信息量),
                'hit_distribution': 每期命中数分布,
                'top_rank_pct': Top-6命中率,
                'mid_rank_pct': Mid-6命中率,
                'bottom_rank_pct': Bottom-6命中率,
                'composite_score': 综合评分,
                'beats_random': 是否优于随机,
                'per_round': 每轮详细数据,
            }
        """
        per_round = []
        ndcg_scores = []
        rank_distributions = []

        for w in range(n_windows):
            train_end = window_size + w * step
            test_start = train_end + 10
            test_end = test_start + test_size

            if test_end > len(draws):
                break

            try:
                pred_scores = formula.evaluate_for_all_numbers(draws[:train_end])
                sorted_nums = sorted(pred_scores.items(), key=lambda x: -x[1])

                # 1. 传统命中数
                hits = []
                for i in range(test_start, test_end, 10):
                    if i + 10 > len(draws):
                        break
                    pred_top6 = [n for n, _ in sorted_nums[:6]]
                    actual = draws[i:i + 10]
                    actual_hits = sum(len(set(pred_top6) & set(
                        d.reds if hasattr(d, 'reds') else sorted(list(d.red))
                    )) for d in actual) / 10
                    hits.append(actual_hits)

                # 2. NDCG — 排序质量
                ndcg = self._compute_ndcg(formula, draws, train_end, test_start, test_size)
                ndcg_scores.append(ndcg)

                # 3. 排名分布 — Top/Mid/Bottom
                rank_dist = self._compute_rank_distribution(formula, draws, train_end, test_start, test_size)
                rank_distributions.append(rank_dist)

                # 4. 记录每轮数据
                per_round.append({
                    'window': w,
                    'avg_hits': sum(hits) / len(hits) if hits else 0,
                    'std_hits': math.sqrt(sum((h - sum(hits)/len(hits))**2 for h in hits) / max(len(hits)-1, 1)) if len(hits) > 1 else 0,
                    'ndcg': ndcg,
                    'rank_top6': rank_dist['top6'],
                    'rank_mid6': rank_dist['mid6'],
                    'rank_bottom6': rank_dist['bottom6'],
                })

            except Exception:
                per_round.append({
                    'window': w, 'avg_hits': 0, 'std_hits': 0,
                    'ndcg': 0, 'rank_top6': 0, 'rank_mid6': 0, 'rank_bottom6': 0,
                })

        if not per_round:
            return self._empty_result()

        # 计算综合指标
        avg_hits = sum(r['avg_hits'] for r in per_round) / len(per_round)
        std_hits = math.sqrt(sum(r['std_hits']**2 for r in per_round) / len(per_round))
        sharpe = (avg_hits - self.random_baseline) / std_hits if std_hits > 0 else 0
        avg_ndcg = sum(r['ndcg'] for r in per_round) / len(per_round)

        # 排名分布平均
        avg_top6 = sum(r['rank_top6'] for r in per_round) / len(per_round)
        avg_mid6 = sum(r['rank_mid6'] for r in per_round) / len(per_round)
        avg_bottom6 = sum(r['rank_bottom6'] for r in per_round) / len(per_round)

        # KL散度 — 公式打分分布 vs 均匀分布
        kl_div = self._compute_kl_overall(formula, draws, window_size)

        # 综合评分 = 加权组合 (V2.1优化版)
        # 根据v2_evaluation_results分析:
        # - NDCG区分度低(0.53-0.54),降权至15%
        # - avg_hits是核心指标,提权至35%
        # - Sharpe比率反映稳定性,提权至25%
        # - Top6命中率反映实际预测能力,提权至20%
        # - KL散度反映信息量,保持10%
        composite = (
            0.35 * min(avg_hits / self.random_baseline, 1.5) +   # 命中数权重35%(原30%)
            0.15 * avg_ndcg +                                     # NDCG权重15%(原25%,区分度太低)
            0.25 * min(max(sharpe, 0) / 3.0, 1.0) +               # 夏普比率权重25%(原20%)
            0.20 * avg_top6 +                                     # Top6命中率权重20%(原无独立项)
            0.10 * (1.0 - kl_div)                                 # KL散度权重10%
        )

        # t检验
        se = std_hits / math.sqrt(len(per_round)) if std_hits > 0 else 1
        t_stat = (avg_hits - self.random_baseline) / se if se > 0 else 0
        p_value = self._t_to_pvalue(t_stat, len(per_round))

        return {
            'avg_hits': round(avg_hits, 4),
            'std_hits': round(std_hits, 4),
            'sharpe_ratio': round(sharpe, 4),
            'ndcg': round(avg_ndcg, 4),
            'kl_divergence': round(kl_div, 4),
            'rank_top6': round(avg_top6, 4),
            'rank_mid6': round(avg_mid6, 4),
            'rank_bottom6': round(avg_bottom6, 4),
            'composite_score': round(composite, 4),
            'p_value': round(p_value, 4),
            'beats_random': avg_hits > self.random_baseline,
            'stable': round(avg_hits - std_hits, 4),
            'rounds': len(per_round),
            'per_round': per_round,
        }

    def _compute_ndcg(self, formula: Any, draws: Any,
                       train_end: int, test_start: int, test_size: int) -> float:
        """
        改进版NDCG — 使用多尺度折扣 + 位置敏感加权

        改进点:
        1. 使用IDCF (Ideal Discounted Cumulative Frequency) 而非 binary relevance
        2. 对Top-3和Top-6给予不同的折扣权重
        3. 考虑号码出现的实际期数作为增益
        """
        pred_scores = formula.evaluate_for_all_numbers(draws[:train_end])
        sorted_nums = sorted(pred_scores.items(), key=lambda x: -x[1])

        dcgs = []
        for i in range(test_start, test_start + test_size, 10):
            if i + 10 > len(draws):
                break
            actual = draws[i:i + 10]

            for d in actual:
                actual_set = set(d.reds if hasattr(d, 'reds') else sorted(list(d.red)))

                # --- 方法1: 标准NDCG (保留用于对比) ---
                dcg_standard = 0.0
                ideal_dcg = 0.0
                for rank, (num, score) in enumerate(sorted_nums):
                    if num in actual_set:
                        dcg_standard += 1.0 / math.log2(rank + 2)
                ideal_dcg = sum(1.0 / math.log2(i + 2) for i in range(min(6, len(sorted_nums))))

                # --- 方法2: 增强NDCG — 使用分数差值作为增益 ---
                # 实际号码的平均分数 vs 非实际号码的平均分数
                actual_scores = [pred_scores.get(num, 0) for num in actual_set]
                non_actual_scores = [pred_scores.get(num, 0) for num in range(1, 34) if num not in actual_set]

                if actual_scores and non_actual_scores:
                    mean_actual = sum(actual_scores) / len(actual_scores)
                    mean_non_actual = sum(non_actual_scores) / len(non_actual_scores)

                    # 区分度 = 实际号码平均分数 - 非实际号码平均分数
                    # 正值说明公式确实把实际号码排得更靠前
                    discrimination = (mean_actual - mean_non_actual) / (max(abs(s) for s in pred_scores.values()) + 1e-10)

                    # 用sigmoid将区分度映射到[0, 1]
                    sig_discrim = 1.0 / (1.0 + math.exp(-10 * discrimination))
                else:
                    sig_discrim = 0.5

                # --- 方法3: Top-k命中率加权 ---
                top3_hits = sum(1 for num in actual_set if num in [n for n, _ in sorted_nums[:3]])
                top6_hits = sum(1 for num in actual_set if num in [n for n, _ in sorted_nums[:6]])
                top10_hits = sum(1 for num in actual_set if num in [n for n, _ in sorted_nums[:10]])

                # 加权混合得分
                blended = (
                    0.3 * dcg_standard / max(ideal_dcg, 1e-10) +   # 标准NDCG占30%
                    0.4 * sig_discrim +                               # 分数区分度占40%
                    0.15 * (top6_hits / 6.0) +                        # Top-6命中率占15%
                    0.15 * (top3_hits / 6.0 * 1.5)                   # Top-3命中率占15%(加权1.5x)
                )
                dcgs.append(min(blended, 1.0))

        return sum(dcgs) / len(dcgs) if dcgs else 0

    def _compute_rank_distribution(self, formula: Any, draws: Any,
                                     train_end: int, test_start: int, test_size: int) -> Dict:
        """计算Top-6/Mid-6/Bottom-6命中率"""
        pred_scores = formula.evaluate_for_all_numbers(draws[:train_end])
        sorted_nums = sorted(pred_scores.items(), key=lambda x: -x[1])

        top6 = [n for n, _ in sorted_nums[:6]]
        mid6 = [n for n, _ in sorted_nums[13:19]]
        bottom6 = [n for n, _ in sorted_nums[27:]]

        hit_top = 0
        hit_mid = 0
        hit_bottom = 0
        periods = 0

        for i in range(test_start, test_start + test_size, 10):
            if i + 10 > len(draws):
                break
            for d in draws[i:i + 10]:
                actual = set(d.reds if hasattr(d, 'reds') else sorted(list(d.red)))
                hit_top += len(set(top6) & actual)
                hit_mid += len(set(mid6) & actual)
                hit_bottom += len(set(bottom6) & actual)
                periods += 1

        return {
            'top6': hit_top / max(periods, 1),
            'mid6': hit_mid / max(periods, 1),
            'bottom6': hit_bottom / max(periods, 1),
        }

    def _compute_kl_overall(self, formula: Any, draws: Any,
                             window_size: int) -> float:
        """计算KL散度 — 公式打分分布 vs 均匀分布"""
        # 用最近window_size期计算平均KL
        samples = draws[-min(window_size, len(draws)):]
        all_scores = {}
        for n in range(1, 34):
            scores = [p.score_number(n, samples) for p in formula.primitives]
            all_scores[n] = sum(scores) / len(scores)

        total = sum(all_scores.values())
        if total <= 0:
            return 0

        p = {n: all_scores[n] / total for n in all_scores}
        q = {n: 1.0 / 33 for n in range(1, 34)}

        # KL(P || Q)
        kl = 0
        for n in p:
            if p[n] > 0 and q[n] > 0:
                kl += p[n] * math.log2(p[n] / q[n])

        return kl

    def _t_to_pvalue(self, t: float, df: int) -> float:
        x = abs(t) / math.sqrt(2)
        try:
            erf_x = self._erf(x)
            p_one_tail = 0.5 * (1 - erf_x)
            return min(1.0, 2 * p_one_tail)
        except:
            return 1.0

    @staticmethod
    def _erf(x: float) -> float:
        sign = 1 if x >= 0 else -1
        x = abs(x)
        a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
        p = 0.3275911
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        return sign * y

    def _empty_result(self) -> Dict:
        return {
            'avg_hits': 0, 'std_hits': 1, 'sharpe_ratio': 0,
            'ndcg': 0, 'kl_divergence': 0,
            'rank_top6': 0, 'rank_mid6': 0, 'rank_bottom6': 0,
            'composite_score': 0, 'p_value': 1.0, 'rounds': 0,
            'beats_random': False, 'stable': -1, 'per_round': [],
        }

    def evaluate_batch(self, formulas: List[Any], draws: Any, **kwargs) -> Dict[str, Dict]:
        """批量评估"""
        results = {}
        for f in formulas:
            name = getattr(f, 'name', str(f))
            results[name] = self.evaluate_comprehensive(f, draws, **kwargs)
        return results
