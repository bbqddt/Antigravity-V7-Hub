# -*- coding: utf-8 -*-
"""
Deep diagnosis of Multi-AI Evolution Engine V19 results
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json

# Load results
with open('E:/享中/evolution_results_v19.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

with open('E:/享中/multi_ai_analysis.json', 'r', encoding='utf-8') as f:
    ai_analysis = json.load(f)

print("=" * 80)
print("MULTI-AI EVOLUTION ENGINE V19 — DEEP DIAGNOSIS")
print("=" * 80)

# ─── 1. AI Model Performance ───
print("\n[1] AI MODEL PREDICTION ANALYSIS")
print("-" * 60)

predictions = ai_analysis['predictions']
for model, preds in predictions.items():
    print(f"  {model:<30}: {preds}")

# Cross-model consensus
consensus = {}
all_nums = set()
for preds in predictions.values():
    all_nums.update(preds)

for n in sorted(all_nums):
    count = sum(1 for preds in predictions.values() if n in preds)
    if count >= 2:
        consensus[n] = count

print(f"\n  Cross-model consensus (≥2 models agree):")
for n, c in sorted(consensus.items(), key=lambda x: -x[1]):
    print(f"    Number {n:>2}: agreed by {c}/4 models")

# Key insight: 24 agreed by ALL 4 models
if 24 in consensus and consensus[24] == 4:
    print(f"\n  ⭐ NUMBER 24: UNANIMOUS CONSENSUS (4/4 models)")
    print(f"     This is the strongest signal from multi-AI collaboration")

# ─── 2. Evolution Convergence Analysis ───
print("\n[2] EVOLUTION CONVERGENCE ANALYSIS")
print("-" * 60)

history = results['history']
best_fitness = [h['best_fitness'] for h in history]
best_avg = [h['best_avg_hits'] for h in history]

print(f"  Generation 1: fitness={best_fitness[0]:.3f}, avg_hits={best_avg[0]:.2f}")
print(f"  Generation 10: fitness={best_fitness[9]:.3f}, avg_hits={best_avg[9]:.2f}")
print(f"  Generation 25: fitness={best_fitness[24]:.3f}, avg_hits={best_avg[24]:.2f}")
print(f"  Generation 50: fitness={best_fitness[-1]:.3f}, avg_hits={best_avg[-1]:.2f}")

# When did convergence happen?
convergence_gen = 1
for i in range(1, len(best_fitness)):
    if abs(best_fitness[i] - best_fitness[i-1]) < 0.001:
        convergence_gen = i + 1
        break

print(f"\n  Convergence at generation: {convergence_gen}")
improvement_pct = (best_fitness[-1] - best_fitness[0]) / best_fitness[0] * 100
print(f"  Total improvement: {improvement_pct:.1f}%")

if improvement_pct < 5:
    print(f"  ⚠️  Low improvement → evolution space is flat")
    print(f"     Most formulas perform similarly → no clear signal to optimize")

# ─── 3. Hit Rate vs Random Baseline ───
print("\n[3] HIT RATE ANALYSIS")
print("-" * 60)

random_baseline_per_window = 1.09 * 10 / 10  # 1.09 per 10-period window
best_avg_hits = best_avg[-1]
print(f"  Random baseline: {random_baseline_per_window:.2f} hits/window")
print(f"  Best formula: {best_avg_hits:.2f} hits/window")
print(f"  Delta: {best_avg_hits - random_baseline_per_window:+.2f}")

if best_avg_hits > random_baseline_per_window * 1.1:
    print(f"  ✅ Better than random!")
elif best_avg_hits > random_baseline_per_window:
    print(f"  ⚠️  Slightly above random (may be selection effect)")
else:
    print(f"  ❌ Worse than random")

# ─── 4. Formula Structure Analysis ───
print("\n[4] BEST FORMULA STRUCTURE")
print("-" * 60)

best_formula = results.get('best_formula', {})
print(f"  Name: {best_formula.get('name', '?')}")
print(f"  Source: {best_formula.get('source', '?')}")
print(f"  Operators: {best_formula.get('operators', [])}")
print(f"  Primitives: {best_formula.get('primitive_names', [])}")

# ─── 5. Core Problems Identified ───
print("\n[5] ROOT CAUSES IDENTIFIED")
print("-" * 60)

problems = []

# Problem 1: LLM models failed
llm_models = ['gemma4', 'gemma2', 'openrouter_qwen']
used_models = list(predictions.keys())
failed_llms = [m for m in llm_models if m not in used_models]
if failed_llms:
    problems.append((
        "LLM模型未接入",
        f"{', '.join(failed_llms)} 未能输出有效号码 → 只有4个引擎参与，缺少LLM的深度推理"
    ))

# Problem 2: Evolution converges too fast
if improvement_pct < 5:
    problems.append((
        "进化空间平坦",
        "所有公式的命中率都接近随机基线 → 没有明确的优化方向可走"
    ))

# Problem 3: Formula structure is weak
if best_formula.get('primitive_names'):
    n_prims = len(best_formula['primitive_names'])
    if n_prims <= 2:
        problems.append((
            "公式过于简单",
            f"最佳公式只用了{n_prims}个原语 → 可能不足以捕捉复杂模式"
        ))

# Problem 4: Last draw hit rate
final_pred = [2, 3, 14, 20, 26, 30]  # from output
actual_last = [6, 10, 12, 15, 24, 27]
hits_last = len(set(final_pred) & set(actual_last))
problems.append((
    "最后一期命中为0",
    f"预测{final_pred} vs 实际{actual_last} → 0/6命中"
))

for title, desc in problems:
    print(f"  ❌ {title}")
    print(f"     {desc}")

# ─── 6. Recommendations ───
print("\n[6] RECOMMENDATIONS")
print("-" * 60)

recommendations = [
    ("修复LLM集成", "Gemma4/Gemma2/OpenRouter的号码解析逻辑有bug，需要修复prompt和解析器"),
    ("增加公式复杂度", "允许3-5个原语的组合，而不是2个。复杂模式需要更多原语协同"),
    ("改变评估策略", "当前walk-forward窗口太小(10期)，改为20期或30期测试"),
    ("引入LSTM/时序模型", "用RNN/LSTM捕捉时间序列中的短期依赖关系"),
    ("强化共识机制", "24号被4个模型一致推荐，应该给共识号码更高的权重"),
    ("多目标优化", "同时优化命中率和稳定性，避免过度追求单指标"),
]

for i, (title, desc) in enumerate(recommendations, 1):
    print(f"  {i}. {title}")
    print(f"     {desc}")

print(f"\n{'='*80}")
print(f"CONCLUSION:")
print(f"  系统有7种AI计算能力，但实际只有4种参与。")
print(f"  即使全部7种参与，由于数据本质上是随机的，")
print(f"  任何算法都无法持续超越随机基线。")
print(f"  但共识号码24是一个有趣的现象——值得追踪。")
print(f"{'='*80}")
