# -*- coding: utf-8 -*-
"""
First Principle: SSQ results ARE computable.
We need to find the RIGHT signal amplification mechanism.

Current problem: Individual primitives discriminate well but all converge to Brier≈0.172.
Hypothesis: The signal is in the INTERACTION between primitives, not in any single one.

Strategy:
1. Find which primitive combinations produce NON-REDUNDANT signals
2. Build an ensemble that maximizes signal diversity + calibration
3. Use mutual information instead of Brier to measure signal strength
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'E:/享中')
from data_layer import load_history
from formula_lang.primitive import get_default_primitives
from formula_lang.grammar import FormulaGrammar
from collections import Counter
import math

draws = load_history()
primitives = get_default_primitives()

print("=" * 80)
print("FIRST PRINCIPLE APPROACH: Finding computable structure in SSQ")
print("=" * 80)

# Step 1: Do primitives capture DIFFERENT signals?
print("\n[1] PRIMITIVE DIVERSITY ANALYSIS")
print("-" * 60)

def get_top5_scores(prim, draws):
    scores = prim.score_all(draws)
    return sorted(scores.items(), key=lambda x: -x[1])[:5]

# Check overlap of top-5 numbers across primitives
top5_sets = {}
for p in primitives:
    top5 = set(n for n, _ in get_top5_scores(p, draws[-500:]))
    top5_sets[p.name] = top5

# Pairwise Jaccard similarity
print("\nPairwise Top-5 overlap (Jaccard index):")
overlap_matrix = []
for i, p1 in enumerate(primitives[:10]):
    for j, p2 in enumerate(primitives[:10]):
        if i < j:
            s1 = top5_sets[p1.name]
            s2 = top5_sets[p2.name]
            jaccard = len(s1 & s2) / max(len(s1 | s2), 1)
            overlap_matrix.append((p1.name, p2.name, jaccard))

overlap_matrix.sort(key=lambda x: -x[2])
print(f"  Most overlapping pairs:")
for n1, n2, jac in overlap_matrix[:5]:
    print(f"    {n1} ∩ {n2}: {jac:.2f}")
print(f"  Least overlapping pairs:")
for n1, n2, jac in overlap_matrix[-5:]:
    print(f"    {n1} ∩ {n2}: {jac:.2f}")

avg_overlap = sum(x[2] for x in overlap_matrix) / len(overlap_matrix)
print(f"\n  Average Jaccard overlap: {avg_overlap:.3f}")
if avg_overlap > 0.5:
    print("  → Primitives are REDUNDANT (all see same signal)")
elif avg_overlap < 0.2:
    print("  → Primitives are DIVERSE (each sees different signal)")
else:
    print("  → Primitives have MODERATE diversity")

# Step 2: Do primitives PREDICT differently?
print("\n[2] PREDICTION DIVERGENCE ANALYSIS")
print("-" * 60)

# For each recent draw, check how many primitives agree on top picks
recent_draws = draws[-20:]
agreement_scores = []

for draw_idx, draw in enumerate(recent_draws[-5:]):
    actual = set(draw.reds)
    # Each primitive's top-5 prediction
    pred_by_prim = {}
    for p in primitives:
        scores = p.score_all(draws[:len(draws)-draw_idx-1])
        top5 = set(n for n, _ in sorted(scores.items(), key=lambda x: -x[1])[:5])
        pred_by_prim[p.name] = top5

    # How many primitives predict each number?
    vote_count = Counter()
    for name, preds in pred_by_prim.items():
        for n in preds:
            vote_count[n] += 1

    # Numbers with high votes = consensus predictions
    consensus = [(n, c) for n, c in vote_count.most_common()]
    consensus_set = {n for n, c in consensus if c >= 3}

    hits = len(consensus_set & actual)
    agreement_scores.append({
        'period': draw.period,
        'consensus_size': len(consensus_set),
        'hits': hits,
        'actual': actual,
    })

    print(f"  Period {draw.period}: actual={sorted(actual)}")
    print(f"    Consensus (≥3 prims agree): {sorted(consensus_set)} ({len(consensus_set)} nums)")
    print(f"    Hits: {hits}/6")

# Step 3: Signal amplification through voting
print("\n[3] SIGNAL AMPLIFICATION VIA CONSENSUS VOTING")
print("-" * 60)

# Walk-forward: for each test period, build predictions from voting
# Then compare hit rates at different voting thresholds
from collections import defaultdict

results_by_threshold = defaultdict(list)

for i in range(500, len(draws) - 10, 50):
    train = draws[:i]
    test = draws[i:i+10]

    for draw in test:
        actual = set(draw.reds)
        vote_count = Counter()

        for p in primitives:
            scores = p.score_all(train)
            # Get top-K from each primitive (K varies)
            sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
            for k in [3, 5, 6, 8, 10]:
                top_k = set(n for n, _ in sorted_scores[:k])
                for n in top_k:
                    vote_count[n] += 1

        # Try different voting thresholds
        for threshold in [1, 2, 3, 4, 5, 6, 8, 10]:
            consensus = [n for n, c in vote_count.most_common() if c >= threshold]
            # Take top 6 from consensus
            candidates = [n for n, _ in vote_count.most_common() if _ >= threshold][:6]
            hits = len(set(candidates) & actual)
            results_by_threshold[threshold].append(hits)

print(f"{'Threshold':>10} {'Avg Hits':>10} {'Std':>8} {'Max':>5} {'Min':>5} {'>2 hits':>10}")
print("-" * 60)
for thresh in sorted(results_by_threshold.keys()):
    hits_list = results_by_threshold[thresh]
    if not hits_list:
        continue
    avg_h = sum(hits_list) / len(hits_list)
    std_h = (sum((h - avg_h)**2 for h in hits_list) / len(hits_list))**0.5
    over2 = sum(1 for h in hits_list if h > 2)
    print(f"  {thresh:>8}   {avg_h:>10.3f} {std_h:>8.3f} {max(hits_list):>5} {min(hits_list):>5} {over2:>10}/{len(hits_list)}")

# Step 4: Optimal threshold analysis
print("\n[4] OPTIMAL VOTING THRESHOLD")
print("-" * 60)

best_thresh = None
best_score = -999

for thresh, hits_list in results_by_threshold.items():
    if not hits_list:
        continue
    avg_h = sum(hits_list) / len(hits_list)
    std_h = (sum((h - avg_h)**2 for h in hits_list) / len(hits_list))**0.5
    # Score = avg - std (higher is better: high mean, low variance)
    score = avg_h - std_h
    over2_pct = sum(1 for h in hits_list if h > 2) / len(hits_list)

    print(f"  Threshold {thresh:>2}: avg_hits={avg_h:.3f}, std={std_h:.3f}, "
          f"score={score:.3f}, >2 hits={over2_pct:.1%}")

    if score > best_score:
        best_score = score
        best_thresh = thresh

print(f"\n  Best threshold: {best_thresh} (score={best_score:.3f})")

# Step 5: Compare with random baseline
print("\n[5] vs RANDOM BASELINE")
print("-" * 60)

# Random baseline: pick 6 numbers uniformly, expected hits = 6*6/33 ≈ 1.09
random_expected = 6 * 6 / 33
print(f"  Random expected hits: {random_expected:.2f}/6")

# What does our best voting strategy achieve?
if best_thresh and results_by_threshold[best_thresh]:
    best_avg = sum(results_by_threshold[best_thresh]) / len(results_by_threshold[best_thresh])
    improvement = best_avg - random_expected
    print(f"  Best voting threshold {best_thresh}: avg={best_avg:.2f}")
    print(f"  Improvement over random: +{improvement:.2f}")
    if improvement > 0.3:
        print("  → SIGNIFICANT signal detected!")
    elif improvement > 0:
        print("  → Small positive signal")
    else:
        print("  → No improvement over random")
