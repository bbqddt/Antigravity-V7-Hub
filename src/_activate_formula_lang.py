# -*- coding: utf-8 -*-
"""Activate formula_lang primitives: create formulas, evaluate with V3"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'E:/享中')
from data_layer import load_history
from formula_lang.primitive import get_default_primitives, Primitive
from formula_lang.grammar import Formula, FormulaGrammar
from formula_lang.evaluator_v3 import FormulaEvaluatorV3
import json

print("Loading history...")
draws = load_history()
print(f"Loaded {len(draws)} draws")

# Create all default primitives
print("\nCreating 33 primitives...")
primitives = get_default_primitives()
print(f"Created {len(primitives)} primitives")

# Show categories
cats = {}
for p in primitives:
    cats.setdefault(p.category, []).append(p.name)
for cat, names in sorted(cats.items()):
    print(f"  {cat}: {len(names)} primitives")

# Evaluate each primitive individually with V3
print("\n=== Evaluating individual primitives with V3 (Brier Score) ===")
evaluator = FormulaEvaluatorV3()

results = {}
for prim in primitives:
    try:
        res = evaluator.evaluate(prim, draws, n_windows=30, window_size=500, step=50)
        results[prim.name] = {
            "category": prim.category,
            "red_brier": res["red_brier"],
            "beats_random": res["beats_random"],
            "stability_std": res["stability_std"],
            "generalization_gap": res["generalization_gap"],
            "overfitting_risk": res["overfitting_risk"],
            "rounds": res["rounds"],
        }
    except Exception as e:
        results[prim.name] = {"error": str(e), "category": prim.category}

# Sort by Brier score (lower is better)
sorted_results = sorted(
    [(name, r) for name, r in results.items() if "error" not in r],
    key=lambda x: x[1]["red_brier"]
)

print(f"\n{'Rank':<5} {'Name':<35} {'Category':<15} {'Red Brier':>10} {'Beats Rand':>10} {'Stability':>10}")
print("-" * 90)
for i, (name, r) in enumerate(sorted_results[:20]):
    beats = "YES" if r["beats_random"] else "no"
    print(f"{i+1:<5} {name:<35} {r['category']:<15} {r['red_brier']:>10.6f} {beats:>10} {r['stability_std']:>10.6f}")

# Save results
with open('E:/享中/primitive_evaluation_v3.json', 'w', encoding='utf-8') as f:
    json.dump({"results": dict(sorted_results), "total": len(sorted_results)}, f, ensure_ascii=False, indent=2)
print(f"\nSaved to primitive_evaluation_v3.json")

# Now create formula combinations using Grammar
print("\n=== Creating formula combinations ===")
formulas = []

# Resonance formulas (multiply scores - best for finding convergent signals)
for i in range(len(primitives)):
    for j in range(i+1, len(primitives)):
        if primitives[i].category == primitives[j].category:
            f = FormulaGrammar.resonance([primitives[i], primitives[j]],
                                         name=f"res_{primitives[i].name}_x_{primitives[j].name}")
            formulas.append(f)

# Weighted sum formulas (linear combination)
for i in range(len(primitives)):
    for j in range(i+1, len(primitives)):
        f = FormulaGrammar.weighted_sum([primitives[i], primitives[j]],
                                        name=f"wsum_{primitives[i].name}_x_{primitives[j].name}")
        formulas.append(f)

# Cross-category resonance (more interesting)
cross_cats = list(cats.keys())
for i in range(len(cross_cats)):
    for j in range(i+1, min(i+3, len(cross_cats))):
        cat_prims_i = [p for p in primitives if p.category == cross_cats[i]]
        cat_prims_j = [p for p in primitives if p.category == cross_cats[j]]
        if cat_prims_i and cat_prims_j:
            p1 = cat_prims_i[0]
            p2 = cat_prims_j[0]
            f = FormulaGrammar.resonance([p1, p2],
                                         name=f"xcat_res_{p1.name}_x_{p2.name}")
            formulas.append(f)

print(f"Created {len(formulas)} formula combinations")

# Evaluate top formulas (sample 200 to save time)
print("\n=== Evaluating top formula combinations (sample of 200) ===")
import random
random.seed(42)
sampled = random.sample(formulas, min(200, len(formulas)))

formula_results = {}
for f in sampled:
    try:
        res = evaluator.evaluate(f, draws, n_windows=30, window_size=500, step=50)
        formula_results[f.name] = {
            "red_brier": res["red_brier"],
            "beats_random": res["beats_random"],
            "stability_std": res["stability_std"],
            "generalization_gap": res["generalization_gap"],
            "overfitting_risk": res["overfitting_risk"],
            "rounds": res["rounds"],
        }
    except Exception as e:
        formula_results[f.name] = {"error": str(e)}

# Sort by Brier
sorted_formulas = sorted(
    [(name, r) for name, r in formula_results.items() if "error" not in r],
    key=lambda x: x[1]["red_brier"]
)

print(f"\nTop-20 formulas by Brier Score:")
print(f"{'Rank':<5} {'Formula Name':<50} {'Red Brier':>10} {'Beats Rand':>10} {'Risk':>10}")
print("-" * 100)
for i, (name, r) in enumerate(sorted_formulas[:20]):
    beats = "YES" if r["beats_random"] else "no"
    print(f"{i+1:<5} {name:<50} {r['red_brier']:>10.6f} {beats:>10} {r['overfitting_risk']:>10}")

# Count survivors
survivors = [name for name, r in sorted_formulas if r["beats_random"]]
print(f"\nSurvivors (beats random): {len(survivors)}/{len(sorted_formulas)}")

# Save
with open('E:/享中/formula_combinations_v3.json', 'w', encoding='utf-8') as f:
    json.dump({
        "top_formulas": [(n, r) for n, r in sorted_formulas[:50]],
        "survivor_count": len(survivors),
        "total_evaluated": len(sorted_formulas),
    }, f, ensure_ascii=False, indent=2)
print(f"Saved to formula_combinations_v3.json")
