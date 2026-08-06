# -*- coding: utf-8 -*-
"""Build formula vault: auto-generate quality formulas with walk-forward screening"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'E:/享中')
from data_layer import load_history
from formula_lang.primitive import get_default_primitives
from formula_lang.grammar import Formula, FormulaGrammar
from formula_lang.evaluator_v3 import FormulaEvaluatorV3
from formula_lang.mutator import PrimitiveMutator
import json, random, math
from collections import Counter

print("Loading history...")
draws = load_history()
print(f"Loaded {len(draws)} draws")

primitives = get_default_primitives()
print(f"Using {len(primitives)} primitives")

evaluator = FormulaEvaluatorV3()
rng = random.Random(42)

# Phase 1: Generate initial formula vault
print("\n=== Phase 1: Generate initial formula vault ===")

def generate_formula_vault(primitives, n_per_combo=10, rng=None):
    """Generate diverse formula combinations."""
    formulas = []
    names = {}

    # 1) 2-primitive resonance within same category
    by_cat = {}
    for p in primitives:
        by_cat.setdefault(p.category, []).append(p)

    for cat, prims in by_cat.items():
        if len(prims) < 2:
            continue
        for _ in range(n_per_combo // 3):
            p1, p2 = rng.sample(prims, 2)
            w = [rng.uniform(0.3, 0.7), 1.0]
            w[0] /= sum(w)
            f = FormulaGrammar.resonance([p1, p2], weights=w,
                                         name=f"vault_res_{p1.name}_{p2.name}")
            formulas.append(f)

        # weighted sums too
        for _ in range(n_per_combo // 3):
            p1, p2 = rng.sample(prims, 2)
            f = FormulaGrammar.weighted_sum([p1, p2], name=f"vault_wsum_{p1.name}_{p2.name}")
            formulas.append(f)

    # 2) Cross-category resonance
    cats = list(by_cat.keys())
    for _ in range(n_per_combo):
        c1, c2 = rng.sample(cats, 2)
        p1 = rng.choice(by_cat[c1])
        p2 = rng.choice(by_cat[c2])
        f = FormulaGrammar.resonance([p1, p2], name=f"vault_xcat_{p1.name}_{p2.name}")
        formulas.append(f)

    # 3) 3-primitive cascade
    for _ in range(n_per_combo // 2):
        subset = rng.sample(primitives, min(3, len(primitives)))
        f = FormulaGrammar.cascade(subset, name=f"vault_cascade_{'_'.join(p.name for p in subset[:3])}")
        formulas.append(f)

    # 4) 4-primitive phase alignment
    for _ in range(n_per_combo // 2):
        subset = rng.sample(primitives, min(4, len(primitives)))
        f = FormulaGrammar.phase_align(subset, name=f"vault_phase_{'_'.join(p.name for p in subset[:4])}")
        formulas.append(f)

    return formulas

vault = generate_formula_vault(primitives, n_per_combo=30, rng=rng)
print(f"Generated {len(vault)} formulas")

# Phase 2: Walk-forward screening — evaluate all formulas
print(f"\n=== Phase 2: Walk-forward screening ({len(vault)} formulas) ===")
screening_results = {}
survivors = []
eliminated = []

for i, f in enumerate(vault):
    if (i + 1) % 50 == 0:
        print(f"  Evaluated {i+1}/{len(vault)} formulas...")

    try:
        res = evaluator.evaluate(f, draws, n_windows=30, window_size=500, step=50)
        screening_results[f.name] = res

        if res["beats_random"]:
            survivors.append({
                "name": f.name,
                "red_brier": res["red_brier"],
                "blue_hit_rate": res["blue_hit_rate"],
                "stability_std": res["stability_std"],
                "generalization_gap": res["generalization_gap"],
                "overfitting_risk": res["overfitting_risk"],
                "rounds": res["rounds"],
            })
        else:
            eliminated.append(f.name)
    except Exception as e:
        screening_results[f.name] = {"error": str(e)}

print(f"  Screening complete!")
print(f"  Survivors: {len(survivors)}")
print(f"  Eliminated: {len(eliminated)}")
print(f"  Survival rate: {len(survivors)/max(len(screening_results),1)*100:.1f}%")

# Phase 3: Evolve top formulas
print(f"\n=== Phase 3: Evolve top formulas ===")
mutator = PrimitiveMutator()

# Take top-10 survivors for evolution
survivors.sort(key=lambda x: x["red_brier"])
top10 = survivors[:min(10, len(survivors))]

print(f"Evolving top {len(top10)} formulas...")

evolved_results = []
for i, surv in enumerate(top10):
    # Find the formula object
    target_name = surv["name"]
    target_formula = None
    for f in vault:
        if f.name == target_name:
            target_formula = f
            break

    if not target_formula:
        continue

    print(f"  Evolving {target_name}...")

    # Mutate primitives in the formula
    for gen in range(3):
        new_prims = []
        for p in target_formula.primitives:
            if rng.random() < 0.3:
                mutated = mutator.mutate(p, draws, rng, generation=gen)
                new_prims.append(mutated)
            else:
                new_prims.append(p)

        # Recreate formula with same operator
        new_formula = Formula(
            name=f"{target_name}_gen{gen}",
            primitives=new_prims,
            operators=target_formula.operators[:],
            parameters=dict(target_formula.parameters)
        )

        # Evaluate
        try:
            res = evaluator.evaluate(new_formula, draws, n_windows=30, window_size=500, step=50)
            evolved_results.append({
                "parent": target_name,
                "generation": gen,
                "name": new_formula.name,
                "red_brier": res["red_brier"],
                "beats_random": res["beats_random"],
                "stability_std": res["stability_std"],
                "generalization_gap": res["generalization_gap"],
                "overfitting_risk": res["overfitting_risk"],
            })

            if res["red_brier"] < surv["red_brier"]:
                # Improvement! Use this as new parent
                target_formula = new_formula
                surv = evolved_results[-1]
                print(f"    Gen {gen}: IMPROVED! Brier {res['red_brier']:.6f} (was {surv.get('prev_brier', '?')})")
            else:
                print(f"    Gen {gen}: Brier {res['red_brier']:.6f}")
        except Exception as e:
            print(f"    Gen {gen}: Error - {e}")

# Phase 4: Final ranking and export
print(f"\n=== Phase 4: Final vault ===")

# Combine all results
all_survivors = sorted(survivors + [e for e in evolved_results if e.get("beats_random")],
                       key=lambda x: x["red_brier"])

print(f"\nFinal vault: {len(all_survivors)} surviving formulas")
print(f"\n{'Rank':<5} {'Name':<45} {'Brier':>10} {'Blue Hit':>10} {'Gap':>8} {'Risk':>10}")
print("-" * 100)
for i, s in enumerate(all_survivors[:30]):
    name = s.get("name", "?")[:44]
    brier = s.get("red_brier", 0)
    blue = s.get("blue_hit_rate", 0)
    gap = s.get("generalization_gap", 0)
    risk = s.get("overfitting_risk", "?")
    print(f"{i+1:<5} {name:<45} {brier:>10.6f} {blue:>10.4f} {gap:>8.4f} {risk:>10}")

# Export vault
vault_export = {
    "total_evaluated": len(screening_results),
    "survivor_count": len(all_survivors),
    "survival_rate": round(len(all_survivors)/max(len(screening_results),1), 4),
    "data_periods": len(draws),
    "formulas": [s for s in all_survivors[:50]],  # top 50
    "timestamp": __import__('datetime').datetime.now().isoformat(),
}

with open('E:/享中/formula_vault_results.json', 'w', encoding='utf-8') as f:
    json.dump(vault_export, f, ensure_ascii=False, indent=2)
print(f"\nVault exported to formula_vault_results.json")
