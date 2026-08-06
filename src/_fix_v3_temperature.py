# -*- coding: utf-8 -*-
"""Fix V3 backtest: lower softmax temperature from T=2.0 to T=0.5"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Patch predictions_to_probs to use T=0.5 instead of T=2.0
import math
from collections import defaultdict

def predictions_to_probs_fixed(predictions, temperature=0.5):
    """Fixed version with lower temperature for better discrimination."""
    if not predictions:
        return {n: 1.0/33.0 for n in range(1, 34)}

    raw_scores = defaultdict(float)
    base_score = 0.01

    for idx, pred in enumerate(predictions):
        reds = pred["reds"]
        score = pred.get("scores", {})
        if isinstance(score, dict):
            group_score = score.get("total_score", 0.5)
        else:
            group_score = float(score)

        rank_decay = 1.0 / (idx + 1)
        for n in reds:
            raw_scores[n] += group_score * rank_decay

    max_val = max(raw_scores.values()) if raw_scores else 0
    exp_scores = {}
    for n in range(1, 34):
        s = raw_scores.get(n, base_score)
        exp_scores[n] = math.exp((s - max_val) / temperature)

    total = sum(exp_scores.values())
    return {n: v/total for n, v in exp_scores.items()}


# Now patch the module and run
sys.path.insert(0, 'E:/享中')
from data_layer import load_history
from walkforward_backtest_v3 import (
    walk_forward_backtest_v3, generate_engine_predictions,
    compute_brier_from_predictions, collide
)

print("Loading history...")
draws = load_history()
print(f"Loaded {len(draws)} draws")

# Quick test: compare T=2.0 vs T=0.5 on last few draws
print("\n=== Temperature comparison on last 10 draws ===")
for offset in [10, 20, 30, 50, 100]:
    if offset >= len(draws):
        continue
    train_data = draws[:len(draws)-offset]
    test_draw = draws[len(draws)-offset]

    preds = generate_engine_predictions(train_data, top_k=5)
    if not preds:
        print(f"  Period {test_draw.period}: No predictions available")
        continue

    probs_t2 = predictions_to_probs_fixed(preds, temperature=2.0)
    probs_t05 = predictions_to_probs_fixed(preds, temperature=0.5)

    # Brier scores
    actual_reds = set(test_draw.reds)
    brier_t2 = sum((probs_t2[n] - (1 if n in actual_reds else 0))**2 for n in range(1,34))/33
    brier_t05 = sum((probs_t05[n] - (1 if n in actual_reds else 0))**2 for n in range(1,34))/33

    # Entropy (discrimination measure)
    ent_t2 = -sum(p*math.log(max(p,1e-10)) for p in probs_t2.values())/math.log(33)
    ent_t05 = -sum(p*math.log(max(p,1e-10)) for p in probs_t05.values())/math.log(33)

    # Top-6 prediction
    top6_t05 = sorted(probs_t05.items(), key=lambda x:-x[1])[:6]
    hits = sum(1 for n,_ in top6_t05 if n in actual_reds)

    print(f"  Period {test_draw.period}: Brier(T=2.0)={brier_t2:.4f} vs Brier(T=0.5)={brier_t05:.4f}, "
          f"Entropy(T=2.0)={ent_t2:.4f} vs Entropy(T=0.5)={ent_t05:.4f}, "
          f"Top6_hits={hits}/6")

print("\n=== Rerunning full backtest with T=0.5 ===")

# Monkey-patch the module's predictions_to_probs
import walkforward_backtest_v3 as wbv3
wbv3.predictions_to_probs = lambda preds, temp=0.5: predictions_to_probs_fixed(preds, temp)

result = walk_forward_backtest_v3(draws, initial_window=500, top_k=5, n_rounds=50)

# Print summary
eng = result.engine
rnd = result.random_baseline
stats = result.statistical_summary

print(f"\n{'='*72}")
print(f"  V3 Backtest Results (T=0.5)")
print(f"{'='*72}")
print(f"\nEngine:")
print(f"  avg_red_hits: {eng['avg_red_hits']:.2f} (std={eng['std_red_hits']:.2f})")
print(f"  blue_hit_rate: {eng['blue_hit_rate']:.2%}")
print(f"  avg_red_brier: {eng['avg_red_brier']:.4f} (baseline=0.139)")
print(f"\nRandom baseline:")
print(f"  avg_red_hits: {rnd['avg_red_hits']:.2f} (std={rnd['std_red_hits']:.2f})")
print(f"\nStatistics:")
print(f"  mean_p_value: {stats['mean_p_value']:.4f}")
print(f"  brier_vs_random_ratio: {stats['brier_vs_random_ratio']:.4f}")
print(f"  wins_over_random: {stats['wins_over_random']}/{eng['rounds']}")
print(f"  significant_rounds: {stats['p_value_significant']:.2%}")

diff = eng['avg_red_hits'] - rnd['avg_red_hits']
print(f"\nComparison: Engine vs Random = {diff:+.2f}")
if stats['brier_vs_random_ratio'] < 1.0:
    print("  RESULT: Better than random! (Brier ratio < 1.0)")
else:
    print("  RESULT: Worse than or equal to random")

# Save results
import json
output = {
    "engine": eng,
    "random_baseline": rnd,
    "statistical_summary": stats,
    "config": result.config,
    "rounds": [{"period": r.period, "red_hits": r.engine_red_hits,
                "red_brier": r.red_brier, "p_value": r.random_p_value} for r in result.rounds],
    "formula_performance": result.formula_performance,
    "temperature": 0.5,
}
with open('E:/享中/v3_results_T0.5.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\nResults saved to v3_results_T0.5.json")
