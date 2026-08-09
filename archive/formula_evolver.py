# -*- coding: utf-8 -*-
"""
Antigravity 公式探索引擎 V0.1

核心理念:
- 如果时间不存在，开奖结果由场的结构决定
- 我们需要找到描述这个结构的公式
- 公式不是预设的——它是从数据中涌现的
- 评估标准不是"统计显著性"，而是"能否在未知数据上复现"

探索策略:
1. 生成候选公式（组合各种数学操作）
2. 用历史数据训练（拟合参数）
3. 用前向滚动验证（避免过拟合）
4. 保留能稳定复现的公式
5. 淘汰不能复现的公式
"""
import numpy as np
import pandas as pd
import json
import math
import random
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from data_layer import load_history, Draw

_PROJECT_ROOT = Path(__file__).resolve().parent


# ─── 公式原子 ───
# 所有公式由这些基本操作组合而成

def atom_number(n, attr):
    """从号码n的属性中取值"""
    props = {
        "binary_weight": bin(n).count('1'),
        "digit_sum": sum(int(d) for d in str(n)),
        "is_prime": 1 if all(n % i != 0 for i in range(2, int(math.sqrt(n))+1)) and n > 1 else 0,
        "is_fibonacci": n in {1,2,3,5,8,13,21},
        "golden_dist": abs((n * (1+math.sqrt(5))/2) % 1 - 0.5),
        "mod3": n % 3,
        "mod5": n % 5,
        "mod7": n % 7,
        "mod13": n % 13,
        "digital_root": n if n < 10 else (n-1) % 9 + 1,
        "prime_factors_count": len(set(i for i in range(2,n+1) if n%i==0 and all(i%j!=0 for j in range(2,int(math.sqrt(i))+1)))) if n > 1 else 0,
    }
    return props.get(attr, n)


def atom_position(pos, number):
    """位置函数——number在pos位置的期望值"""
    return number / 34.0 * (pos + 1)


def atom_difference(a, b):
    """差值（取绝对值）"""
    return abs(a - b)


def atom_ratio(a, b):
    """比值（避免除零）"""
    if abs(b) < 1e-10:
        return 0
    return a / b


def atom_mod(a, b):
    """取模"""
    return a % b


def atom_floor(a):
    """向下取整"""
    return int(math.floor(a))


def atom_sin(a):
    """正弦"""
    return math.sin(a)


def atom_cos(a):
    """余弦"""
    return math.cos(a)


def atom_sqrt(a):
    """平方根"""
    return math.sqrt(max(0, a))


def atom_exp(a):
    """指数"""
    try:
        return math.exp(min(a, 20))  # 防溢出
    except OverflowError:
        return 1e8


def atom_log(a):
    """对数"""
    try:
        return math.log(max(abs(a), 1e-10))
    except ValueError:
        return 0


def atom_power(a, b):
    """幂"""
    try:
        if a < 0 and b != int(b):
            return 0
        return a ** b
    except (OverflowError, ZeroDivisionError):
        return 0


# ─── 公式类别 ───
# 每种公式代表一类"场结构假设"

class FormulaFamily:
    """公式家族基类"""
    name = "base"
    description = ""

    def generate_candidates(self, n_candidates=100):
        """生成候选公式"""
        raise NotImplementedError

    def evaluate(self, formula, draws, train_end, test_start):
        """评估公式"""
        raise NotImplementedError

    def score(self, result):
        """计算公式得分"""
        raise NotImplementedError


class PositionFormula(FormulaFamily):
    """
    位置公式家族: P(i) = f(number_i, position, history)

    假设: 每个位置i有一个确定的函数f，给定号码和位置信息，
    可以计算出该位置在下一期的值。

    如果时间不存在，这个函数不依赖于"时间"，
    而依赖于号码在结构中的位置。
    """
    name = "positional"

    def generate_candidates(self, n_candidates=100):
        """生成位置公式候选"""
        candidates = []

        # 基本结构: f(pos, num) = Σ w_k * atom_k(pos, num, history)
        # 探索不同的 atom 组合

        atoms = [
            ("binary_weight", lambda n: bin(n).count('1')),
            ("digit_sum", lambda n: sum(int(d) for d in str(n))),
            ("golden_dist", lambda n: abs((n * (1+math.sqrt(5))/2) % 1 - 0.5)),
            ("mod3", lambda n: n % 3),
            ("mod5", lambda n: n % 5),
            ("mod7", lambda n: n % 7),
            ("is_prime", lambda n: 1 if n > 1 and all(n % i != 0 for i in range(2, int(math.sqrt(n))+1)) else 0),
            ("digital_root", lambda n: (n-1) % 9 + 1),
        ]

        # 组合1: 线性组合
        for _ in range(n_candidates // 4):
            num_atoms = random.randint(2, 5)
            selected = random.sample(atoms, num_atoms)
            weights = [random.uniform(-2, 2) for _ in range(num_atoms)]
            bias = random.uniform(-10, 10)
            candidates.append({
                "type": "linear",
                "atoms": selected,
                "weights": weights,
                "bias": bias,
            })

        # 组合2: 非线性组合
        for _ in range(n_candidates // 4):
            a1, f1 = random.choice(atoms)
            a2, f2 = random.choice(atoms)
            op = random.choice(["+", "-", "*", "/"])
            candidates.append({
                "type": "nonlinear",
                "atom1": (a1, f1),
                "atom2": (a2, f2),
                "op": op,
            })

        # 组合3: 周期函数
        for _ in range(n_candidates // 4):
            freq = random.choice([2, 3, 5, 7, 13, 16, 21, 28, 33, 34])
            phase = random.uniform(0, 2 * math.pi)
            amplitude = random.uniform(0.5, 10)
            candidates.append({
                "type": "periodic",
                "frequency": freq,
                "phase": phase,
                "amplitude": amplitude,
            })

        # 组合4: 黄金比例共振
        for _ in range(n_candidates // 4):
            multiplier = random.choice([1, 2, 3, 5, 8, 13, 21, 34])
            candidates.append({
                "type": "golden_resonance",
                "multiplier": multiplier,
            })

        return candidates

    def evaluate(self, formula, draws, train_end, test_start):
        """
        评估位置公式。

        对每个位置pos，用公式计算每个号码的"得分"，
        然后看得分最高的号码是否与实际开奖匹配。
        """
        train_draws = draws[:train_end]
        test_draws = draws[test_start:]

        # 计算每个号码的公式得分
        scores = {}
        for n in range(1, 34):
            scores[n] = self._formula_score(formula, n, train_draws)

        # 对测试集，检查公式得分最高的号码是否命中
        hits = 0
        total = 0
        for draw in test_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
            top_6 = [n for n, _ in sorted_scores[:6]]
            hit = len(set(top_6) & set(reds))
            hits += hit
            total += 6

        accuracy = hits / max(total, 1)
        return {
            "accuracy": accuracy,
            "hits": hits,
            "total": total,
            "formula": formula,
        }

    def _formula_score(self, formula, number, draws):
        """计算单个号码的公式得分"""
        ft = formula["type"]

        if ft == "linear":
            score = formula["bias"]
            for atom_name, atom_fn, weight in zip(formula["atoms"], [f for _, f in formula["atoms"]], formula["weights"]):
                score += weight * atom_fn(number)
            return score

        elif ft == "nonlinear":
            a1, f1 = formula["atom1"]
            a2, f2 = formula["atom2"]
            v1 = f1(number)
            v2 = f2(number)
            op = formula["op"]
            if op == "+": return v1 + v2
            elif op == "-": return v1 - v2
            elif op == "*": return v1 * v2
            elif op == "/": return v1 / max(v2, 1e-10)
            return 0

        elif ft == "periodic":
            return formula["amplitude"] * math.sin(
                2 * math.pi * number / formula["frequency"] + formula["phase"]
            )

        elif ft == "golden_resonance":
            phi = (1 + math.sqrt(5)) / 2
            return abs(math.sin(2 * math.pi * number * phi / formula["multiplier"]))

        return 0


class CorrelationFormula(FormulaFamily):
    """
    关联公式家族: C(i,j) = f(number_i, number_j, history)

    假设: 号码之间的关联不是随机的，而是由场结构决定的。
    如果我们能找到正确的关联函数，就能预测哪些号码会一起出现。
    """
    name = "correlation"

    def generate_candidates(self, n_candidates=100):
        candidates = []

        # 基础关联函数
        assoc = [
            ("mod_match", lambda a, b: 1 if a % b == 0 or b % a == 0 else 0),
            ("diff", lambda a, b: abs(a - b)),
            ("gcd", lambda a, b: math.gcd(a, b)),
            ("golden_phase", lambda a, b: abs(math.sin(math.pi * (a+b) * (1+math.sqrt(5))/2))),
            ("digit_overlap", lambda a, b: 1 if set(str(a)) & set(str(b)) else 0),
            ("prime_pair", lambda a, b: 1 if all(a%i!=0 for i in range(2,int(math.sqrt(a))+1)) and all(b%j!=0 for j in range(2,int(math.sqrt(b))+1)) else 0),
        ]

        for _ in range(n_candidates):
            func = random.choice(assoc)
            weight = random.uniform(-1, 1)
            candidates.append({
                "type": "pair_correlation",
                "func": func,
                "weight": weight,
            })

        return candidates

    def evaluate(self, formula, draws, train_end, test_start):
        """评估关联公式——看公式预测的强关联对是否真的共现"""
        train_draws = draws[:train_end]
        test_draws = draws[test_start:]

        # 计算训练集中所有号码对的公式得分
        pair_scores = defaultdict(float)
        for draw in train_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for i in range(len(reds)):
                for j in range(i+1, len(reds)):
                    a, b = reds[i], reds[j]
                    key = (min(a,b), max(a,b))
                    pair_scores[key] += formula["weight"] * formula["func"](a, b)[1]

        # 对测试集，检查高分对是否共现
        hits = 0
        total = 0
        for draw in test_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for i in range(len(reds)):
                for j in range(i+1, len(reds)):
                    a, b = reds[i], reds[j]
                    key = (min(a,b), max(a,b))
                    total += 1
                    if key in pair_scores and pair_scores[key] > 0:
                        hits += 1

        accuracy = hits / max(total, 1)
        return {"accuracy": accuracy, "hits": hits, "total": total, "formula": formula}


# ─── 公式进化器 ───
# 用遗传算法进化公式

class FormulaEvolver:
    """公式进化器"""

    def __init__(self, families=None):
        self.families = families or [PositionFormula(), CorrelationFormula()]
        self.formula_archive = []  # 历史公式记录
        self.best_formulas = {}  # 按家族存储最佳公式

    def evolve(self, draws, n_generations=50, population_size=100,
               train_ratio=0.7, n_rounds=30):
        """
        进化公式。

        使用滚动窗口交叉验证：
        - 每轮用前train_ratio的数据训练
        - 用剩余数据测试
        - 只在测试集上表现稳定的公式才被保留
        """
        n_train = int(len(draws) * train_ratio)

        print(f"🧬 公式进化器启动: {n_generations}代, 种群{population_size}")
        print(f"   训练窗口: {n_train}期, 回测轮数: {n_rounds}")

        for gen in range(n_generations):
            # 生成种群
            population = []
            for family in self.families:
                candidates = family.generate_candidates(population_size // len(self.families))
                for c in candidates:
                    population.append((family, c))

            # 评估（用多轮滚动验证）
            fitness = []
            for family, formula in population:
                scores = []
                for r in range(n_rounds):
                    train_end = n_train - r * 10
                    test_start = train_end + 10
                    if train_end < 100 or test_start >= len(draws):
                        continue
                    try:
                        result = family.evaluate(formula, draws, train_end, test_start)
                        scores.append(result["accuracy"])
                    except:
                        scores.append(0)

                if scores:
                    avg_fitness = np.mean(scores)
                    std_fitness = np.std(scores)
                    # 稳定性加权
                    fitness.append((family, formula, avg_fitness, std_fitness))
                else:
                    fitness.append((family, formula, 0, 1))

            # 排序
            fitness.sort(key=lambda x: -x[2])

            # 记录最佳
            if fitness:
                best_f, best_formula, best_fit, best_std = fitness[0]
                print(f"  代{gen+1:3d}: 最佳公式得分={best_fit:.4f} ± {best_std:.4f}")

                key = best_f.name
                if key not in self.best_formulas or best_fit > self.best_formulas[key]["fitness"]:
                    self.best_formulas[key] = {
                        "formula": best_formula,
                        "fitness": best_fit,
                        "std": best_std,
                        "generation": gen + 1,
                    }

            # 选择前20%进化
            survivors = [f for f in fitness[:max(1, len(fitness)//5)] if f[2] > 0]

            if not survivors:
                print(f"  代{gen+1}: 无存活，退出")
                break

            # 交叉变异生成下一代
            new_population = []
            for _ in range(population_size):
                parent = random.choice(survivors)
                family, formula, fit, std = parent
                mutated = self._mutate(formula)
                new_population.append((family, mutated))

            population = new_population

        return self.best_formulas

    def _mutate(self, formula):
        """对公式进行随机变异"""
        import copy
        mutated = copy.deepcopy(formula)
        mutation_type = random.choice(["weight", "atom", "type"])

        if mutation_type == "weight" and "weights" in mutated:
            idx = random.randint(0, len(mutated["weights"]) - 1)
            mutated["weights"][idx] += random.gauss(0, 0.5)
        elif mutation_type == "atom" and "atoms" in mutated:
            if random.random() < 0.3:
                # 添加/删除原子
                atoms_pool = [
                    ("binary_weight", lambda n: bin(n).count('1')),
                    ("digit_sum", lambda n: sum(int(d) for d in str(n))),
                    ("golden_dist", lambda n: abs((n * (1+math.sqrt(5))/2) % 1 - 0.5)),
                    ("mod3", lambda n: n % 3),
                    ("mod5", lambda n: n % 5),
                    ("is_prime", lambda n: 1 if n > 1 and all(n%i!=0 for i in range(2,int(math.sqrt(n))+1)) else 0),
                ]
                if random.random() < 0.5 and len(mutated["atoms"]) < 5:
                    new_atom = random.choice(atoms_pool)
                    if new_atom not in mutated["atoms"]:
                        mutated["atoms"].append(new_atom)
                        mutated["weights"].append(random.uniform(-2, 2))
                elif len(mutated["atoms"]) > 1:
                    idx = random.randint(0, len(mutated["atoms"]) - 1)
                    mutated["atoms"].pop(idx)
                    mutated["weights"].pop(idx)
        elif mutation_type == "type":
            # 改变公式类型
            if "type" in mutated:
                mutated["type"] = random.choice(["linear", "nonlinear", "periodic", "golden_resonance"])

        return mutated


# ─── 主函数 ───

def run_formula_evolution():
    """运行公式进化"""
    print("=" * 70)
    print("  🧬 Antigravity 公式探索引擎 V0.1")
    print("  假设: 公式不是预设的，而是从数据中涌现的")
    print("=" * 70)
    print()

    draws = load_history()
    print(f"数据: {len(draws)} 期")
    print()

    evolver = FormulaEvolver()
    best = evolver.evolve(draws, n_generations=20, population_size=60, n_rounds=20)

    print("\n" + "=" * 70)
    print("  📋 进化结果")
    print("=" * 70)

    for family_name, info in best.items():
        print(f"\n  [{family_name}]")
        print(f"  最佳公式: {info['formula']}")
        print(f"  得分: {info['fitness']:.4f} ± {info['std']:.4f}")
        print(f"  在第 {info['generation']} 代达到")

    # 保存结果
    output = {}
    for k, v in best.items():
        output[k] = {
            "formula": str(v["formula"]),
            "fitness": v["fitness"],
            "std": v["std"],
            "generation": v["generation"],
        }

    with open(str(_PROJECT_ROOT / "evolved_formulas.json"), "w", encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n📄 进化结果已保存: evolved_formulas.json")


if __name__ == "__main__":
    run_formula_evolution()
