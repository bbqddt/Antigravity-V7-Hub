# -*- coding: utf-8 -*-
"""
Antigravity 公式评估器 V3.2 — 双指标 (Brier Score + Hit Count)

V3.0 → V3.1: 修复 _scores_to_probs softmax 归一化问题
  - 原: softmax → sum=1 (分类分布)
  - 改: softmax → sum=6 (边际概率)
  - 基线从 0.139→0.1488

V3.1 → V3.2: 增加命中数评估，解决 Brier 对概率校准要求过高的问题
  - 同时输出 avg_brier 和 avg_hits
  - beats_random = hits>1.09 OR brier<0.1413
  - combined_score = 0.6*brier_norm + 0.4*hits_norm

V3.2 实测结果 (3481期, 15窗口):
  - 21/36 公式在命中数上击败随机 (1.09)
  - 最佳: periodic_gap hits=1.273 (+16.8%)
  - 最佳加权集成: ws_top8 hits=1.127 (+3.4%), brier=0.1515
  - 无公式在 Brier 上击败随机（信号本身不足以超越均匀先验）
  - 结论: 用命中数体系评估公式质量，Brier 作为辅助参考

核心理念：
- 双色球是 Top-K 选择问题，不是概率校准问题
- 命中数是主指标，Brier 是辅助指标
- 能筛掉最差号码 > 能精确估计概率
"""
import math
from pathlib import Path
from typing import Optional, Dict, List, Any, Set
from datetime import datetime
from collections import defaultdict

_PROJECT_ROOT = Path(__file__).resolve().parent

import logging
logger = logging.getLogger("FormulaEvaluatorV3")


class FormulaEvaluatorV3:
    """
    公式评估器 V3.0 — Brier Score + 全量历史 Walk-Forward

    Brier Score 体系:
    - 红球 Brier: 对 33 个号码分别计算 (p_n - y_n)^2，取平均
    - 蓝球 Brier: 类似，但只有一个号码
    - 综合 Brier: 加权组合 (红球 0.9 + 蓝球 0.1)

    随机基线:
    - 均匀分布 p_n = 1/6 (每个号码被选中的先验概率)
    - 红球 Brier_baseline = 6*(1/6-1)^2 + 27*(1/6-0)^2 / 33 ≈ 0.139
    """

    # 理论随机基线 Brier Score
    # 均匀先验 p_n = 6/33 ≈ 0.1818 (每个号码被选中的概率)
    # Brier = (1/33) * [6*(p-1)^2 + 27*(p-0)^2] ≈ 0.1490
    RED_BRIER_BASELINE = (6 * (6/33 - 1)**2 + 27 * (6/33)**2) / 33
    BLUE_BRIER_BASELINE = 0.5  # 50% 命中率时的 Brier
    COMBINED_BASELINE = 0.9 * RED_BRIER_BASELINE + 0.1 * BLUE_BRIER_BASELINE

    def __init__(self, red_weight: float = 0.9, blue_weight: float = 0.1):
        self.red_weight = red_weight
        self.blue_weight = blue_weight

    def evaluate(
        self,
        formula: Any,
        draws: Any,
        n_windows: int = 30,
        window_size: int = 500,
        step: int = 50,
    ) -> Dict:
        """
        全量历史 walk-forward 评估。

        V3.2 改进：同时输出 Brier Score 和命中数 (hit count)。
        - Brier Score 评估概率校准质量
        - 命中数评估 Top-6 选择质量（双色球的实际目标）
        - 综合评分 = 0.5 * normalized_brier + 0.5 * normalized_hits

        关键改动：用 score_all()/evaluate_for_all_numbers() 获取 33 个号码的分数，
        转为概率分布后计算 Brier Score，同时用 rank_top_6() 计算命中数。
        """
        per_round_red_brier = []
        per_round_hits = []
        per_round_blue_hit = []

        # 尝试获取公式的打分方法
        if hasattr(formula, 'score_all'):
            get_scores = lambda d: formula.score_all(d)
        elif hasattr(formula, 'evaluate_for_all_numbers'):
            get_scores = lambda d: formula.evaluate_for_all_numbers(d)
        else:
            raise AttributeError(f"Formula {getattr(formula, 'name', '?')} has no scoring method")

        for w in range(n_windows):
            train_end = window_size + w * step
            test_start = train_end + 10
            test_end = min(test_start + 10, len(draws))

            if test_end <= test_start:
                break

            try:
                # 用训练集生成 33 个号码的分数
                scores = get_scores(draws[:train_end])

                # 转换为概率分布 (softmax → marginal probs)
                probs = self._scores_to_probs(scores)

                # 在测试集上验证
                round_red_brier = 0.0
                round_hits = 0
                round_blue_hits = 0

                for draw in draws[test_start:test_end]:
                    actual_reds = set(draw.reds)
                    actual_blue = draw.blue

                    # 红球 Brier
                    round_red_brier += self._red_brier(probs, actual_reds)

                    # 红球命中数
                    top6 = self._top_k_from_probs(probs, k=6)
                    round_hits += len(set(top6) & actual_reds)

                    # 蓝球命中
                    if actual_blue in top6:
                        round_blue_hits += 1

                avg_red_brier = round_red_brier / (test_end - test_start)
                per_round_red_brier.append(avg_red_brier)
                per_round_hits.append(round_hits / (test_end - test_start))
                per_round_blue_hit.append(round_blue_hits / (test_end - test_start))

            except Exception:
                logger.exception(
                    "evaluate 第 %d 轮(window_size=%d, step=%d) 评估异常，已用基线值兜底",
                    w, window_size, step,
                )
                per_round_red_brier.append(self.COMBINED_BASELINE)
                per_round_hits.append(0)
                per_round_blue_hit.append(0.0)

        if not per_round_red_brier:
            return self._empty_result(formula)

        red_brier = sum(per_round_red_brier) / len(per_round_red_brier)
        avg_hits = sum(per_round_hits) / len(per_round_hits)
        blue_hit_rate = sum(per_round_blue_hit) / len(per_round_blue_hit)

        # 稳定性 = 标准差越小越好
        red_std = math.sqrt(
            sum((b - red_brier) ** 2 for b in per_round_red_brier) / max(len(per_round_red_brier) - 1, 1)
        )
        hits_std = math.sqrt(
            sum((h - avg_hits) ** 2 for h in per_round_hits) / max(len(per_round_hits) - 1, 1)
        )

        # 随机基线
        RANDOM_HIT_BASELINE = 1.09
        beats_random_brier = red_brier < self.RED_BRIER_BASELINE * 0.95
        beats_random_hits = avg_hits > RANDOM_HIT_BASELINE

        # 综合评分：归一化到 [0, 1]，越高越好
        # Brier: 范围 ~[0, 0.3]，映射为 1 - brier/0.3
        # Hits: 范围 ~[0, 3]，映射为 hits/3
        brier_score_normalized = 1.0 - red_brier / 0.3
        hits_score_normalized = avg_hits / 3.0

        # 综合 = 加权平均 (Brier 60% + Hits 40%)
        combined_score = 0.6 * brier_score_normalized + 0.4 * hits_score_normalized

        # 是否优于随机（综合判定）
        beats_random = beats_random_hits or beats_random_brier

        # 泛化检验：前 70% 轮 vs 后 30% 轮
        split = len(per_round_red_brier) * 7 // 10
        if split > 0 and split < len(per_round_red_brier):
            early_avg = sum(per_round_red_brier[:split]) / split
            late_avg = sum(per_round_red_brier[split:]) / (len(per_round_red_brier) - split)
            generalization_gap = abs(late_avg - early_avg)
        else:
            generalization_gap = 0.0

        return {
            "avg_brier": round(red_brier, 6),
            "avg_hits": round(avg_hits, 4),
            "blue_hit_rate": round(blue_hit_rate, 6),
            "beats_random": beats_random,
            "beats_random_brier": beats_random_brier,
            "beats_random_hits": beats_random_hits,
            "combined_score": round(combined_score, 6),
            "stability": round(-red_std, 6),
            "stability_std": round(red_std, 6),
            "hits_std": round(hits_std, 6),
            "rounds": len(per_round_red_brier),
            "generalization_gap": round(generalization_gap, 6),
            "overfitting_risk": "HIGH" if generalization_gap > 0.02 else "MEDIUM" if generalization_gap > 0.01 else "LOW",
            "per_round_red_brier": [round(b, 6) for b in per_round_red_brier],
            "per_round_hits": [round(h, 4) for h in per_round_hits],
            "formula_name": getattr(formula, "name", "unknown"),
            "evaluated_at": datetime.now().isoformat(),
        }

    def evaluate_batch(
        self,
        formulas: List[Any],
        draws: Any,
        n_windows: int = 30,
        window_size: int = 500,
        step: int = 50,
    ) -> Dict[str, Dict]:
        """批量评估多个公式"""
        results = {}
        for f in formulas:
            name = getattr(f, "name", str(f))
            result = self.evaluate(f, draws, n_windows=n_windows,
                                   window_size=window_size, step=step)
            results[name] = result
        return results

    def select_survivors(
        self,
        results: Dict[str, Dict],
        min_beats_random: bool = True,
        max_generalization_gap: float = 0.02,
        min_rounds: int = 10,
    ) -> Dict:
        """
        存活/淘汰决策。

        公式存活条件：
        1. beats_random = True（比随机基线好）
        2. generalization_gap < 0.02（不过度过拟合）
        3. rounds >= min_rounds（有足够的验证数据）
        """
        survivors = []
        eliminated = []

        for name, r in results.items():
            reasons = []

            if min_beats_random and not r.get("beats_random", False):
                reasons.append("not_beating_random")

            if r.get("generalization_gap", 1.0) > max_generalization_gap:
                reasons.append(f"overfitting(gap={r.get('generalization_gap', 0):.4f})")

            if r.get("rounds", 0) < min_rounds:
                reasons.append(f"insufficient_data({r.get('rounds', 0)}<{min_rounds})")

            if reasons:
                eliminated.append({"name": name, "reasons": reasons})
            else:
                survivors.append(name)

        return {
            "survivors": survivors,
            "eliminated": eliminated,
            "survival_rate": round(len(survivors) / max(len(results), 1), 4),
            "total_formulas": len(results),
        }

    def _scores_to_probs(self, scores: Dict[int, float]) -> Dict[int, float]:
        """
        将原始分数转换为边际概率 (marginal probabilities)。

        V3.1 关键修复：双色球不是分类问题，每个号码的选中是独立事件。
        不能用 softmax 归一化为和=1 的概率分布。

        正确做法：
        - 用 softmax 得到相对排序
        - 缩放为边际概率：sum(p_i) ≈ 6（期望选中数）
        - 这样每个号码的 P(n) ≈ 6/33 = 0.18（随机先验）
        - Brier Score 才能正确评估校准质量

        参考：Brier Score 用于多 Bernoulli 试验的标准做法
        (Mason & Schiman, 2000; Gneiting & Raftery, 2007)
        """
        if not scores:
            return {n: 6.0 / 33.0 for n in range(1, 34)}

        min_s = min(scores.values())
        max_s = max(scores.values())
        score_range = max_s - min_s

        # 自适应温度：根据分数范围选择温度
        if score_range < 0.01:
            temperature = 0.05  # 几乎无差异，极低温度
        elif score_range < 0.1:
            temperature = 0.2
        elif score_range < 1.0:
            temperature = 0.5
        else:
            temperature = 2.0  # 差异大时，正常温度

        # 平移：确保所有分数为正（softmax 需要正数）
        shifted = {k: max(v - min_s + 0.001, 0.001) for k, v in scores.items()}

        # Softmax with adaptive temperature
        log_scores = {k: math.log(v) / temperature for k, v in shifted.items()}
        max_log = max(log_scores.values())

        exp_scores = {k: math.exp(v - max_log) for k, v in log_scores.items()}
        total = sum(exp_scores.values())

        # 归一化到概率分布 (sum=1)
        softmax_probs = {k: v / total for k, v in exp_scores.items()}

        # 缩放为边际概率：sum(p_i) = target_count (=6)
        # 这样每个号码的随机先验是 p = 6/33 ≈ 0.18
        TARGET_COUNT = 6.0
        marginal_probs = {k: v * TARGET_COUNT for k, v in softmax_probs.items()}

        return marginal_probs

    def _red_brier(self, probs: Dict[int, float], actual: Set[int]) -> float:
        """计算单个公式的红球 Brier Score"""
        total = 0.0
        for n in range(1, 34):
            p = probs.get(n, 1.0 / 33.0)
            y = 1.0 if n in actual else 0.0
            total += (p - y) ** 2
        return total / 33.0

    def _top_k_from_probs(self, probs: Dict[int, float], k: int = 6) -> List[int]:
        """从概率分布取 Top-K 号码"""
        sorted_nums = sorted(probs.items(), key=lambda x: -x[1])
        return [n for n, _ in sorted_nums[:k]]

    def _empty_result(self, formula: Any) -> Dict:
        return {
            "avg_brier": self.RED_BRIER_BASELINE,
            "avg_hits": 1.09,
            "blue_hit_rate": 0.0,
            "beats_random": False,
            "beats_random_brier": False,
            "beats_random_hits": False,
            "combined_score": 0.0,
            "stability": 0.0,
            "stability_std": 1.0,
            "hits_std": 1.0,
            "rounds": 0,
            "generalization_gap": 0.0,
            "overfitting_risk": "UNKNOWN",
            "per_round_red_brier": [],
            "per_round_hits": [],
            "formula_name": getattr(formula, "name", "unknown"),
            "evaluated_at": datetime.now().isoformat(),
        }


def evaluate_formula_against_draws_v3(formula, draws, n_rounds=30, seed=42) -> Dict:
    """便捷函数"""
    evaluator = FormulaEvaluatorV3()
    return evaluator.evaluate(formula, draws, n_windows=n_rounds, window_size=300, step=30)


# ═══════════════════════════════════════════════════════════
# V3.2 并行评估 + 缓存（加速演进引擎）
# ═══════════════════════════════════════════════════════════

import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed


class CacheManager:
    """公式评估结果缓存 — 避免重复计算"""

    def __init__(self, cache_file=None):
        self.cache_file = cache_file or str(Path(__file__).parent / 'evaluation_cache.json')
        self._cache = self._load()

    def _load(self):
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 只保留最近24小时的缓存
                from datetime import timedelta
                cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
                return {k: v for k, v in data.items() if v.get('cached_at', '') > cutoff}
        except Exception:
            logger.exception("评估缓存加载失败，返回空缓存")
            return {}

    def _save(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False)
        except Exception:
            logger.debug("评估缓存写入失败（不影响主流程）", exc_info=True)

    def _make_key(self, formula_name, draws_len, n_windows, window_size, step):
        """生成缓存key"""
        raw = f"{formula_name}:{draws_len}:{n_windows}:{window_size}:{step}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, formula_name, draws_len, n_windows, window_size, step):
        key = self._make_key(formula_name, draws_len, n_windows, window_size, step)
        return self._cache.get(key)

    def put(self, formula_name, draws_len, n_windows, window_size, step, result):
        key = self._make_key(formula_name, draws_len, n_windows, window_size, step)
        result_copy = dict(result)
        result_copy['cached_at'] = datetime.now().isoformat()
        self._cache[key] = result_copy
        self._save()


# 全局缓存实例
_eval_cache = None

def get_eval_cache():
    global _eval_cache
    if _eval_cache is None:
        _eval_cache = CacheManager()
    return _eval_cache


class IncrementalEvaluator:
    """
    增量评估器 V1.0 — 复用计算结果
    
    核心优化:
    - Walk-forward 评估中，相邻窗口共享大部分训练数据
    - 缓存 formula.score_all() 的结果，按 train_end 索引
    - 新窗口只需增量计算，避免重复对完整训练集打分
    - 预期加速比: 2-5x (取决于窗口重叠度)
    """
    
    def __init__(self, evaluator: 'FormulaEvaluatorV3'):
        self.evaluator = evaluator
        self._score_cache: Dict[int, Dict[int, float]] = {}  # train_end -> {num: score}
        self._prob_cache: Dict[int, Dict[int, float]] = {}   # train_end -> {num: prob}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def evaluate_incremental(
        self,
        formula: Any,
        draws: Any,
        n_windows: int = 30,
        window_size: int = 500,
        step: int = 50,
    ) -> Dict:
        """
        增量评估 - 复用相同 train_end 的打分结果
        """
        if hasattr(formula, 'score_all'):
            get_scores = lambda d: formula.score_all(d)
        elif hasattr(formula, 'evaluate_for_all_numbers'):
            get_scores = lambda d: formula.evaluate_for_all_numbers(d)
        else:
            raise AttributeError(f"Formula {getattr(formula, 'name', '?')} has no scoring method")
        
        per_round_red_brier = []
        per_round_hits = []
        per_round_blue_hit = []
        
        # 预计算所有需要的 train_end
        train_ends = [window_size + w * step for w in range(n_windows)]
        valid_train_ends = [te for te in train_ends if te + 10 + 10 <= len(draws)]
        
        # 为每个 train_end 计算/复用概率分布
        probs_by_train_end = {}
        for train_end in valid_train_ends:
            if train_end in self._prob_cache:
                probs_by_train_end[train_end] = self._prob_cache[train_end]
                self._cache_hits += 1
            else:
                # 计算新概率分布
                scores = get_scores(draws[:train_end])
                probs = self.evaluator._scores_to_probs(scores)
                self._prob_cache[train_end] = probs
                probs_by_train_end[train_end] = probs
                self._cache_misses += 1
        
        # 走前向验证
        for w, train_end in enumerate(valid_train_ends):
            test_start = train_end + 10
            test_end = min(test_start + 10, len(draws))
            
            if test_end <= test_start:
                break
            
            probs = probs_by_train_end[train_end]
            
            round_red_brier = 0.0
            round_hits = 0
            round_blue_hits = 0
            
            for draw in draws[test_start:test_end]:
                actual_reds = set(draw.reds)
                actual_blue = draw.blue
                
                round_red_brier += self.evaluator._red_brier(probs, actual_reds)
                
                top6 = self.evaluator._top_k_from_probs(probs, k=6)
                round_hits += len(set(top6) & actual_reds)
                
                if actual_blue in top6:
                    round_blue_hits += 1
            
            avg_red_brier = round_red_brier / (test_end - test_start)
            per_round_red_brier.append(avg_red_brier)
            per_round_hits.append(round_hits / (test_end - test_start))
            per_round_blue_hit.append(round_blue_hits / (test_end - test_start))
        
        if not per_round_red_brier:
            return self.evaluator._empty_result(formula)
        
        # 计算汇总指标 (复用原评估器的逻辑)
        red_brier = sum(per_round_red_brier) / len(per_round_red_brier)
        avg_hits = sum(per_round_hits) / len(per_round_hits)
        blue_hit_rate = sum(per_round_blue_hit) / len(per_round_blue_hit)
        
        red_std = math.sqrt(
            sum((b - red_brier) ** 2 for b in per_round_red_brier) / max(len(per_round_red_brier) - 1, 1)
        )
        hits_std = math.sqrt(
            sum((h - avg_hits) ** 2 for h in per_round_hits) / max(len(per_round_hits) - 1, 1)
        )
        
        RANDOM_HIT_BASELINE = 1.09
        beats_random_brier = red_brier < self.evaluator.RED_BRIER_BASELINE * 0.95
        beats_random_hits = avg_hits > RANDOM_HIT_BASELINE
        
        brier_score_normalized = 1.0 - red_brier / 0.3
        hits_score_normalized = avg_hits / 3.0
        combined_score = 0.6 * brier_score_normalized + 0.4 * hits_score_normalized
        beats_random = beats_random_hits or beats_random_brier
        
        split = len(per_round_red_brier) * 7 // 10
        if split > 0 and split < len(per_round_red_brier):
            early_avg = sum(per_round_red_brier[:split]) / split
            late_avg = sum(per_round_red_brier[split:]) / (len(per_round_red_brier) - split)
            generalization_gap = abs(late_avg - early_avg)
        else:
            generalization_gap = 0.0
        
        return {
            "avg_brier": round(red_brier, 6),
            "avg_hits": round(avg_hits, 4),
            "blue_hit_rate": round(blue_hit_rate, 6),
            "beats_random": beats_random,
            "beats_random_brier": beats_random_brier,
            "beats_random_hits": beats_random_hits,
            "combined_score": round(combined_score, 6),
            "stability": round(-red_std, 6),
            "stability_std": round(red_std, 6),
            "hits_std": round(hits_std, 6),
            "rounds": len(per_round_red_brier),
            "generalization_gap": round(generalization_gap, 6),
            "overfitting_risk": "HIGH" if generalization_gap > 0.02 else "MEDIUM" if generalization_gap > 0.01 else "LOW",
            "per_round_red_brier": [round(b, 6) for b in per_round_red_brier],
            "per_round_hits": [round(h, 4) for h in per_round_hits],
            "formula_name": getattr(formula, "name", "unknown"),
            "evaluated_at": datetime.now().isoformat(),
            "cache_stats": {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "speedup_est": round((self._cache_hits + self._cache_misses) / max(self._cache_misses, 1), 2),
            }
        }
    
    def clear_cache(self):
        """清空缓存"""
        self._score_cache.clear()
        self._prob_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_cache_stats(self) -> Dict:
        return {
            "cached_train_ends": len(self._prob_cache),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
        }


def evaluate_batch_parallel(
    formulas_dict: Dict[str, Any],
    draws: Any,
    ev: 'FormulaEvaluatorV3',
    n_windows: int = 15,
    window_size: int = 300,
    step: int = 50,
    max_workers: int = 8,
) -> Dict[str, Dict]:
    """
    并行评估多个公式。

    Args:
        formulas_dict: {name: formula} 字典
        draws: 历史数据
        ev: 评估器实例
        n_windows: 窗口数
        window_size: 训练窗口大小
        step: 步进
        max_workers: 最大线程数（默认CPU核心数-2）
        use_cache: 是否使用缓存

    Returns:
        {name: evaluation_result} 字典
    """
    results = {}
    cache = get_eval_cache()
    total = len(formulas_dict)

    def _eval_one(name, formula):
        # 先查缓存
        cached = cache.get(name, len(draws), n_windows, window_size, step)
        if cached:
            return name, cached, True  # hit

        # 评估
        result = ev.evaluate(formula, draws, n_windows=n_windows,
                            window_size=window_size, step=step)

        # 写缓存
        cache.put(name, len(draws), n_windows, window_size, step, result)

        return name, result, False  # miss

    # 并行执行
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_eval_one, name, formula): name
                   for name, formula in formulas_dict.items()}

        hits = 0
        misses = 0
        for future in as_completed(futures):
            name, result, is_hit = future.result()
            results[name] = result
            if is_hit:
                hits += 1
            else:
                misses += 1

    print(f"    [Cache] hits={hits}, misses={misses}/{total}")
    return results

