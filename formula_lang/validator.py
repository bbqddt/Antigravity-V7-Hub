# -*- coding: utf-8 -*-
"""
Antigravity 公式验证系统 V3.1 — 基于规律发现的验证体系

核心理念:
- 公式 = 对号码规律的假设
- 历史开奖数据 = 规律的"土壤"
- 验证 = 公式从历史数据中提取的规律是否真实存在
- 不是"预测下一期开什么"，而是"这个规律在历史上是否成立"

验证5个维度:
1. 规律发现 — 公式从数据中提取了什么规律（号码偏好、结构特征）
2. 规律验证 — 该规律在独立数据上是否仍然成立（训练/测试隔离）
3. 规律强度 — 该规律的统计显著性（相关性、区分度）
4. 规律稳定性 — 该规律在不同时间窗口是否一致（抗过拟合）
5. 规律进化 — 该规律变异后是否能变得更强（可进化性）

用法:
    from formula_lang.validator import FormulaValidator

    validator = FormulaValidator()
    result = validator.validate(formula, draws)
    print(result['verdict'])  # VALIDATED / PROMISING / MARGINAL / INVALID
"""
import math
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from collections import Counter

_PROJECT_ROOT = Path(__file__).resolve().parent


class FormulaValidator:
    """
    公式验证器 V3.1

    核心思想: 公式打分 → 提取规律 → 独立验证 → 综合评分
    """

    def __init__(self):
        self.validation_history = []

    def validate(self, formula: Any, draws: List[Any],
                 window_sizes: List[int] = None) -> Dict:
        """
        全面验证一个公式 — 5个维度

        Args:
            formula: 公式对象（有 score_number(n, draws) 或 rank_top_6(draws) 方法）
            draws: 历史开奖数据
            window_sizes: 不同时间窗口大小

        Returns:
            验证结果字典
        """
        if window_sizes is None:
            window_sizes = [50, 100, 200, 500]

        start = time.time()

        # 维度1: 规律发现
        patterns = self._discover_patterns(formula, draws)

        # 维度2: 规律验证 (独立数据集)
        validation = self._validate_patterns(formula, draws, patterns)

        # 维度3: 规律强度
        strength = self._measure_strength(formula, draws, patterns)

        # 维度4: 规律稳定性 (多窗口)
        stability = self._measure_stability(formula, draws, window_sizes)

        # 维度5: 规律进化潜力
        evolution = self._measure_evolution_potential(formula, draws, patterns)

        elapsed = time.time() - start

        # 综合评分
        overall = self._compute_overall_score(patterns, validation, strength, stability, evolution)
        verdict = self._make_verdict(overall, patterns, validation, strength, stability, evolution)

        result = {
            "formula_name": getattr(formula, "name", "unknown"),
            "category": getattr(formula, "category", getattr(formula, "primitives", ["unknown"])[0].category if hasattr(formula, "primitives") else "unknown"),
            "validated_at": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "dimensions": {
                "discovery": patterns,
                "validation": validation,
                "strength": strength,
                "stability": stability,
                "evolution": evolution,
            },
            "overall_score": overall,
            "verdict": verdict,
        }

        self.validation_history.append(result)
        return result

    def _normalize_scores(self, scores: Dict[int, float]) -> Dict[int, float]:
        """
        标准化打分到 0-1 范围，消除量纲差异。
        这是关键修复 — 不同原语的打分量纲完全不同。
        """
        vals = list(scores.values())
        if not vals:
            return scores

        min_v = min(vals)
        max_v = max(vals)

        if max_v == min_v:
            # 所有分数相同，返回均匀分布
            return {n: 0.5 for n in scores}

        return {n: (scores[n] - min_v) / (max_v - min_v) for n in scores}

    def _get_formula_scores(self, formula: Any, draws: List[Any]) -> Dict[int, float]:
        """
        获取公式对所有33个号码的打分。
        支持两种接口: score_number(n, draws) 或 rank_top_6(draws)
        """
        scores = {}

        # 优先使用 score_number 方法
        if hasattr(formula, 'score_number'):
            for n in range(1, 34):
                try:
                    scores[n] = formula.score_number(n, draws)
                except:
                    scores[n] = 0.0
        # 否则使用 evaluate_for_all_numbers
        elif hasattr(formula, 'evaluate_for_all_numbers'):
            try:
                scores = formula.evaluate_for_all_numbers(draws)
            except:
                scores = {n: 0.0 for n in range(1, 34)}
        # 否则使用 rank_top_6（只给Top-6打分，其余为0）
        elif hasattr(formula, 'rank_top_6'):
            try:
                top6 = formula.rank_top_6(draws)
                for n in range(1, 34):
                    if n in top6:
                        scores[n] = 1.0
                    else:
                        scores[n] = 0.0
            except:
                scores = {n: 0.0 for n in range(1, 34)}
        else:
            scores = {n: 0.0 for n in range(1, 34)}

        # 标准化
        return self._normalize_scores(scores)

    # ─── 维度1: 规律发现 ────────────────────────────────────────

    def _discover_patterns(self, formula: Any, draws: List[Any]) -> Dict:
        """
        维度1: 规律发现

        公式从历史数据中提取了什么规律？
        - 号码偏好：哪些号码得分高
        - 区分度：公式能否有效区分号码
        - 注意力集中度：公式是有主见还是均匀分布
        """
        raw_scores = self._get_formula_scores(formula, draws)

        # 分析分数分布
        vals = list(raw_scores.values())
        mean_v = sum(vals) / 34
        std_v = math.sqrt(sum((v - mean_v) ** 2 for v in vals) / 34)

        # Top-6偏好号码
        ranked = sorted(raw_scores.items(), key=lambda x: -x[1])
        top6 = [n for n, _ in ranked[:6]]
        top6_scores = {n: round(s, 4) for n, s in ranked[:6]}

        # Bottom-6排斥号码
        bottom6 = [n for n, _ in ranked[-6:]]
        bottom6_scores = {n: round(s, 4) for n, s in ranked[-6:]}

        # 注意力集中度 (熵)
        total = sum(abs(v) for v in vals)
        if total > 0:
            probs = [abs(v) / total for v in vals]
            entropy = -sum(p * math.log(p + 1e-10) for p in probs if p > 0)
            max_entropy = math.log(34)
            concentration = 1.0 - entropy / max_entropy if max_entropy > 0 else 0
        else:
            concentration = 0

        # 区分度 (变异系数)
        cv = std_v / max(abs(mean_v), 1e-10)

        return {
            "top6_preferred": top6,
            "top6_scores": top6_scores,
            "bottom6_avoided": bottom6,
            "bottom6_scores": bottom6_scores,
            "mean_score": round(mean_v, 4),
            "std_score": round(std_v, 4),
            "concentration": round(concentration, 4),  # 0=均匀, 1=极度集中
            "distinctiveness": round(cv, 4),  # 变异系数，越大区分度越高
            "num_unique_scores": len(set(round(v, 4) for v in vals)),
        }

    # ─── 维度2: 规律验证 ────────────────────────────────────────

    def _validate_patterns(self, formula: Any, draws: List[Any],
                           discovered: Dict) -> Dict:
        """
        维度2: 规律验证

        将数据分为训练集(前70%)和验证集(后30%)。
        在训练集上用公式发现规律，在验证集上检查规律是否成立。
        """
        n = len(draws)
        train_end = int(n * 0.7)

        train_data = draws[:train_end]
        val_data = draws[train_end:]

        if not val_data:
            return {"error": "no_validation_data"}

        # 在训练集上获取公式打分
        train_scores = self._get_formula_scores(formula, train_data)
        ranked_train = sorted(train_scores.items(), key=lambda x: -x[1])
        train_top6 = [n for n, _ in ranked_train[:6]]

        # 在验证集上检查: 这些号码是否"重要"？
        # 方法: 检查验证集中，train_top6中的号码是否频繁出现
        val_hits = 0
        val_total = 0
        for draw in val_data:
            actual_reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            val_total += 1
            val_hits += len(set(train_top6) & set(actual_reds))

        # 理论随机期望: 6个号码在33选6中，每期期望命中 = 6*6/33 ≈ 1.09
        expected_random = 1.09 * val_total
        observed = val_hits

        # 验证比率: >1 表示公式发现的规律在验证集上有效
        validation_ratio = observed / max(expected_random, 0.1)

        # 公式Top-6号码在验证集中的出现频率
        appearance_freq = {}
        for n in range(1, 34):
            count = sum(1 for d in val_data
                       if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
            appearance_freq[n] = count / val_total

        top6_appearance = {n: round(appearance_freq.get(n, 0), 4) for n in train_top6}

        return {
            "train_size": train_end,
            "val_size": val_total,
            "train_top6": train_top6,
            "validation_hits": observed,
            "expected_random_hits": round(expected_random, 2),
            "validation_ratio": round(validation_ratio, 4),
            "top6_appearance_freq": top6_appearance,
            "pattern_valid": validation_ratio > 0.8,  # 至少80%随机水平
        }

    # ─── 维度3: 规律强度 ────────────────────────────────────────

    def _measure_strength(self, formula: Any, draws: List[Any],
                          discovered: Dict) -> Dict:
        """
        维度3: 规律强度

        - 区分度: 公式能否有效区分重要/不重要号码
        - 一致性: 公式打分与历史开奖频率的相关性
        - 置信度: 规律的可信程度
        """
        scores = self._get_formula_scores(formula, draws)

        # 计算号码的历史出现频率
        recent_n = min(200, len(draws))
        recent = draws[-recent_n:]
        hist_freq = {}
        for n in range(1, 34):
            count = sum(1 for d in recent
                       if n in (d.reds if hasattr(d, 'reds') else sorted(list(d.red))))
            hist_freq[n] = count / (recent_n * 6)  # 归一化到0-1

        # 公式打分 vs 历史频率的相关性
        score_vals = [scores.get(n, 0) for n in range(1, 34)]
        freq_vals = [hist_freq.get(n, 0) for n in range(1, 34)]

        correlation = self._pearson_correlation(score_vals, freq_vals)

        # 公式Top-6号码在近期开奖中的平均出现频率
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        formula_top6 = [n for n, _ in ranked[:6]]
        avg_freq = sum(hist_freq.get(n, 0) for n in formula_top6) / 6

        # 区分度: 分数标准差越大，公式越有主见
        std_score = math.sqrt(sum((s - sum(score_vals)/34)**2 for s in score_vals) / 34)

        return {
            "score_freq_correlation": round(correlation, 4),
            "formula_top6": formula_top6,
            "top6_avg_frequency": round(avg_freq, 4),
            "score_std": round(std_score, 4),
            "strength_indicator": "STRONG" if abs(correlation) > 0.2 and std_score > 0.1 else
                                  "MODERATE" if abs(correlation) > 0.05 else
                                  "WEAK",
        }

    # ─── 维度4: 规律稳定性 ────────────────────────────────────────

    def _measure_stability(self, formula: Any, draws: List[Any],
                           window_sizes: List[int]) -> Dict:
        """
        维度4: 规律稳定性

        公式在不同时间窗口发现的规律是否一致？
        如果规律只在特定窗口成立，说明可能是过拟合。
        """
        window_results = []

        for ws in window_sizes:
            if ws >= len(draws):
                continue

            data = draws[-ws:]
            scores = self._get_formula_scores(formula, data)
            ranked = sorted(scores.items(), key=lambda x: -x[1])
            top6 = [n for n, _ in ranked[:6]]

            window_results.append({
                "window_size": ws,
                "top6": top6,
                "score_std": round(math.sqrt(sum((s - sum(scores.values())/34)**2 for s in scores.values()) / 34), 4),
            })

        # 计算窗口间的一致性 (Jaccard相似度)
        similarities = []
        for i in range(len(window_results) - 1):
            set_a = set(window_results[i]["top6"])
            set_b = set(window_results[i + 1]["top6"])
            if set_a or set_b:
                jaccard = len(set_a & set_b) / len(set_a | set_b)
                similarities.append(jaccard)

        avg_similarity = sum(similarities) / max(len(similarities), 1)

        return {
            "windows_tested": len(window_results),
            "results": window_results,
            "avg_top6_similarity": round(avg_similarity, 4),
            "stability_indicator": "STABLE" if avg_similarity > 0.5 else
                                   "MODERATE" if avg_similarity > 0.2 else
                                   "UNSTABLE",
        }

    # ─── 维度5: 规律进化潜力 ────────────────────────────────────────

    def _measure_evolution_potential(self, formula: Any, draws: List[Any],
                                     discovered: Dict) -> Dict:
        """
        维度5: 规律进化潜力

        公式是否还有改进空间？
        """
        from formula_lang.mutator import PrimitiveMutator
        mutator = PrimitiveMutator()

        # 获取原始打分
        original_scores = self._get_formula_scores(formula, draws)
        original_std = math.sqrt(sum((s - sum(original_scores.values())/34)**2 for s in original_scores.values()) / 34)

        improved = 0
        unchanged = 0
        worsened = 0

        for i in range(10):
            try:
                mutated = mutator.mutate(formula, draws, generation=i)
                mutated_scores = self._get_formula_scores(mutated, draws)
                mutated_std = math.sqrt(sum((s - sum(mutated_scores.values())/34)**2 for s in mutated_scores.values()) / 34)

                if mutated_std > original_std * 1.05:
                    improved += 1
                elif mutated_std < original_std * 0.95:
                    worsened += 1
                else:
                    unchanged += 1
            except:
                worsened += 1

        return {
            "original_std": round(original_std, 4),
            "improved": improved,
            "unchanged": unchanged,
            "worsened": worsened,
            "evolution_potential": "HIGH" if improved > 5 else
                                   "MEDIUM" if improved > 2 else
                                   "LOW",
        }

    # ─── 综合评分 ─────────────────────────────────────────────

    def _compute_overall_score(self, discovery, validation, strength,
                                stability, evolution) -> float:
        """
        综合评分 (0-100)

        权重分配:
        - 规律发现: 15% (注意力集中度 + 区分度)
        - 规律验证: 30% (最重要 — 规律是否真实存在)
        - 规律强度: 25% (相关性 + 置信度)
        - 规律稳定性: 20% (抗过拟合能力)
        - 进化潜力: 10% (可进化性)
        """
        # 规律发现 (0-15)
        discovery_score = (discovery.get("concentration", 0) * 8 +
                          discovery.get("distinctiveness", 0) * 7)

        # 规律验证 (0-30) — 最重要
        val_ratio = validation.get("validation_ratio", 0)
        validation_score = min(30, max(0, val_ratio * 15))

        # 规律强度 (0-25)
        corr = abs(strength.get("score_freq_correlation", 0))
        strength_score = min(25, corr * 50)

        # 规律稳定性 (0-20)
        stability_score = stability.get("avg_top6_similarity", 0) * 20

        # 进化潜力 (0-10)
        ev_total = evolution.get("improved", 0) + evolution.get("unchanged", 0) + evolution.get("worsened", 0)
        evolution_score = (evolution.get("improved", 0) / max(ev_total, 1)) * 10

        return round(discovery_score + validation_score + strength_score +
                     stability_score + evolution_score, 2)

    def _make_verdict(self, score, discovery, validation, strength,
                      stability, evolution) -> str:
        """做出判定"""
        if score >= 70:
            indicator = "VALIDATED"
            desc = "公式发现的规律真实且强大"
        elif score >= 45:
            indicator = "PROMISING"
            desc = "公式有潜力，规律部分成立"
        elif score >= 25:
            indicator = "MARGINAL"
            desc = "公式规律较弱，需进一步变异或淘汰"
        else:
            indicator = "INVALID"
            desc = "公式未发现有效规律，建议淘汰"

        return f"{indicator} (score={score}) — {desc}"

    # ─── 工具方法 ─────────────────────────────────────────────

    @staticmethod
    def _pearson_correlation(x: List[float], y: List[float]) -> float:
        """皮尔逊相关系数"""
        n = len(x)
        if n < 2:
            return 0
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

        if std_x == 0 or std_y == 0:
            return 0

        return cov / (std_x * std_y)


def validate_formula(formula, draws, output_path: str = None) -> Dict:
    """便捷函数: 验证一个公式"""
    validator = FormulaValidator()
    result = validator.validate(formula, draws)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return result
