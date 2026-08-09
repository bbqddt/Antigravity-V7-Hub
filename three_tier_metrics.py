"""
Three-Tier Metrics for Formula Evaluation
独立模块，不改动原 formula_evolution.py
"""
import numpy as np
from typing import List, Dict, Any
from formula_evolution import FormulaMatchChecker

RANDOM_EXPECTATION = 6 * 6 / 33  # ≈ 1.09


def expected_calibration_error(probs: np.ndarray, outcomes: np.ndarray, n_bins: int = 10) -> float:
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i + 1])
        if not mask.any():
            continue
        acc = outcomes[mask].mean()
        conf = probs[mask].mean()
        ece += mask.mean() * abs(acc - conf)
    return float(ece)


def permutation_test(hits_list: List[int], n_bootstrap: int = 2000, block: int = 50) -> tuple:
    if not hits_list:
        return 1.0, 0.0
    arr = np.array(hits_list)
    obs_stat = arr.mean() - RANDOM_EXPECTATION
    n = len(arr)
    boot_stats = []
    for _ in range(n_bootstrap):
        idx = np.random.choice(n // block, size=n // block, replace=True)
        samp = np.concatenate([arr[i*block:(i+1)*block] for i in idx])[:n]
        boot_stats.append(samp.mean() - RANDOM_EXPECTATION)
    boot_stats = np.array(boot_stats)
    p_val = float((boot_stats >= obs_stat).mean())
    effect = float(obs_stat)
    return p_val, effect


def kelly_simulation(hits_per_period: List[int], odds: float = 1.0,
                     bankroll: float = 10000, n_sims: int = 2000) -> Dict:
    if not hits_per_period:
        return {"roi": 0, "ruin_prob": 1, "sharpe": 0, "max_drawdown": 1}
    p_win = np.clip(np.array(hits_per_period) / 6.0, 0.01, 0.99)
    q = 1 - p_win
    f_star = np.clip((p_win - q) / 1.0, 0, 0.25)
    
    final_values = []
    max_dds = []
    for _ in range(2000):
        capital = 10000
        peak = 10000
        max_dd = 0
        for f, p, qq in zip(f_star, p_win, 1 - p_win):
            bet = capital * f
            win = np.random.random() < p
            capital += bet if win else -bet
            peak = max(peak, capital)
            max_dd = max(max_dd, (peak - capital) / peak)
        final_values.append(capital)
        max_dds.append(max_dd)
    
    final_values = np.array(final_values)
    returns = (final_values - 10000) / 10000
    return {
        "roi": float(np.median(returns)),
        "ruin_prob": float((final_values < 5000).mean()),
        "sharpe": float(np.mean(returns) / (np.std(returns) + 1e-9)),
        "max_drawdown": float(np.median(max_dds))
    }


def compute_three_tier(checker: FormulaMatchChecker, formula: Any, use_walk_forward: bool = True) -> Dict:
    if use_walk_forward:
        wf = checker.walk_forward_check(formula, initial_window=200, step=20, test_size=10)
        if "error" in wf or wf.get("total_periods_checked", 0) == 0:
            return {"error": "walk_forward_failed"}
        hits_list = []
        for r in wf.get("round_results", []):
            if not r.get("error"):
                hits_list.extend(r["hits"])
        per_period_hits = hits_list
    else:
        report = checker.check_formula(formula)
        per_period_hits = report.get("per_period_hits", [])
    
    if not per_period_hits:
        return {"error": "no_hits_data"}
    
    n = len(per_period_hits)
    probs = np.array([h / 6.0 for h in per_period_hits for _ in range(h)]) if any(per_period_hits) else np.array([])
    outcomes = np.array([1]*sum(per_period_hits) + [0]*(6*n - sum(per_period_hits))) if n else np.array([])
    
    ece = expected_calibration_error(probs, outcomes) if len(probs) == len(outcomes) and len(probs) > 0 else 1.0
    p_val, effect = permutation_test(per_period_hits)
    kelly = kelly_simulation(per_period_hits)
    
    return {
        "ece": round(ece, 4),
        "p_value": round(p_val, 4),
        "effect_size": round(effect, 4),
        "kelly_roi": round(kelly["roi"], 4),
        "kelly_ruin": round(kelly["ruin_prob"], 4),
        "kelly_sharpe": round(kelly["sharpe"], 4),
        "max_drawdown": round(kelly["max_drawdown"], 4),
        "statistically_significant": p_val < 0.01 and effect > 0.15,
        "economically_viable": kelly["ruin_prob"] < 0.05 and kelly["sharpe"] > 0.5,
        "avg_hits": round(np.mean(per_period_hits), 4) if per_period_hits else 0,
        "beats_random": np.mean(per_period_hits) > RANDOM_EXPECTATION if per_period_hits else False,
    }