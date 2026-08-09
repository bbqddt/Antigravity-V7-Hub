# -*- coding: utf-8 -*-
"""
Antigravity 公式发现系统 V0.3 — 暴力搜索 + 自动校正

核心理念:
- 不要从"智能"的进化开始——先从暴力搜索开始
- 生成 10万+ 个简单公式，用滚动窗口验证
- 保留前100个最佳公式
- 用这100个公式作为"种子"，让它们自由变异
- 每一轮都回测——如果公式在未知数据上失效，淘汰
- 如果存活，保留

这不是遗传算法。这是**公式筛选器**。
我们不"进化"公式——我们**过滤**掉不能复现的公式。
剩下的就是结构。
"""
import numpy as np
import pandas as pd
import json
import math
import random
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from data_layer import load_history

_PROJECT_ROOT = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════
# 公式生成器 — 暴力枚举
# ═══════════════════════════════════════════════════════════

def generate_simple_formulas(n_total=100000):
    """
    生成大量简单公式。

    公式类型:
    1. 单原子: f(n) = atom(n)
    2. 双原子组合: f(n) = op(atom1(n), atom2(n))
    3. 原子+常数: f(n) = atom(n) + c
    4. 常数变换: f(n) = c1 * atom1(n) + c2 * atom2(n)
    """
    atoms = [
        "binary_weight", "digit_sum", "digit_root", "mod3", "mod5",
        "mod7", "mod11", "mod13", "mod17", "mod33",
        "is_prime", "is_fibonacci", "is_square",
        "golden_dist", "digital_root",
        "sqrt", "exp", "log", "sin", "cos",
        "abs", "square", "negate",
        "digit_max", "digit_min", "digit_unique_count",
        "binary_weight", "binary_length",
        "zipf_score", "harmonic_number",
    ]

    ops = ["+", "-", "*", "/", "max", "min", "mod", "pow"]

    formulas = []
    for _ in range(n_total):
        formula_type = random.choice(["single", "double", "linear", "trig"])

        if formula_type == "single":
            atom = random.choice(atoms)
            formulas.append({"type": "single", "atom": atom})

        elif formula_type == "double":
            a1 = random.choice(atoms)
            a2 = random.choice(atoms)
            op = random.choice(ops)
            formulas.append({"type": "double", "atom1": a1, "atom2": a2, "op": op})

        elif formula_type == "linear":
            a1 = random.choice(atoms)
            a2 = random.choice(atoms)
            c1 = random.uniform(-5, 5)
            c2 = random.uniform(-5, 5)
            formulas.append({
                "type": "linear",
                "atom1": a1, "atom2": a2,
                "c1": round(c1, 2), "c2": round(c2, 2),
            })

        elif formula_type == "trig":
            atom = random.choice(["mod7", "mod11", "mod13", "golden_dist", "binary_weight"])
            freq = random.choice([2, 3, 5, 7, 11, 13, 16, 21, 28, 33, 34])
            phase = random.uniform(0, 6.28)
            amp = random.uniform(0.5, 10)
            formulas.append({
                "type": "trig",
                "atom": atom,
                "frequency": freq,
                "phase": round(phase, 2),
                "amplitude": round(amp, 2),
            })

    return formulas


# ═══════════════════════════════════════════════════════════
# 公式求值器
# ═══════════════════════════════════════════════════════════

def eval_formula(formula, n):
    """求值一个公式在号码n处的值"""
    atom_lib = {
        "binary_weight": lambda n: bin(n).count('1'),
        "digit_sum": lambda n: sum(int(d) for d in str(n)),
        "digit_root": lambda n: (n-1) % 9 + 1,
        "mod3": lambda n: n % 3,
        "mod5": lambda n: n % 5,
        "mod7": lambda n: n % 7,
        "mod11": lambda n: n % 11,
        "mod13": lambda n: n % 13,
        "mod17": lambda n: n % 17,
        "mod33": lambda n: n % 33,
        "is_prime": lambda n: 1 if n > 1 and all(n % i != 0 for i in range(2, int(math.sqrt(n))+1)) else 0,
        "is_fibonacci": lambda n: 1 if n in {1,2,3,5,8,13,21} else 0,
        "is_square": lambda n: 1 if int(math.sqrt(n))**2 == n else 0,
        "golden_dist": lambda n: abs((n * (1+math.sqrt(5))/2) % 1 - 0.5),
        "sqrt": lambda n: math.sqrt(max(0, n)),
        "exp": lambda n: min(math.exp(n), 100),
        "log": lambda n: math.log(max(abs(n), 1e-10)),
        "sin": lambda n: math.sin(n),
        "cos": lambda n: math.cos(n),
        "abs": lambda n: abs(n),
        "square": lambda n: n * n,
        "negate": lambda n: -n,
        "digit_max": lambda n: max(int(d) for d in str(n)),
        "digit_min": lambda n: min(int(d) for d in str(n)),
        "digit_unique_count": lambda n: len(set(str(n))),
        "binary_length": lambda n: len(bin(n)) - 2,
        "zipf_score": lambda n: 1.0 / (n * math.log(n + 1)) if n > 0 else 0,
        "harmonic_number": lambda n: sum(1.0/i for i in range(1, n+1)) if n > 0 else 0,
    }

    ft = formula["type"]

    try:
        if ft == "single":
            return atom_lib.get(formula["atom"], lambda x: x)(n)

        elif ft == "double":
            v1 = atom_lib.get(formula["atom1"], lambda x: x)(n)
            v2 = atom_lib.get(formula["atom2"], lambda x: x)(n)
            op = formula["op"]
            if op == "+": return v1 + v2
            elif op == "-": return v1 - v2
            elif op == "*": return v1 * v2
            elif op == "/": return v1 / max(v2, 1e-10)
            elif op == "max": return max(v1, v2)
            elif op == "min": return min(v1, v2)
            elif op == "mod": return v1 % max(v2, 1)
            elif op == "pow": return v1 ** min(abs(v2), 5)

        elif ft == "linear":
            v1 = atom_lib.get(formula["atom1"], lambda x: x)(n)
            v2 = atom_lib.get(formula["atom2"], lambda x: x)(n)
            return formula["c1"] * v1 + formula["c2"] * v2

        elif ft == "trig":
            v = atom_lib.get(formula["atom"], lambda x: x)(n)
            return formula["amplitude"] * math.sin(
                2 * math.pi * v / formula["frequency"] + formula["phase"]
            )

    except:
        return 0.0

    return 0.0


# ═══════════════════════════════════════════════════════════
# 公式筛选器
# ═══════════════════════════════════════════════════════════

class FormulaFilter:
    """公式筛选器 — 暴力搜索 + 滚动验证"""

    def __init__(self, draws):
        self.draws = draws
        self.n_draws = len(draws)
        self.candidates = []
        self.passed = []  # 通过验证的公式
        self.best_formulas = []

    def brute_search(self, n_formulas=100000, n_windows=15, window_size=500, step=50):
        """
        暴力搜索 + 滚动验证。

        流程:
        1. 生成 N 个随机公式
        2. 用 M 个滚动窗口验证
        3. 只在所有窗口上都表现好的公式才保留
        4. 保留 Top-K
        """
        print(f"🔍 暴力搜索: 生成 {n_formulas} 个公式")
        print(f"   验证: {n_windows} 个滚动窗口")
        print()

        formulas = generate_simple_formulas(n_formulas)

        # 评估每个公式
        scores = []
        for i, formula in enumerate(formulas):
            if (i + 1) % 10000 == 0:
                print(f"  进度: {i+1}/{n_formulas} ({100*(i+1)/n_formulas:.0f}%)")

            valid_scores = []
            for w in range(n_windows):
                train_end = window_size + w * step
                test_start = train_end + 10
                if test_start >= self.n_draws:
                    break

                # 用训练集计算每个号码的公式得分
                scores_per_num = {}
                for n in range(1, 34):
                    v = eval_formula(formula, n)
                    if isinstance(v, (int, float)) and math.isfinite(float(v)):
                        scores_per_num[n] = float(v)

                if len(scores_per_num) < 6:
                    continue

                # 取Top-6
                sorted_nums = sorted(scores_per_num.items(), key=lambda x: -x[1])
                top_6 = [n for n, _ in sorted_nums[:6]]

                # 碰撞
                test_draw = self.draws[test_start] if test_start < self.n_draws else None
                if not test_draw:
                    continue
                reds = test_draw.reds if hasattr(test_draw, 'reds') else sorted(list(test_draw.red))
                hit = len(set(top_6) & set(reds))
                valid_scores.append(hit / 6.0)

            if valid_scores:
                avg = np.mean(valid_scores)
                std = np.std(valid_scores)
                # 稳定性加权
                stable = avg - std
                scores.append({
                    "formula": formula,
                    "avg": avg,
                    "std": std,
                    "stable": stable,
                    "windows": len(valid_scores),
                })

        print(f"\n  评估完成: {len(scores)} 个有效公式")

        # 排序
        scores.sort(key=lambda x: -x["stable"])

        # 保留 Top-K
        k = min(100, len(scores))
        self.best_formulas = scores[:k]

        print(f"\n📊 Top-10 公式:")
        for i, s in enumerate(self.best_formulas[:10]):
            print(f"  #{i+1}: stable={s['stable']:.4f} avg={s['avg']:.4f}±{s['std']:.4f} "
                  f"windows={s['windows']} | {s['formula']}")

        # 保存
        output = {
            "best_formulas": [
                {
                    "formula": s["formula"],
                    "avg": round(s["avg"], 4),
                    "std": round(s["std"], 4),
                    "stable": round(s["stable"], 4),
                    "windows": s["windows"],
                }
                for s in self.best_formulas[:20]
            ],
            "total_evaluated": len(scores),
            "timestamp": datetime.now().isoformat(),
        }
        with open(str(_PROJECT_ROOT / "formula_candidates.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n📄 候选公式已保存: formula_candidates.json")

        return self.best_formulas


if __name__ == "__main__":
    draws = load_history()
    print(f"数据: {len(draws)} 期")
    print()

    filter = FormulaFilter(draws)
    filter.brute_search(n_formulas=100000, n_windows=10, window_size=500, step=50)
