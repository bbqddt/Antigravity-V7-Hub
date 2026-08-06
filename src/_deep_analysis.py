# -*- coding: utf-8 -*-
"""Deep analysis: Why are all primitives/formulas giving identical Brier scores?"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'E:/享中')
from data_layer import load_history
from formula_lang.primitive import get_default_primitives
from formula_lang.grammar import FormulaGrammar

draws = load_history()
primitives = get_default_primitives()

# Test: do different primitives give different scores?
print("=== Score Distribution Analysis ===\n")
print(f"{'Primitive':<35} {'Min':>8} {'Max':>8} {'Mean':>8} {'Std':>8} {'Unique':>8}")
print("-" * 80)

for prim in primitives[:10]:
    scores = prim.score_all(draws[-500:])
    vals = list(scores.values())
    unique = len(set(round(v, 6) for v in vals))
    print(f"{prim.name:<35} {min(vals):>8.4f} {max(vals):>8.4f} {sum(vals)/len(vals):>8.4f} {(__import__('math').sqrt(sum((v-sum(vals)/len(vals))**2 for v in vals)/len(vals))):>8.4f} {unique:>8}")

# Check: are all primitives outputting near-uniform scores?
print("\n=== Are primitives actually discriminating? ===\n")
for prim in primitives[:5]:
    scores = prim.score_all(draws[-500:])
    vals = sorted(scores.items(), key=lambda x: -x[1])
    top6 = vals[:6]
    bot6 = vals[-6:]
    print(f"\n{prim.name}:")
    print(f"  Top-6: {[(n, round(s, 4)) for n,s in top6]}")
    print(f"  Bot-6: {[(n, round(s, 4)) for n,s in bot6]}")
    print(f"  Range: {max(scores.values()) - min(scores.values()):.4f}")

# Check: what does the evaluator's _scores_to_probs do?
print("\n=== Evaluator Temperature Analysis ===\n")
import math

# Simulate what happens when we convert scores to probs
for prim in primitives[:3]:
    scores = prim.score_all(draws[-500:])
    min_s = min(scores.values())
    max_s = max(scores.values())
    score_range = max_s - min_s

    # Adaptive temperature
    if score_range < 0.01:
        temp = 0.05
    elif score_range < 0.1:
        temp = 0.2
    elif score_range < 1.0:
        temp = 0.5
    else:
        temp = 2.0

    shifted = {k: max(v - min_s + 0.001, 0.001) for k, v in scores.items()}
    log_scores = {k: math.log(v) / temp for k, v in shifted.items()}
    max_log = max(log_scores.values())
    exp_scores = {k: math.exp(v - max_log) for k, v in log_scores.items()}
    total = sum(exp_scores.values())
    probs = {k: v/total for k, v in exp_scores.items()}

    prob_vals = sorted(probs.values(), reverse=True)
    ent = -sum(p*math.log(max(p, 1e-10)) for p in probs.values()) / math.log(33)

    print(f"{prim.name}:")
    print(f"  Score range: {score_range:.6f} -> temperature: {temp}")
    print(f"  Probs Top-6: {[round(p, 4) for p in prob_vals[:6]]}")
    print(f"  Probs Bot-6: {[round(p, 4) for p in prob_vals[-6:]]}")
    print(f"  Entropy: {ent:.4f} (1.0 = uniform)")
    print(f"  Max prob: {max(probs.values()):.4f}, Min prob: {min(probs.values()):.6f}")
    print()

# Check: what about LuckcastV15 predictions?
print("=== LuckcastV15 Score Distribution ===\n")
try:
    from luckcast_antigravity_v1 import rank_candidates
    last_500 = draws[-500:]
    pool = rank_candidates(last_500, n_candidates=1000, top_k=5)
    print(f"Generated {len(pool)} prediction groups")

    # Analyze scores
    all_scores = []
    for g in pool:
        if isinstance(g, dict):
            sc = g.get("scores", {}).get("total_score", 0.5)
        else:
            sc = float(g[2]) if not isinstance(g[2], dict) else g[2].get("total_score", 0.5)
        all_scores.append(sc)

    import statistics
    print(f"Score stats: mean={statistics.mean(all_scores):.4f}, "
          f"stdev={statistics.stdev(all_scores):.4f}, "
          f"min={min(all_scores):.4f}, max={max(all_scores):.4f}")
    print(f"Score range: {max(all_scores)-min(all_scores):.4f}")

    # What does predictions_to_probs do with these scores?
    from walkforward_backtest_v3 import predictions_to_probs
    probs = predictions_to_probs(pool[:5], temperature=2.0)
    prob_vals = sorted(probs.values(), reverse=True)
    ent = -sum(p*math.log(max(p, 1e-10)) for p in probs.values()) / math.log(33)
    print(f"\nWith T=2.0: entropy={ent:.4f}, max_prob={max(probs.values()):.4f}")

    probs05 = predictions_to_probs(pool[:5], temperature=0.5)
    prob_vals05 = sorted(probs05.values(), reverse=True)
    ent05 = -sum(p*math.log(max(p, 1e-10)) for p in probs05.values()) / math.log(33)
    print(f"With T=0.5: entropy={ent05:.4f}, max_prob={max(probs05.values()):.4f}")

except Exception as e:
    print(f"Error: {e}")
