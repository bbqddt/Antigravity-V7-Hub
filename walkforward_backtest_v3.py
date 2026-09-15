# -*- coding: utf-8 -*-
"""
前向滚动回测框架 V3 (Walk-Forward Backtest V3)

V3 改进（基于 V2 的问题）：
1. V2 用命中数评估，但双色球期望命中 ~2.0，很难区分信号和噪声
2. V3 改用 Brier Score：评估概率预测的校准质量
   - 从引擎的组级预测派生 per-number 概率分布
   - Brier = mean((p_n - y_n)^2)，越小越准
   - 随机均匀分布的 Brier ≈ 0.139
3. 集成 EWMA 权重管理：每轮更新公式权重，下一轮加权投票
4. 全量历史数据做评估，不用短期 20 期
5. 新增公式存活/淘汰决策

核心理念：
- 不追求"碰巧命中高"，追求"概率输出准"
- 短期波动是噪声，长期校准才是信号
- 权重缓慢衰减(alpha=0.05)，不让一两期决定生死
"""
import sys
import math
import json
import os
import random
import argparse
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Fix Windows GBK encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

from data_layer import load_history, Draw


# ─── 配置 ─────────────────────────────────────────────────
INITIAL_WINDOW = 500
MIN_WINDOW = 100
RANDOM_SEED = 42
N_RANDOM_ROUNDS = 100
EWMA_ALPHA = 0.05       # 权重衰减因子
BLUE_BALL_EWMA_ALPHA = 0.05
MIN_WEIGHT_RATIO = 0.01  # 最低权重保护


# ─── 数据结构 ─────────────────────────────────────────────

@dataclass
class RoundResult:
    """单轮回测结果"""
    period: int
    train_size: int
    engine_red_hits: int
    engine_blue_hit: bool
    red_brier: float          # 红球 Brier Score
    blue_brier: float         # 蓝球 Brier Score
    random_avg_red: float
    random_median_red: float  # 随机对照组中位数命中
    random_p_value: float
    formula_weights: Dict[str, float]  # 本轮各公式权重


@dataclass
class BacktestResult:
    """完整回测结果"""
    engine: Dict[str, float]
    random_baseline: Dict[str, float]
    rounds: List[RoundResult]
    statistical_summary: Dict[str, float]
    config: Dict[str, int]
    formula_performance: Dict[str, Dict]  # 每个公式的历史表现


# ═══════════════════════════════════════════════════════════
# 公式权重管理器 — Brier Score + EWMA
# ═══════════════════════════════════════════════════════════

class FormulaWeightManager:
    """
    公式权重管理器。

    核心指标：Brier Score
    - 对每个号码 n，公式输出一个概率 p_n
    - 实际开出 y_n = 1 如果 n 开了，否则 0
    - Brier = mean((p_n - y_n)^2) over all 33 numbers

    Brier Score 越小越好：
    - 完美预测: 0.0
    - 均匀随机 (1/33): ~0.029
    """

    def __init__(self, alpha: float = EWMA_ALPHA, min_weight: float = MIN_WEIGHT_RATIO):
        self.alpha = alpha
        self.min_weight = min_weight
        self.weights: Dict[str, float] = {}
        self.brier_history: Dict[str, List[float]] = defaultdict(list)
        self.total_rounds: Dict[str, int] = defaultdict(int)
        self.round_count: int = 0

    def register(self, name: str, weight: float = 1.0):
        self.weights[name] = weight
        self.brier_history[name] = []
        self.total_rounds[name] = 0

    def unregister(self, name: str):
        self.weights.pop(name, None)
        self.brier_history.pop(name, None)
        self.total_rounds.pop(name, None)

    def update(self, formula_name: str, probs: Dict[int, float], actual_reds: set):
        if formula_name not in self.weights:
            self.register(formula_name)

        self.round_count += 1
        self.total_rounds[formula_name] += 1

        # 红球 Brier
        red_brier = self._compute_red_brier(probs, actual_reds)
        self.brier_history[formula_name].append(red_brier)

        # EWMA 更新权重: Brier 越小 → 权重越大
        old_weight = self.weights[formula_name]
        new_weight = old_weight * math.exp(-self.alpha * red_brier)
        self.weights[formula_name] = new_weight

        # 最低权重保护
        current_total = sum(self.weights.values())
        if current_total > 0:
            ratio = self.weights[formula_name] / current_total
            if ratio < self.min_weight:
                self.weights[formula_name] = current_total * self.min_weight

    @staticmethod
    def _compute_red_brier(probs: Dict[int, float], actual: set) -> float:
        total = 0.0
        for n in range(1, 34):
            p = probs.get(n, 1.0 / 33.0)
            y = 1.0 if n in actual else 0.0
            total += (p - y) ** 2
        return total / 33.0

    def get_weights(self) -> Dict[str, float]:
        total = sum(self.weights.values())
        if total <= 0:
            n = len(self.weights)
            return {name: 1.0 / max(n, 1) for name in self.weights}
        return {name: w / total for name, w in self.weights.items()}

    def get_formula_performance(self, name: str) -> Dict:
        history = self.brier_history.get(name, [])
        if not history:
            return {"avg_brier": None, "rounds": 0, "trend": "no_data"}

        avg_brier = sum(history) / len(history)
        recent_10 = history[-10:]
        recent_avg = sum(recent_10) / len(recent_10)

        trend = "stable"
        if len(history) >= 5:
            mid = len(history) // 2
            early = sum(history[:mid]) / mid
            late = sum(history[mid:]) / (len(history) - mid)
            if late < early * 0.9:
                trend = "improving"
            elif late > early * 1.1:
                trend = "degrading"

        return {
            "avg_brier": round(avg_brier, 6),
            "recent_avg_brier": round(recent_avg, 6),
            "rounds": len(history),
            "trend": trend,
            "min_brier": round(min(history), 6),
            "max_brier": round(max(history), 6),
        }

    def reset(self):
        self.weights.clear()
        self.brier_history.clear()
        self.total_rounds.clear()
        self.round_count = 0


# ═══════════════════════════════════════════════════════════
# 从组级预测派生 per-number 概率分布
# ═══════════════════════════════════════════════════════════

def predictions_to_probs(predictions: List[Dict], temperature: float = 2.0) -> Dict[int, float]:
    """
    将引擎输出的组级预测转换为 33 个号码的概率分布。

    方法：
    1. 对每组预测，给其中的 6 个红球加分（权重 = 分数 × 排名衰减）
    2. 给未出现的号码加一个极小的基础分
    3. Softmax 归一化

    这样 Brier Score 才能真正衡量概率校准质量。
    """
    if not predictions:
        return {n: 1.0 / 33.0 for n in range(1, 34)}

    raw_scores = defaultdict(float)
    base_score = 0.01  # 基础分，确保所有号码都有非零概率

    for idx, pred in enumerate(predictions):
        reds = pred["reds"]
        score = pred.get("scores", {})
        if isinstance(score, dict):
            group_score = score.get("total_score", 0.5)
        else:
            group_score = float(score)

        # 排名衰减：排越前的组，其号码权重越高
        rank_decay = 1.0 / (idx + 1)

        for n in reds:
            raw_scores[n] += group_score * rank_decay

    # Softmax 转换
    max_val = max(raw_scores.values()) if raw_scores else 0
    exp_scores = {}
    for n in range(1, 34):
        s = raw_scores.get(n, base_score)
        exp_scores[n] = math.exp((s - max_val) / temperature)

    total = sum(exp_scores.values())
    probs = {n: v / total for n, v in exp_scores.items()}

    return probs


# ═══════════════════════════════════════════════════════════
# 预测生成
# ═══════════════════════════════════════════════════════════

def generate_engine_predictions(
    draws: List[Draw],
    top_k: int = 5,
    engine: str = "auto",
) -> List[Dict]:
    """
    使用指定引擎生成预测，逐级降级。
    """
    # None 和 "auto" 都意味着自动选择
    if engine is None:
        engine = "auto"

    predictions = []

    if engine in ("auto", "luckcast"):
        try:
            from luckcast_antigravity_v1 import rank_candidates
            pool = rank_candidates(draws, n_candidates=1000, top_k=top_k)
            for idx, p in enumerate(pool, 1):
                if isinstance(p, dict):
                    predictions.append({
                        "group": idx,
                        "method": "LuckcastV15",
                        "reds": p["reds"],
                        "blue": p["blue"],
                        "scores": p.get("scores", {}),
                    })
                else:
                    reds, blue, sc = p
                    predictions.append({
                        "group": idx,
                        "method": "LuckcastV15",
                        "reds": reds,
                        "blue": blue,
                        "scores": {"total_score": float(sc) if not isinstance(sc, dict) else sc.get("total_score", 0.5)},
                    })
            if predictions:
                return predictions
        except Exception as e:
            pass

    if engine in ("auto", "enhanced"):
        try:
            import pandas as pd
            csv_file = Path(__file__).parent / "data" / "lottery_history.csv"
            df = pd.read_csv(csv_file)
            from enhanced_predictor import WeightedEnsemble
            ensemble = WeightedEnsemble(df)
            preds = ensemble.generate(num_groups=top_k)
            for idx, p in enumerate(preds, 1):
                predictions.append({
                    "group": idx,
                    "method": "EnhancedV2",
                    "reds": p["reds"],
                    "blue": p["blue"],
                    "scores": {
                        "total_score": p.get("causal_multiplier", 0.5),
                        "causal_valid": p.get("causal_valid", True),
                    },
                })
            if predictions:
                return predictions
        except Exception as e:
            pass

    return predictions


# ═══════════════════════════════════════════════════════════
# 碰撞检测 & Brier Score
# ═══════════════════════════════════════════════════════════

def collide(prediction: Dict, actual: Draw) -> Dict:
    pred_reds = set(prediction["reds"])
    red_hits = pred_reds & set(actual.reds)
    blue_hit = (prediction["blue"] == actual.blue)
    return {
        "red_hits": len(red_hits),
        "blue_hit": bool(blue_hit),
        "red_hit_numbers": sorted(red_hits),
        "total_hits": len(red_hits) + (1 if blue_hit else 0),
    }


def compute_brier_from_predictions(predictions: List[Dict], actual: Draw) -> tuple:
    """
    从一组预测中计算 Brier Score。

    Returns:
        (red_brier, blue_brier)
    """
    # 转换为概率分布
    probs = predictions_to_probs(predictions)

    actual_reds = set(actual.reds)
    actual_blue = actual.blue

    # 红球 Brier
    total = 0.0
    for n in range(1, 34):
        p = probs.get(n, 1.0 / 33.0)
        y = 1.0 if n in actual_reds else 0.0
        total += (p - y) ** 2
    red_brier = total / 33.0

    # 蓝球 Brier (简化: 预测蓝球命中则 0，否则 1)
    blue_hit = any(p["blue"] == actual_blue for p in predictions)
    blue_brier = 0.0 if blue_hit else 1.0

    return red_brier, blue_brier


# ═══════════════════════════════════════════════════════════
# 统计检验
# ═══════════════════════════════════════════════════════════

def t_test_one_tailed(engine_hits: List[float], random_hits: List[float]) -> float:
    if len(engine_hits) < 10 or len(random_hits) < 10:
        return 1.0

    eng_mean = np.mean(engine_hits)
    rnd_mean = np.mean(random_hits)
    eng_std = np.std(engine_hits, ddof=1)
    rnd_std = np.std(random_hits, ddof=1)

    n1, n2 = len(engine_hits), len(random_hits)
    se = np.sqrt(eng_std**2 / n1 + rnd_std**2 / n2) if (eng_std > 0 and rnd_std > 0) else 1.0

    if se == 0:
        return 1.0

    t_stat = (eng_mean - rnd_mean) / se
    p_value = 0.5 * (1 - math.erf(t_stat / math.sqrt(2)))
    return p_value


# ═══════════════════════════════════════════════════════════
# 前向滚动回测 V3
# ═══════════════════════════════════════════════════════════

def walk_forward_backtest_v3(
    draws: List[Draw],
    initial_window: int = INITIAL_WINDOW,
    top_k: int = 5,
    n_rounds: int = None,
    engine: str = None,
) -> BacktestResult:
    """
    V3 回测：Brier Score + EWMA 权重管理 + 全量历史
    """
    # None 和 "auto" 都意味着自动选择引擎
    if engine is None:
        engine = "auto"

    total = len(draws)
    if n_rounds is None:
        n_rounds = total - initial_window
    n_rounds = min(n_rounds, total - initial_window)

    print(f"回测配置: 窗口={initial_window}, 轮数={n_rounds}, "
          f"总数据={total} 期 (#{draws[0].period} ~ #{draws[-1].period})")
    print(f"EWMA Alpha={EWMA_ALPHA}, Min Weight={MIN_WEIGHT_RATIO}")
    print()

    # 权重管理器
    wm = FormulaWeightManager(alpha=EWMA_ALPHA, min_weight=MIN_WEIGHT_RATIO)

    engine_red_hits = []
    engine_blue_hits = []
    engine_red_briers = []
    engine_blue_briers = []

    random_avg_reds = []
    random_p_values = []

    round_results = []
    formula_brier_history: Dict[str, List[float]] = defaultdict(list)

    for i in range(initial_window, initial_window + n_rounds):
        train_data = draws[:i]
        test_draw = draws[i]

        # Engine 预测
        engine_preds = generate_engine_predictions(train_data, top_k, engine)
        if not engine_preds:
            continue

        # 取最佳组（按总命中数）
        engine_scores = [collide(p, test_draw) for p in engine_preds]
        best_engine = max(engine_scores, key=lambda x: x["total_hits"])

        # 用全部 K 组预测来计算 Brier（比只用最佳组更准确）
        red_brier, blue_brier = compute_brier_from_predictions(engine_preds, test_draw)

        # 更新权重管理器
        probs = predictions_to_probs(engine_preds)
        wm.update(
            formula_name=engine_preds[0]["method"],
            probs=probs,
            actual_reds=set(test_draw.reds),
        )

        # 多轮随机对照
        random_red_hits_dist = []
        for _ in range(N_RANDOM_ROUNDS):
            rand_preds = _generate_random_predictions(top_k)
            rand_scores_list = [collide(p, test_draw) for p in rand_preds]
            best_rand = max(rand_scores_list, key=lambda x: x["red_hits"])
            random_red_hits_dist.append(best_rand["red_hits"])

        # 统计检验
        eng_red = best_engine["red_hits"]
        p_value = t_test_one_tailed([eng_red] * (i - initial_window + 1), random_red_hits_dist)

        # 记录
        engine_red_hits.append(eng_red)
        engine_blue_hits.append(1 if best_engine["blue_hit"] else 0)
        engine_red_briers.append(red_brier)
        engine_blue_briers.append(blue_brier)
        formula_brier_history[engine_preds[0]["method"]].append(red_brier)

        random_avg_reds.append(np.mean(random_red_hits_dist))
        random_p_values.append(p_value)

        # 当前权重快照
        current_weights = wm.get_weights()

        round_results.append(RoundResult(
            period=test_draw.period,
            train_size=len(train_data),
            engine_red_hits=eng_red,
            engine_blue_hit=bool(best_engine["blue_hit"]),
            red_brier=red_brier,
            blue_brier=blue_brier,
            random_avg_red=float(np.mean(random_red_hits_dist)),
            random_median_red=float(np.median(random_red_hits_dist)),
            random_p_value=p_value,
            formula_weights=dict(current_weights),
        ))

    # 汇总
    eng_arr = np.array(engine_red_hits)
    rnd_arr = np.array(random_avg_reds)
    brier_arr = np.array(engine_red_briers)

    result = BacktestResult(
        engine={
            "avg_red_hits": float(np.mean(eng_arr)) if len(eng_arr) > 0 else 0,
            "blue_hit_rate": float(np.mean(engine_blue_hits)) if engine_blue_hits else 0,
            "max_red_hits": int(np.max(eng_arr)) if len(eng_arr) > 0 else 0,
            "median_red_hits": float(np.median(eng_arr)) if len(eng_arr) > 0 else 0,
            "std_red_hits": float(np.std(eng_arr)) if len(eng_arr) > 0 else 0,
            "rounds": len(eng_arr),
            "avg_red_brier": float(np.mean(brier_arr)) if len(brier_arr) > 0 else 0,
            "avg_blue_brier": float(np.mean(engine_blue_briers)) if engine_blue_briers else 0,
        },
        random_baseline={
            "avg_red_hits": float(np.mean(rnd_arr)) if len(rnd_arr) > 0 else 0,
            "median_red_hits": float(np.median(rnd_arr)) if len(rnd_arr) > 0 else 0,
            "std_red_hits": float(np.std(rnd_arr)) if len(rnd_arr) > 0 else 0,
            "rounds": len(rnd_arr),
        },
        rounds=round_results,
        statistical_summary={
            "p_value_significant": sum(1 for p in random_p_values if p < 0.05) / len(random_p_values) if random_p_values else 0,
            "mean_p_value": float(np.mean(random_p_values)) if random_p_values else 1.0,
            "wins_over_random": sum(1 for r in round_results if r.engine_red_hits > r.random_median_red),
            "brier_vs_random_ratio": float(np.mean(brier_arr) / 0.139) if len(brier_arr) > 0 else 1.0,
        },
        config={
            "initial_window": initial_window,
            "n_rounds": n_rounds,
            "top_k": top_k,
            "n_random_rounds": N_RANDOM_ROUNDS,
        },
        formula_performance={
            name: wm.get_formula_performance(name) for name in wm.weights
        },
    )

    return result


def _generate_random_predictions(top_k: int = 5) -> List[Dict]:
    predictions = []
    for i in range(top_k):
        reds = sorted(random.sample(range(1, 34), 6))
        blue = random.randint(1, 16)
        predictions.append({
            "group": f"random-{i+1}",
            "method": "random",
            "reds": reds,
            "blue": blue,
        })
    return predictions


# ═══════════════════════════════════════════════════════════
# 报告生成
# ═══════════════════════════════════════════════════════════

def print_report_v3(result: BacktestResult):
    eng = result.engine
    rnd = result.random_baseline
    stats = result.statistical_summary

    print("\n" + "=" * 72)
    print("  📊 前向滚动回测报告 V3 (Brier Score + EWMA 权重)")
    print("=" * 72)

    print(f"\n--- 配置 ---")
    print(f"  初始窗口: {result.config['initial_window']} 期")
    print(f"  回测轮数: {result.config['n_rounds']}")
    print(f"  EWMA Alpha: {EWMA_ALPHA}")
    print(f"  最低权重: {MIN_WEIGHT_RATIO}")

    print(f"\n--- Engine ---")
    print(f"  平均红球命中: {eng['avg_red_hits']:.2f} / 6  (±{eng['std_red_hits']:.2f})")
    print(f"  中位数红球命中: {eng['median_red_hits']:.2f}")
    print(f"  蓝球命中率: {eng['blue_hit_rate']:.2%}")
    print(f"  平均红球 Brier: {eng['avg_red_brier']:.4f}  (随机基线 ≈ 0.139)")
    print(f"  平均蓝球 Brier: {eng['avg_blue_brier']:.4f}")

    print(f"\n--- Random (100 轮对照) ---")
    print(f"  平均红球命中: {rnd['avg_red_hits']:.2f} / 6  (±{rnd['std_red_hits']:.2f})")
    print(f"  中位数红球命中: {rnd['median_red_hits']:.2f}")

    print(f"\n--- 统计显著性 ---")
    print(f"  显著优于随机 (p<0.05) 的轮数占比: {stats['p_value_significant']:.2%}")
    print(f"  平均 p 值: {stats['mean_p_value']:.4f}")
    print(f"  Brier vs 随机比率: {stats['brier_vs_random_ratio']:.4f}")
    print(f"    (< 1.0 表示比随机校准更好)")

    diff_red = eng['avg_red_hits'] - rnd['avg_red_hits']
    print(f"\n--- 对比 ---")
    print(f"  红球差异: {diff_red:+.2f}")

    if diff_red > 0.2:
        print(f"  ✅ Engine 优于随机")
    elif diff_red > 0:
        print(f"  ⚠️  Engine 略高于随机（可能是选择效应）")
    elif diff_red > -0.2:
        print(f"  ⚠️  Engine 与随机无显著差异")
    else:
        print(f"  ❌ Engine 不如随机")

    # Brier 解读
    brier_ratio = stats['brier_vs_random_ratio']
    print(f"\n--- Brier Score 解读 ---")
    if brier_ratio < 0.9:
        print(f"  ✅ Brier 比率 {brier_ratio:.4f} < 0.9，概率校准优于随机")
    elif brier_ratio < 1.0:
        print(f"  ⚠️  Brier 比率 {brier_ratio:.4f} ≈ 1.0，与随机相当")
    else:
        print(f"  ❌ Brier 比率 {brier_ratio:.4f} > 1.0，概率校准差于随机")

    # 公式性能
    if result.formula_performance:
        print(f"\n--- 公式性能排名 ---")
        print(f"{'公式':<20} | {'平均Brier':>10} | {'最近Brier':>10} | {'轮数':>5} | {'趋势':<12}")
        print("-" * 70)
        ranked = sorted(
            result.formula_performance.items(),
            key=lambda x: (x[1].get("avg_brier") or 999)
        )
        for name, perf in ranked[:10]:
            avg_b = perf.get("avg_brier")
            recent_b = perf.get("recent_avg_brier")
            rounds = perf.get("rounds", 0)
            trend = perf.get("trend", "?")
            avg_str = f"{avg_b:.4f}" if avg_b is not None else "N/A"
            recent_str = f"{recent_b:.4f}" if recent_b is not None else "N/A"
            print(f"  {name:<18} | {avg_str:>10} | {recent_str:>10} | {rounds:>5} | {trend:<12}")

    # 详细结果（最近 20 轮）
    if round_results := result.rounds:
        print(f"\n--- 最近 {min(20, len(round_results))} 轮详情 ---")
        print(f"{'期号':>6} | {'训练量':>5} | Engine红| Brier   | Random中位| p值   ")
        print("-" * 75)
        for r in round_results[-20:]:
            p_str = f"{r.random_p_value:.3f}" if r.random_p_value < 0.1 else "  >0.1"
            print(f"{r.period:>6} | {r.train_size:>5} | "
                  f"  {r.engine_red_hits:>2}    | {r.red_brier:.4f}   | "
                  f" {r.random_median_red:>8} | {p_str:>5}")


def generate_markdown_report_v3(result: BacktestResult, output_path: str):
    eng = result.engine
    rnd = result.random_baseline
    stats = result.statistical_summary

    lines = []
    lines.append("# 📊 Antigravity 前向滚动回测报告 V3")
    lines.append("> **生成时间**: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    lines.append(f"> **配置**: 初始窗口={result.config['initial_window']}, 回测轮数={result.config['n_rounds']}")
    lines.append(f"> **EWMA Alpha={EWMA_ALPHA}, 最低权重={MIN_WEIGHT_RATIO}**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📈 Engine vs Random (100 轮对照) 对比")
    lines.append("")
    lines.append("| 指标 | Engine | Random (100轮) | 差异 |")
    lines.append("|------|--------|----------------|------|")
    lines.append(f"| 平均红球命中 | {eng['avg_red_hits']:.2f}/6 | {rnd['avg_red_hits']:.2f}/6 | {eng['avg_red_hits']-rnd['avg_red_hits']:+.2f} |")
    lines.append(f"| 中位数红球命中 | {eng['median_red_hits']:.2f}/6 | {rnd['median_red_hits']:.2f}/6 | |")
    lines.append(f"| 蓝球命中率 | {eng['blue_hit_rate']:.2%} | - | |")
    lines.append(f"| 平均红球 Brier | {eng['avg_red_brier']:.4f} | - | |")
    lines.append(f"| 平均蓝球 Brier | {eng['avg_blue_brier']:.4f} | - | |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 统计显著性")
    lines.append("")
    lines.append(f"- 显著优于随机 (p<0.05) 的轮数占比: {stats['p_value_significant']:.2%}")
    lines.append(f"- 平均 p 值: {stats['mean_p_value']:.4f}")
    lines.append(f"- Brier vs 随机比率: {stats['brier_vs_random_ratio']:.4f}")
    lines.append(f"- 胜过随机中位数的轮数: {stats['wins_over_random']}/{eng['rounds']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🎯 理论随机基线")
    lines.append("")
    lines.append("| 指标 | 理论值 |")
    lines.append("|------|--------|")
    lines.append(f"| 红球期望命中 | {6*6/33:.2f} (约 1.09) |")
    lines.append(f"| 蓝球期望命中率 | {1/16:.2%} (1/16) |")
    lines.append(f"| 红球 Brier 基线 | 0.139 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🔍 结论")
    lines.append("")

    diff_red = eng['avg_red_hits'] - rnd['avg_red_hits']
    brier_ratio = stats['brier_vs_random_ratio']

    if brier_ratio < 0.9:
        lines.append(f"> ✅ Brier 比率 {brier_ratio:.4f} < 0.9，概率校准优于随机。")
        lines.append(f"> 引擎输出的概率分布比随机均匀分布更接近真实频率。")
    elif brier_ratio < 1.0:
        lines.append(f"> ⚠️  Brier 比率 {brier_ratio:.4f} ≈ 1.0，概率校准与随机相当。")
        lines.append(f"> 引擎可能有微弱信号，但被噪声淹没。")
    else:
        lines.append(f"> ❌ Brier 比率 {brier_ratio:.4f} > 1.0，概率校准差于随机。")
        lines.append(f"> 引擎的概率输出没有有效信号。")

    lines.append(f"> 红球命中差异: {diff_red:+.2f} (Engine {eng['avg_red_hits']:.2f} vs Random {rnd['avg_red_hits']:.2f})")
    lines.append("")
    lines.append("---")
    lines.append(f'*"数据不说谎，它只是换了一种方式告诉你真相。"')

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

def run(csv_path=None, n_rounds=None, top_k=5, initial_window=None,
        output_dir=None, engine="auto"):
    print("=" * 72)
    print("  🚀 Antigravity 前向滚动回测系统 V3 (Brier Score + EWMA)")
    print("=" * 72)

    draws = load_history(csv_path)
    min_win = initial_window or INITIAL_WINDOW
    if len(draws) < min_win:
        print(f"数据量不足 ({len(draws)} 期)，需要至少 {min_win} 期。")
        return

    result = walk_forward_backtest_v3(
        draws,
        initial_window=initial_window or INITIAL_WINDOW,
        top_k=top_k,
        n_rounds=n_rounds,
        engine=engine if engine != "auto" else None,
    )

    print_report_v3(result)

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    report_path = os.path.join(output_dir, "walkforward_report_v3.md")
    generate_markdown_report_v3(result, report_path)
    print(f"\n>>> Markdown 报告已保存: {report_path}")

    data_path = os.path.join(output_dir, "walkforward_results_v3.json")
    serializable = {
        "engine": result.engine,
        "random_baseline": result.random_baseline,
        "statistical_summary": result.statistical_summary,
        "config": result.config,
        "rounds": [
            {
                "period": r.period,
                "train_size": r.train_size,
                "engine_red_hits": r.engine_red_hits,
                "engine_blue_hit": r.engine_blue_hit,
                "red_brier": r.red_brier,
                "blue_brier": r.blue_brier,
                "random_avg_red": r.random_avg_red,
                "p_value": r.random_p_value,
            }
            for r in result.rounds
        ],
        "formula_performance": result.formula_performance,
    }
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print(f">>> 原始数据已保存: {data_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="前向滚动回测 V3 (Brier Score)")
    parser.add_argument("--data-file", help="CSV 数据文件路径")
    parser.add_argument("--n-rounds", type=int, help="回测轮数")
    parser.add_argument("--top-k", type=int, default=5, help="每组预测几组号码")
    parser.add_argument("--initial-window", type=int, help="初始训练窗口大小")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--engine", choices=["auto", "luckcast", "enhanced"],
                        default="auto", help="回测引擎")
    args = parser.parse_args()

    run(
        csv_path=args.data_file,
        n_rounds=args.n_rounds,
        top_k=args.top_k,
        initial_window=args.initial_window,
        output_dir=args.output_dir,
        engine=args.engine,
    )
