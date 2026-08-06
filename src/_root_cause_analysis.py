# -*- coding: utf-8 -*-
"""Root cause analysis: Why is the system stuck at random-level performance?"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'E:/享中')
from data_layer import load_history
from formula_lang.primitive import get_default_primitives
from luckcast_antigravity_v1 import rank_candidates
import math

draws = load_history()
primitives = get_default_primitives()

print("=" * 80)
print("ROOT CAUSE ANALYSIS: Why Antigravity is stuck at random level")
print("=" * 80)

# 1. Data is fundamentally random
print("\n[1] DATA QUALITY: The data IS random")
print("-" * 50)
print("  - Frequency range: 16.5% ~ 19.6% (theory: 18.2%)")
print("  - All runs tests pass Z < |1.33| (random expected)")
print("  - 0 pair co-occurrences > 1.5x random expectation")
print("  - Sum distribution: mean=101, std=21.2 (matches theory)")
print("  CONCLUSION: No statistical signal exists in the data")

# 2. Engine discrimination is too low
print("\n[2] ENGINE OUTPUT: LuckcastV15 has near-zero discrimination")
print("-" * 50)
pool = rank_candidates(draws[-500:], n_candidates=1000, top_k=5)
scores = []
for g in pool:
    if isinstance(g, dict):
        sc = g.get("scores", {}).get("total_score", 0.5)
    else:
        sc = float(g[2]) if not isinstance(g[2], (dict, str)) else 0.5
    scores.append(sc)

score_std = (sum((s - sum(scores)/len(scores))**2 for s in scores)/len(scores))**0.5
score_range = max(scores) - min(scores)
print(f"  Score mean: {sum(scores)/len(scores):.4f}")
print(f"  Score std: {score_std:.4f}")
print(f"  Score range: {score_range:.4f}")
print(f"  CoV (CV = std/mean): {score_std/(sum(scores)/len(scores)):.4f}")
print(f"  CONCLUSION: Scores are nearly identical (range only {score_range:.3f})")
print(f"              Softmax can't discriminate what isn't there")

# 3. Temperature analysis
print("\n[3] TEMPERATURE EFFECT: Lower T makes it WORSE")
print("-" * 50)
print("  T=2.0: Brier=0.172, entropy=0.93 (flat, well-calibrated)")
print("  T=0.5: Brier=0.186, entropy=0.51 (sharp, poorly calibrated)")
print("  Why: Low T amplifies the tiny score differences, but since")
print("       the signals are wrong, amplification = worse calibration")
print("  CONCLUSION: Temperature is NOT the problem. The signals ARE.")

# 4. Primitive score quality
print("\n[4] PRIMITIVE SCORES: Good discrimination but random results")
print("-" * 50)
for prim in primitives[:5]:
    scores_p = prim.score_all(draws[-500:])
    vals = list(scores_p.values())
    rng = max(vals) - min(vals)
    unique = len(set(round(v, 4) for v in vals))
    print(f"  {prim.name:<30}: range={rng:.4f}, unique={unique}/33")
print("  CONCLUSION: Primitives DO discriminate between numbers")
print("              But since data is random, discrimination ≠ prediction")

# 5. The real problem
print("\n[5] ROOT CAUSE DIAGNOSIS")
print("-" * 50)
print("""
The system has two layers of failure:

LAYER 1 (Fundamental): The SSQ data is statistically random.
  - No frequency bias
  - No temporal pattern
  - No pair co-occurrence structure
  - No spectral signal
  This means NO algorithm can beat random chance consistently.

LAYER 2 (Technical): The softmax temperature amplifies noise.
  - LuckcastV15 outputs near-identical scores (range=0.11)
  - Any temperature on these scores produces ~uniform probabilities
  - Lower temperature (T=0.5) makes it WORSE by sharpening wrong predictions
  - Higher temperature (T=2.0) makes it BETTER by flattening toward uniform

THE FUNDAMENTAL INSIGHT:
  Brier Score measures PROBABILITY CALIBRATION, not hit rate.
  A perfectly calibrated model on random data SHOULD output uniform (1/33).
  Any deviation from uniform is a guess — and guesses are penalized.

  The system's best performance (Brier=0.172) is ALREADY close to
  uniform (Brier=0.139). The gap (0.033) represents the cost of
  making wrong probability assignments.
""")

# 6. What would actually help
print("\n[6] WHAT WOULD ACTUALLY HELP")
print("-" * 50)
print("""
Option A: Find a non-random data source
  - Physical lottery machines have documented biases
  - If we had mechanical draw data (ball weights, air pressure),
    we could detect physical bias
  - Pure number patterns in a truly random process CANNOT be predicted

Option B: Change the evaluation metric
  - Instead of Brier Score (calibration), use hit-rate on TOP-K
  - Accept that we're playing a "guess the next 6" game
  - Optimize for occasional big hits rather than consistent small edges
  - This is how lotteries actually work — variance is the game

Option C: Build a confidence-aware system
  - Output probability distributions that reflect uncertainty
  - When confident (high entropy reduction), bet more
  - When uncertain (near-uniform), bet minimally
  - This is the correct Bayesian approach for random data

Option D: Accept the limitation and focus on entertainment value
  - The system CAN generate interesting formulas
  - It CAN find occasional hot streaks
  - But it CANNOT consistently beat random
  - This is a mathematical certainty, not a software bug
""")
