# -*- coding: utf-8 -*-
"""
前向滚动回测框架 V2 (Walk-Forward Backtest V2)

V2 改进（基于 V1 的问题）：
1. V1 的 Engine (1.95) < Random (2.10)，因为评分函数引入了系统性偏差
2. V2 改为诚实评估：区分"有物理信号"和"无信号"两种情况
3. 新增统计显著性检验（p-value），不只是平均值对比
4. 新增校准误差（Calibration Error）：评估置信度是否准确
5. 新增多轮随机对照：不是单次 Random，而是 100 次随机实验取分布

设计：
- 初始训练窗口: 500 期
- 滚动步长: 1 期
- 每次用前 N 期数据生成预测，与第 N+1 期真实开奖碰撞
- 同时生成 100 次随机对照组的预测分布
- 输出完整的命中率对比报告 + 统计显著性
"""
import sys
import math
import json
import os
import random
import argparse
from datetime import datetime
from collections import Counter
from typing import List, Tuple, Dict, Optional
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
N_RANDOM_ROUNDS = 100  # 随机对照实验次数


# ─── 数据结构 ─────────────────────────────────────────────
@dataclass
class RoundResult:
    """单轮回测结果"""
    period: int
    train_size: int
    engine_red_hits: int
    engine_blue_hit: bool
    engine_best_of_k: int  # 如果生成了 K 组，取最好的
    random_avg_red: float
    random_median_red: int
    random_p_value: float  # engine 优于随机的 p 值
    calibration_error: float  # 置信度校准误差


@dataclass
class BacktestResult:
    """完整回测结果"""
    engine: Dict[str, float]
    random_baseline: Dict[str, float]
    rounds: List[RoundResult]
    statistical_summary: Dict[str, float]
    config: Dict[str, int]


# ─── 预测生成 ─────────────────────────────────────────────

def _normalize_prediction(pred, method: str, idx: int) -> Dict:
    """统一预测格式"""
    if isinstance(pred, dict):
        scores = pred.get("scores", {})
        if isinstance(scores, dict) and "total_score" not in scores:
            # 没有 total_score，用 causal_multiplier 代替
            scores["total_score"] = scores.get("causal_multiplier", 0.5)
        return {
            "group": idx,
            "method": method,
            "reds": pred["reds"],
            "blue": pred["blue"],
            "scores": scores if isinstance(scores, dict) else {},
        }
    # 兼容旧格式: (reds, blue, scores)
    reds, blue, scores = pred
    if not isinstance(scores, dict):
        scores = {"total_score": float(scores)}
    return {
        "group": idx,
        "method": method,
        "reds": reds,
        "blue": blue,
        "scores": scores,
    }


def generate_engine_predictions(
    draws: List[Draw],
    top_k: int = 5,
    engine: str = "auto",
) -> List[Dict]:
    """
    使用指定引擎生成预测，逐级降级。

    Args:
        engine: "luckcast" | "enhanced" | "fusion" | "auto"
    """
    predictions = []

    if engine in ("auto", "luckcast"):
        # Luckcast V15
        try:
            from luckcast_antigravity_v1 import rank_candidates
            pool = rank_candidates(draws, n_candidates=1000, top_k=top_k)
            for idx, p in enumerate(pool, 1):
                predictions.append(_normalize_prediction(p, "LuckcastV15", idx))
            if predictions:
                return predictions
        except Exception as e:
            pass

    if engine in ("auto", "enhanced"):
        # Enhanced Predictor V2.0
        try:
            import pandas as pd
            csv_file = Path(__file__).parent / "data" / "lottery_history.csv"
            df = pd.read_csv(csv_file)

            from enhanced_predictor import WeightedEnsemble
            ensemble = WeightedEnsemble(df)
            preds = ensemble.generate(num_groups=top_k)
            for idx, p in enumerate(preds, 1):
                pred_dict = {
                    "reds": p["reds"],
                    "blue": p["blue"],
                    "scores": {
                        "total_score": p.get("causal_multiplier", 0.5),
                        "causal_valid": p.get("causal_valid", True),
                    },
                }
                predictions.append(_normalize_prediction(pred_dict, "EnhancedV2", idx))
            if predictions:
                return predictions
        except Exception as e:
            pass

    # 全部失败：返回空列表
    return predictions


def generate_fusion_predictions(
    draws: List[Draw],
    top_k: int = 5,
) -> List[Dict]:
    """
    Fusion 引擎：同时运行 Luckcast + Enhanced，取跨引擎共振组合。
    """
    try:
        from luckcast_antigravity_v1 import rank_candidates as lc_rank
        import pandas as pd
        from enhanced_predictor import WeightedEnsemble

        csv_file = Path(__file__).parent / "data" / "lottery_history.csv"
        df = pd.read_csv(csv_file)

        # 并行获取两引擎预测
        lc_preds = lc_rank(draws, n_candidates=1000, top_k=top_k * 2)
        ensemble = WeightedEnsemble(df)
        en_preds = ensemble.generate(num_groups=top_k * 2)

        # 红球组合共振计数
        from collections import Counter
        combo_counter: Counter = Counter()
        combo_map: Dict = {}

        for red, blue, scores in lc_preds:
            key = tuple(sorted(red))
            combo_counter[key] += 1
            if key not in combo_map:
                combo_map[key] = {"lc": [], "en": []}
            combo_map[key]["lc"].append((list(red), int(blue), scores))

        for p in en_preds:
            key = tuple(sorted(p["reds"]))
            combo_counter[key] += 1
            if key not in combo_map:
                combo_map[key] = {"lc": [], "en": []}
            combo_map[key]["en"].append((p["reds"], p["blue"], {}))

        # 取共振组合（至少一个引擎推荐）
        fused = []
        for combo, count in combo_counter.most_common(top_k):
            candidates = combo_map[combo]
            # 取LC引擎的蓝球（如果有）
            if candidates["lc"]:
                _, blue, scores = candidates["lc"][0]
            elif candidates["en"]:
                _, blue, _ = candidates["en"][0]
            else:
                blue = 8

            fused.append({
                "group": len(fused) + 1,
                "method": "Fusion",
                "reds": list(combo),
                "blue": blue,
                "scores": {
                    "total_score": count / 2.0,  # 归一化到 1.0
                    "cross_engine_support": count,
                },
            })

        return fused

    except Exception as e:
        return []


def generate_random_predictions(top_k: int = 5) -> List[Dict]:
    """生成随机对照组预测"""
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


# ─── 碰撞检测 ─────────────────────────────────────────────
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


# ─── 统计检验 ─────────────────────────────────────────────
def t_test_one_tailed(engine_hits: List[float], random_hits: List[float]) -> float:
    """
    单侧 t 检验：engine 是否显著优于 random。

    返回 p 值。p < 0.05 表示显著。
    """
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
    # 近似 p 值（大样本时用正态分布）
    p_value = 1 - _normal_cdf(t_stat)
    return p_value


def _normal_cdf(x: float) -> float:
    """标准正态分布 CDF 近似"""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def calibration_error(confidences: List[float], hits: List[int]) -> float:
    """
    校准误差：预测置信度与实际命中率的偏差。

    如果模型说"我有 80% 把握命中"，实际命中率应该接近 80%。
    V2.1 修复：数据不足时返回 0.0 而非 NaN，避免汇总时污染。
    """
    if not confidences or not hits:
        return 0.0

    if len(confidences) < 5:
        # 数据不足，返回一个保守的估计值
        return 0.5

    bins = min(5, len(confidences) // 2)
    bin_size = len(confidences) // bins
    if bin_size < 2:
        return 0.5

    total_error = 0.0
    count = 0

    for i in range(bins):
        start = i * bin_size
        end = start + bin_size if i < bins - 1 else len(confidences)
        if start >= len(confidences):
            break

        bin_conf = float(np.mean(confidences[start:end]))
        bin_hit_rate = float(np.mean(hits[start:end]))
        total_error += abs(bin_conf - bin_hit_rate)
        count += 1

    return total_error / count if count > 0 else 0.0


# ─── 前向滚动回测 ─────────────────────────────────────────
def walk_forward_backtest(
    draws: List[Draw],
    initial_window: int = INITIAL_WINDOW,
    top_k: int = 5,
    n_rounds: int = None,
    engine: str = None,
) -> BacktestResult:
    total = len(draws)
    if n_rounds is None:
        n_rounds = total - initial_window
    n_rounds = min(n_rounds, total - initial_window)

    print(f"回测配置: 窗口={initial_window}, 轮数={n_rounds}, "
          f"总数据={total} 期 (#{draws[0].period} ~ #{draws[-1].period})")
    print()

    engine_red_hits = []
    engine_blue_hits = []
    engine_confidences = []
    engine_best_hits = []

    random_avg_reds = []
    random_p_values = []
    cal_errors = []

    round_results = []

    for i in range(initial_window, initial_window + n_rounds):
        train_data = draws[:i]
        test_draw = draws[i]

        # Engine 预测
        if engine:
            engine_preds = generate_engine_predictions(train_data, top_k, engine=engine)
        else:
            engine_preds = generate_engine_predictions(train_data, top_k)
        if not engine_preds:
            continue

        # Engine 碰撞（取最佳组）
        engine_scores = [collide(p, test_draw) for p in engine_preds]
        best_engine = max(engine_scores, key=lambda x: x["total_hits"])

        # 多轮随机对照（100 次实验）
        random_red_hits_dist = []
        for _ in range(N_RANDOM_ROUNDS):
            rand_preds = generate_random_predictions(top_k)
            rand_scores = [collide(p, test_draw) for p in rand_preds]
            best_rand = max(rand_scores, key=lambda x: x["total_hits"])
            random_red_hits_dist.append(best_rand["red_hits"])

        # 统计检验
        eng_red = best_engine["red_hits"]
        p_value = t_test_one_tailed(
            [eng_red] * (i - initial_window + 1),
            random_red_hits_dist,
        )

        # 记录
        engine_red_hits.append(eng_red)
        engine_blue_hits.append(1 if best_engine["blue_hit"] else 0)
        engine_best_hits.append(eng_red)

        # 从 scores 提取置信度
        conf = engine_preds[engine_scores.index(best_engine)].get("scores", {}).get(
            "total_score", 0.5
        )
        engine_confidences.append(conf)

        random_avg_reds.append(np.mean(random_red_hits_dist))
        random_p_values.append(p_value)

        cal_err = calibration_error(engine_confidences, engine_best_hits)
        cal_errors.append(cal_err)

        round_results.append(RoundResult(
            period=test_draw.period,
            train_size=len(train_data),
            engine_red_hits=eng_red,
            engine_blue_hit=bool(best_engine["blue_hit"]),
            engine_best_of_k=eng_red,
            random_avg_red=float(np.mean(random_red_hits_dist)),
            random_median_red=int(np.median(random_red_hits_dist)),
            random_p_value=p_value,
            calibration_error=cal_err,
        ))

    # 汇总统计
    eng_red_arr = np.array(engine_red_hits)
    rnd_arr = np.array(random_avg_reds)

    result = BacktestResult(
        engine={
            "avg_red_hits": float(np.mean(eng_red_arr)) if len(eng_red_arr) > 0 else 0,
            "blue_hit_rate": float(np.mean(engine_blue_hits)) if engine_blue_hits else 0,
            "max_red_hits": int(np.max(eng_red_arr)) if len(eng_red_arr) > 0 else 0,
            "median_red_hits": float(np.median(eng_red_arr)) if len(eng_red_arr) > 0 else 0,
            "std_red_hits": float(np.std(eng_red_arr)) if len(eng_red_arr) > 0 else 0,
            "rounds": len(eng_red_arr),
            "calibration_error": float(np.mean(cal_errors)) if cal_errors else 1.0,
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
        },
        config={
            "initial_window": initial_window,
            "n_rounds": n_rounds,
            "top_k": top_k,
            "n_random_rounds": N_RANDOM_ROUNDS,
        },
    )

    return result


# ─── 报告生成 ─────────────────────────────────────────────
def print_report(result: BacktestResult):
    eng = result.engine
    rnd = result.random_baseline
    stats = result.statistical_summary

    print("\n" + "=" * 72)
    print("  📊 前向滚动回测报告 V2 (统计显著性增强版)")
    print("=" * 72)

    print(f"\n--- 配置 ---")
    print(f"  初始窗口: {result.config['initial_window']} 期")
    print(f"  回测轮数: {result.config['n_rounds']}")
    print(f"  每组预测: {result.config['top_k']} 组")
    print(f"  随机对照: {result.config['n_random_rounds']} 轮")

    print(f"\n--- Engine (V11/V10) ---")
    print(f"  平均红球命中: {eng['avg_red_hits']:.2f} / 6  (±{eng['std_red_hits']:.2f})")
    print(f"  中位数红球命中: {eng['median_red_hits']:.2f}")
    print(f"  蓝球命中率: {eng['blue_hit_rate']:.2%}")
    print(f"  最大红球命中: {eng['max_red_hits']}")
    print(f"  校准误差: {eng['calibration_error']:.4f}")

    print(f"\n--- Random (100 轮对照) ---")
    print(f"  平均红球命中: {rnd['avg_red_hits']:.2f} / 6  (±{rnd['std_red_hits']:.2f})")
    print(f"  中位数红球命中: {rnd['median_red_hits']:.2f}")

    print(f"\n--- 统计显著性 ---")
    print(f"  显著优于随机 (p<0.05) 的轮数占比: {stats['p_value_significant']:.2%}")
    print(f"  平均 p 值: {stats['mean_p_value']:.4f}")
    print(f"  胜过随机中位数的轮数: {stats['wins_over_random']}/{eng['rounds']} ({stats['wins_over_random']/eng['rounds']:.2%})")

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

    # 理论随机基线
    print(f"\n--- 理论随机基线 ---")
    print(f"  红球期望命中: 6 * 6/33 = {6*6/33:.2f} (约 1.09)")
    print(f"  蓝球期望命中率: 1/16 = {1/16:.2%}")
    print(f"  100 中选最佳的期望红球命中: ~{1.09 + 0.9:.2f} (约 2.0)")

    # 详细结果（最近 20 轮）
    if round_results := result.rounds:
        print(f"\n--- 最近 {min(20, len(round_results))} 轮详情 ---")
        print(f"{'期号':>6} | {'训练量':>5} | Engine红| Random中位| p值   | 校准误差")
        print("-" * 75)
        for r in round_results[-20:]:
            p_str = f"{r.random_p_value:.3f}" if r.random_p_value < 0.1 else "  >0.1"
            print(f"{r.period:>6} | {r.train_size:>5} | "
                  f"  {r.engine_red_hits:>2}    | {r.random_median_red:>10} | "
                  f"{p_str:>5} | {r.calibration_error:.3f}")


def generate_markdown_report(result: BacktestResult, output_path: str):
    eng = result.engine
    rnd = result.random_baseline
    stats = result.statistical_summary

    lines = []
    lines.append("# 📊 Antigravity 前向滚动回测报告 V2")
    lines.append(f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> **配置**: 初始窗口={result.config['initial_window']}, "
                 f"回测轮数={result.config['n_rounds']}")
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
    lines.append(f"| 校准误差 | {eng['calibration_error']:.4f} | - | |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 统计显著性")
    lines.append("")
    lines.append(f"- 显著优于随机 (p<0.05) 的轮数占比: {stats['p_value_significant']:.2%}")
    lines.append(f"- 平均 p 值: {stats['mean_p_value']:.4f}")
    lines.append(f"- 胜过随机中位数的轮数: {stats['wins_over_random']}/{eng['rounds']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🎯 理论随机基线")
    lines.append("")
    lines.append("| 指标 | 理论值 |")
    lines.append("|------|--------|")
    lines.append(f"| 红球期望命中 | {6*6/33:.2f} (约1.09) |")
    lines.append(f"| 蓝球期望命中率 | {1/16:.2%} (1/16) |")
    lines.append(f"| 100 中选最佳期望 | ~{1.09 + 0.9:.2f} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🔍 结论")
    lines.append("")

    diff_red = eng['avg_red_hits'] - rnd['avg_red_hits']
    if diff_red > 0.2:
        lines.append(f"> ✅ Engine 平均红球命中 {eng['avg_red_hits']:.2f}，明显优于 Random 的 {rnd['avg_red_hits']:.2f}，")
        lines.append(f"> 差异 {diff_red:+.2f}，说明引擎有有效信号。")
    elif diff_red > 0:
        lines.append(f"> ⚠️ Engine 平均红球命中 {eng['avg_red_hits']:.2f}，略高于 Random 的 {rnd['avg_red_hits']:.2f}，")
        lines.append(f"> 差异 {diff_red:+.2f}，可能是选择效应（从 K 组中选最佳）。")
    else:
        lines.append(f"> ⚠️ Engine 平均红球命中 {eng['avg_red_hits']:.2f}，**不优于** Random 的 {rnd['avg_red_hits']:.2f}，")
        lines.append(f"> 差异 {diff_red:+.2f}。引擎没有有效信号，或信号太弱被噪声淹没。")

    lines.append("")
    lines.append("---")
    lines.append(f'*"数据不说谎，它只是换了一种方式告诉你真相。"')

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─── 多引擎对比回测 ───────────────────────────────────────

def run_comparison_backtest(
    draws: List[Draw],
    engines: List[str] = None,
    initial_window: int = INITIAL_WINDOW,
    top_k: int = 5,
    n_rounds: int = None,
) -> Dict[str, BacktestResult]:
    """
    对比多个引擎的回测结果。

    engines: ["LuckcastV15", "EnhancedV2", "Fusion", "Random"]
    """
    if engines is None:
        engines = ["LuckcastV15", "EnhancedV2", "Fusion"]

    results = {}
    for engine_name in engines:
        print(f"\n{'='*60}")
        print(f"  回测引擎: {engine_name}")
        print(f"{'='*60}")

        if engine_name == "Random":
            # 随机对照基线
            results["Random"] = _run_random_baseline(draws, top_k=top_k, n_rounds=n_rounds,
                                                      initial_window=initial_window)
        elif engine_name == "Fusion":
            results["Fusion"] = _run_fusion_backtest(draws, top_k=top_k, n_rounds=n_rounds,
                                                      initial_window=initial_window)
        else:
            # Map engine names to internal identifiers
            engine_map = {
                "LuckcastV15": "luckcast",
                "EnhancedV2": "enhanced",
                "Fusion": "fusion",
            }
            internal_name = engine_map.get(engine_name, engine_name)
            result = walk_forward_backtest(
                draws,
                initial_window=initial_window,
                top_k=top_k,
                n_rounds=n_rounds,
                engine=internal_name,
            )
            results[engine_name] = result

    # 汇总对比
    print(f"\n{'='*72}")
    print("  📊 多引擎回测对比总结")
    print(f"{'='*72}")
    print(f"\n{'引擎':<15} | {'红球命中':>10} | {'蓝球率':>8} | {'p值显著':>8} | {'校准误差':>8}")
    print("-" * 65)
    for name, result in results.items():
        eng = result.engine
        stats = result.statistical_summary if hasattr(result, 'statistical_summary') else {}
        cal = eng.get('calibration_error', 0)
        sig = stats.get('p_value_significant', 0) if isinstance(stats, dict) else 0
        print(f"{name:<15} | {eng['avg_red_hits']:>10.2f} | {eng['blue_hit_rate']:>8.2%} | "
              f"{sig:>8.2%} | {cal:>8.4f}")

    return results


def _run_random_baseline(draws, top_k, n_rounds, initial_window):
    """纯随机对照基线回测"""
    from random import randint
    import numpy as np

    engine_hits = []
    engine_blues = []

    total = len(draws)
    n = n_rounds or (total - initial_window)

    for i in range(initial_window, initial_window + n):
        test_draw = draws[i]
        # 随机生成 top_k 组
        best_hits = 0
        best_blue = False
        for _ in range(top_k):
            reds = sorted(randint(1, 33) for _ in range(6))
            # 去重
            reds = sorted(set(reds))
            while len(reds) < 6:
                reds.append(sorted(set(reds.union({randint(1, 33)})))[len(reds)])
            reds = sorted(reds)[:6]
            blue = randint(1, 16)
            hits = len(set(reds) & set(test_draw.reds))
            if hits > best_hits or (hits == best_hits and blue == test_draw.blue):
                best_hits = hits
                best_blue = (blue == test_draw.blue)

        engine_hits.append(best_hits)
        engine_blues.append(1 if best_blue else 0)

    eng_arr = np.array(engine_hits)
    return BacktestResult(
        engine={
            "avg_red_hits": float(np.mean(eng_arr)),
            "blue_hit_rate": float(np.mean(engine_blues)),
            "max_red_hits": int(np.max(eng_arr)),
            "median_red_hits": float(np.median(eng_arr)),
            "std_red_hits": float(np.std(eng_arr)),
            "rounds": len(eng_arr),
            "calibration_error": 0.0,
        },
        random_baseline={},
        rounds=[],
        statistical_summary={},
        config={"initial_window": initial_window, "n_rounds": n, "top_k": top_k, "n_random_rounds": 0},
    )


def _run_fusion_backtest(draws, top_k, n_rounds, initial_window):
    """Fusion 引擎回测"""
    engine_hits = []
    engine_blues = []

    total = len(draws)
    n = n_rounds or (total - initial_window)

    for i in range(initial_window, initial_window + n):
        train_data = draws[:i]
        test_draw = draws[i]

        preds = generate_fusion_predictions(train_data, top_k=top_k)
        if not preds:
            continue

        best_hits = 0
        best_blue = False
        for p in preds:
            hits = len(set(p["reds"]) & set(test_draw.reds))
            blue_hit = (p["blue"] == test_draw.blue)
            if hits > best_hits or (hits == best_hits and blue_hit):
                best_hits = hits
                best_blue = blue_hit

        engine_hits.append(best_hits)
        engine_blues.append(1 if best_blue else 0)

    import numpy as np
    eng_arr = np.array(engine_hits) if engine_hits else np.array([0])
    return BacktestResult(
        engine={
            "avg_red_hits": float(np.mean(eng_arr)),
            "blue_hit_rate": float(np.mean(engine_blues)) if engine_blues else 0,
            "max_red_hits": int(np.max(eng_arr)),
            "median_red_hits": float(np.median(eng_arr)),
            "std_red_hits": float(np.std(eng_arr)),
            "rounds": len(eng_arr),
            "calibration_error": 0.0,
        },
        random_baseline={},
        rounds=[],
        statistical_summary={},
        config={"initial_window": initial_window, "n_rounds": n, "top_k": top_k, "n_random_rounds": 0},
    )


# ─── 入口 ─────────────────────────────────────────────────
def run(csv_path=None, n_rounds=None, top_k=5, initial_window=None,
        output_dir=None, engine="auto", ablation=False):
    print("=" * 72)
    print("  🚀 Antigravity 前向滚动回测系统 V2")
    print("=" * 72)

    draws = load_history(csv_path)
    min_win = initial_window or INITIAL_WINDOW
    if len(draws) < min_win:
        print(f"数据量不足 ({len(draws)} 期)，需要至少 {min_win} 期。")
        return

    # 检查是否请求消融模式
    if ablation:
        print("\n" + "=" * 72)
        print("  🔬 消融回测: 逐维度/策略独立评估")
        print("=" * 72)

        # Luckcast V15 各维度消融
        try:
            from luckcast_antigravity_v1 import DIMENSIONS, LearningState, _DIM_NAMES
            import numpy as np

            draws = load_history(csv_path)
            state = LearningState(_DIM_NAMES)

            print(f"\n--- Luckcast V15 维度消融 (窗口={initial_window or INITIAL_WINDOW}, 轮数={n_rounds or (len(draws)-(initial_window or INITIAL_WINDOW))}) ---")
            print(f"{'维度':<20} | {'红球命中':>10} | {'蓝球率':>8}")
            print("-" * 50)

            for i, dim_cls in enumerate(DIMENSIONS):
                # 临时只启用当前维度
                original_dims = DIMENSIONS[:]
                # 生成该维度的候选池
                dim_rng = random.Random(42 + i * 1000)
                pool = dim_cls.generate_pool(draws[:initial_window or 500], pool_size=200, rng=dim_rng)

                dim_hits = []
                dim_blues = []
                n_ablation = min(n_rounds or 30, len(draws) - (initial_window or 500))

                for j in range(n_ablation):
                    idx = (initial_window or 500) + j
                    if idx >= len(draws):
                        break
                    test = draws[idx]
                    best = 0
                    best_blue_hit = False
                    for red, blue in pool:
                        h = len(set(red) & set(test.reds))
                        if h > best or (h == best and blue == test.blue):
                            best = h
                            best_blue_hit = (blue == test.blue)
                    dim_hits.append(best)
                    dim_blues.append(1 if best_blue_hit else 0)

                if dim_hits:
                    avg_hits = np.mean(dim_hits)
                    blue_rate = np.mean(dim_blues)
                    print(f"  {dim_cls.name:<18} | {avg_hits:>10.2f} | {blue_rate:>7.0%}")
        except Exception as e:
            print(f"[WARN] 维度消融失败: {e}")

        print()
        return

    # 检查是否请求对比模式
    if engine == "compare":
        results = run_comparison_backtest(
            draws,
            engines=["LuckcastV15", "EnhancedV2", "Fusion"],
            initial_window=initial_window or INITIAL_WINDOW,
            top_k=top_k,
            n_rounds=n_rounds,
        )
        # 保存对比结果
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(__file__))
        comp_path = os.path.join(output_dir, "comparison_backtest_v2.json")
        with open(comp_path, "w", encoding="utf-8") as f:
            json.dump({
                name: {
                    "engine": r.engine,
                    "config": r.config,
                }
                for name, r in results.items()
            }, f, ensure_ascii=False, indent=2)
        print(f"\n>>> 对比结果已保存: {comp_path}")
        return

    result = walk_forward_backtest(
        draws,
        initial_window=initial_window or INITIAL_WINDOW,
        top_k=top_k,
        n_rounds=n_rounds,
        engine=engine if engine != "auto" else None,
    )

    print_report(result)

    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    report_path = os.path.join(output_dir, "walkforward_report_v2.md")
    generate_markdown_report(result, report_path)
    print(f"\n>>> Markdown 报告已保存: {report_path}")

    data_path = os.path.join(output_dir, "walkforward_results_v2.json")
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
                "random_avg_red": r.random_avg_red,
                "random_median_red": r.random_median_red,
                "p_value": r.random_p_value,
                "calibration_error": r.calibration_error,
            }
            for r in result.rounds
        ],
    }
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print(f">>> 原始数据已保存: {data_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="前向滚动回测 V2")
    parser.add_argument("--data-file", help="CSV 数据文件路径")
    parser.add_argument("--n-rounds", type=int, help="回测轮数 (None=滚到最后一期)")
    parser.add_argument("--top-k", type=int, default=5, help="每组预测几组号码")
    parser.add_argument("--initial-window", type=int, help="初始训练窗口大小")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--engine", choices=["auto", "luckcast", "enhanced", "compare"],
                        default="auto", help="回测引擎")
    parser.add_argument("--ablation", action="store_true", help="逐维度/策略消融回测")
    args = parser.parse_args()

    run(
        csv_path=args.data_file,
        n_rounds=args.n_rounds,
        top_k=args.top_k,
        initial_window=args.initial_window,
        output_dir=args.output_dir,
        engine=args.engine,
        ablation=args.ablation,
    )
