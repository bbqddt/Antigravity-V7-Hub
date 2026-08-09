# -*- coding: utf-8 -*-
"""
Antigravity 公式生成器 V0.2 — 无限搜索空间

核心理念:
- 不要从4类原子函数开始——要从所有可能的数学结构开始
- 不要从加减乘除开始——要从任何你能想到的操作开始
- 公式不是"设计"的——是"生长"出来的
- 关键是：生成尽可能多的候选，让它们自己竞争

策略:
1. 定义一个"公式生成器"——能产生任意复杂度的表达式树
2. 每棵树都是一个候选公式
3. 用历史数据训练，用滚动窗口验证
4. 存活下来的公式继续繁殖
5. 淘汰的公式变成新公式的"基因片段"

这就是进化——但不是遗传算法那种有限的进化。
是让公式自己决定它需要什么原子函数。
"""
import numpy as np
import pandas as pd
import json
import math
import random
import copy
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from data_layer import load_history

_PROJECT_ROOT = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════
# 原子函数库 — 不是固定的，是动态生长的
# ═══════════════════════════════════════════════════════════

ATOM_LIBRARY = {
    # ─── 基础算术 ───
    "identity": lambda n: n,
    "negate": lambda n: -n,
    "abs": lambda n: abs(n),
    "square": lambda n: n * n,
    "cube": lambda n: n ** 3,
    "sqrt": lambda n: math.sqrt(max(0, n)),
    "cbrt": lambda n: math.copysign(abs(n) ** (1/3), n),
    "reciprocal": lambda n: 1.0 / max(n, 1e-10),
    "exp": lambda n: math.exp(min(n, 20)),
    "log": lambda n: math.log(max(abs(n), 1e-10)),
    "log10": lambda n: math.log10(max(abs(n), 1e-10)),
    "sin": lambda n: math.sin(n),
    "cos": lambda n: math.cos(n),
    "tan": lambda n: math.tan(n) if abs(math.cos(n)) > 0.01 else 0,
    "asin": lambda n: math.asin(max(-1, min(1, n))),
    "atan": lambda n: math.atan(n),
    "sigmoid": lambda n: 1.0 / (1 + math.exp(-min(max(n, -500), 500))),
    "softplus": lambda n: math.log1p(math.exp(min(n, 50))),
    "relu": lambda n: max(0, n),
    "floor": lambda n: math.floor(n),
    "ceil": lambda n: math.ceil(n),
    "round": lambda n: round(n),
    "sign": lambda n: 1 if n > 0 else (-1 if n < 0 else 0),

    # ─── 数位操作 ───
    "digit_sum": lambda n: sum(int(d) for d in str(abs(n))),
    "digit_product": lambda n: eval('*'.join(str(d) for d in str(abs(n)))) if all(int(d) != 0 for d in str(abs(n))) else 0,
    "digit_reverse": lambda n: int(str(abs(n))[::-1]),
    "digit_max": lambda n: max(int(d) for d in str(abs(n))),
    "digit_min": lambda n: min(int(d) for d in str(abs(n))),
    "digit_unique_count": lambda n: len(set(str(abs(n)))),
    "digit_root": lambda n: (n - 1) % 9 + 1 if n != 0 else 0,
    "digit_histogram": lambda n: tuple(sorted(str(abs(n)).count(d) for d in '0123456789')),

    # ─── 模运算 ───
    "mod3": lambda n: n % 3,
    "mod4": lambda n: n % 4,
    "mod5": lambda n: n % 5,
    "mod6": lambda n: n % 6,
    "mod7": lambda n: n % 7,
    "mod8": lambda n: n % 8,
    "mod9": lambda n: n % 9,
    "mod10": lambda n: n % 10,
    "mod11": lambda n: n % 11,
    "mod12": lambda n: n % 12,
    "mod13": lambda n: n % 13,
    "mod16": lambda n: n % 16,
    "mod17": lambda n: n % 17,
    "mod21": lambda n: n % 21,
    "mod23": lambda n: n % 23,
    "mod31": lambda n: n % 31,
    "mod33": lambda n: n % 33,
    "mod34": lambda n: n % 34,
    "mod_phi": lambda n: n % 34,  # golden ratio proxy

    # ─── 数论 ───
    "is_prime": lambda n: 1 if n > 1 and all(n % i != 0 for i in range(2, int(math.sqrt(n)) + 1)) else 0,
    "is_fibonacci": lambda n: 1 if n in {1,2,3,5,8,13,21,34,55,89} else 0,
    "is_square": lambda n: 1 if int(math.sqrt(n)) ** 2 == n else 0,
    "is_cube": lambda n: 1 if round(n ** (1/3)) ** 3 == n else 0,
    "is_triangular": lambda n: 1 if int(math.sqrt(2*n)) * (int(math.sqrt(2*n))+1) // 2 == n else 0,
    "is_perfect": lambda n: 1 if n in {6, 28, 496} else 0,
    "prime_count": lambda n: sum(1 for i in range(2, n+1) if all(i % j != 0 for j in range(2, int(math.sqrt(i))+1))) if n > 1 else 0,
    "prime_factor_count": lambda n: len(set(i for i in range(2, n+1) if n % i == 0 and all(i % j != 0 for j in range(2, int(math.sqrt(i))+1)))),
    "smallest_prime_factor": lambda n: next((i for i in range(2, n+1) if n % i == 0), n),
    "largest_prime_factor": lambda n: next((i for i in range(n, 1, -1) if n % i == 0 and all(i % j != 0 for j in range(2, int(math.sqrt(i))+1))), 1),

    # ─── 二进制 ───
    "binary_weight": lambda n: bin(n).count('1'),
    "binary_length": lambda n: len(bin(n)) - 2,
    "binary_reverse": lambda n: int(bin(n)[2:][::-1], 2) if n > 0 else 0,
    "binary_popcount_even": lambda n: 1 if bin(n).count('1') % 2 == 0 else 0,
    "bit_and_33": lambda n: n & 33,
    "bit_or_33": lambda n: n | 33,
    "bit_xor_33": lambda n: n ^ 33,

    # ─── 黄金比例 ───
    "golden_dist": lambda n: abs((n * (1 + math.sqrt(5)) / 2) % 1 - 0.5),
    "golden_angle": lambda n: abs(math.sin(math.pi * n * (1 + math.sqrt(5)) / 2)),
    "golden_mod": lambda n: n % int((1 + math.sqrt(5)) / 2 * 10),

    # ─── 组合 ───
    "n_choose_2": lambda n: n * (n - 1) // 2,
    "n_choose_3": lambda n: n * (n - 1) * (n - 2) // 6,
    "factorial_approx": lambda n: math.gamma(n + 1) if n < 170 else 1e100,

    # ─── 常数 ───
    "pi_scaled": lambda n: n * math.pi,
    "e_scaled": lambda n: n * math.e,
    "phi_scaled": lambda n: n * (1 + math.sqrt(5)) / 2,
    "sqrt2_scaled": lambda n: n * math.sqrt(2),
    "sqrt3_scaled": lambda n: n * math.sqrt(3),
    "sqrt5_scaled": lambda n: n * math.sqrt(5),
    "ln2_scaled": lambda n: n * math.log(2),
    "ln3_scaled": lambda n: n * math.log(3),

    # ─── 非常规 ───
    "sum_digits_squared": lambda n: sum(int(d)**2 for d in str(abs(n))),
    "alternating_digit_sum": lambda n: sum((-1)**i * int(d) for i, d in enumerate(str(abs(n)))),
    "digit_pair_sum": lambda n: sum(int(str(abs(n))[i:i+2]) for i in range(0, len(str(abs(n)))-1, 2)),
    "zipf_score": lambda n: 1.0 / (n * math.log(n + 1)),
    "harmonic_number": lambda n: sum(1.0/i for i in range(1, n+1)) if n > 0 else 0,
    " Mertens_function": lambda n: sum((-1)**(prime_count(i)-prime_count(i-1)) for i in range(1, n+1)) if n > 0 else 0,
}

# 修复命名错误
ATOM_LIBRARY.pop(" Mertens_function", None)


# ═══════════════════════════════════════════════════════════
# 二元操作符
# ═══════════════════════════════════════════════════════════

BINARY_OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / max(b, 1e-10),
    "min": lambda a, b: min(a, b),
    "max": lambda a, b: max(a, b),
    "pow": lambda a, b: a ** min(abs(b), 5),
    "mod": lambda a, b: a % max(b, 1),
    "and": lambda a, b: 1 if (a > 0 and b > 0) else 0,
    "or": lambda a, b: 1 if (a > 0 or b > 0) else 0,
    "xor": lambda a, b: 1 if ((a > 0) != (b > 0)) else 0,
    "atan2": lambda a, b: math.atan2(a, max(b, 1e-10)),
}


# ═══════════════════════════════════════════════════════════
# 公式树 — 公式是树，不是字符串
# ═══════════════════════════════════════════════════════════

class FormulaTree:
    """一棵公式树"""

    def __init__(self, atom=None, op=None, left=None, right=None, constant=None):
        self.atom = atom
        self.op = op
        self.left = left
        self.right = right
        self.constant = constant

    def evaluate(self, n):
        """在号码n处求值 — 简化版，保证返回有限浮点数"""
        if self.atom:
            fn = ATOM_LIBRARY.get(self.atom, lambda x: x)
            try:
                result = fn(n)
                if isinstance(result, (list, tuple)):
                    return float(len(result))
                v = float(result)
                return v if math.isfinite(v) else 0.0
            except:
                return 0.0

        if self.constant is not None:
            return float(self.constant)

        if self.op and self.left and self.right:
            try:
                a = self.left.evaluate(n)
                b = self.right.evaluate(n)
                op_fn = BINARY_OPS.get(self.op, lambda x, y: x + y)
                result = op_fn(a, b)
                v = float(result)
                return v if math.isfinite(v) else 0.0
            except:
                return 0.0

        return float(n)

    def clone(self):
        return FormulaTree(
            atom=self.atom,
            op=self.op,
            left=self.left.clone() if self.left else None,
            right=self.right.clone() if self.right else None,
            constant=self.constant,
        )

    def __repr__(self):
        if self.atom:
            return f"Atom({self.atom})"
        if self.constant is not None:
            return f"Const({self.constant:.2f})"
        if self.op:
            return f"Op({self.op}, {self.left}, {self.right})"
        return "Identity()"

    def to_dict(self):
        d = {}
        if self.atom:
            d["atom"] = self.atom
        if self.constant is not None:
            d["constant"] = round(self.constant, 4)
        if self.op:
            d["op"] = self.op
            d["left"] = self.left.to_dict() if self.left else None
            d["right"] = self.right.to_dict() if self.right else None
        return d

    @staticmethod
    def from_dict(d):
        if not d:
            return FormulaTree(atom="identity")
        if "atom" in d:
            return FormulaTree(atom=d["atom"])
        if "constant" in d:
            return FormulaTree(constant=d["constant"])
        return FormulaTree(
            op=d["op"],
            left=FormulaTree.from_dict(d.get("left")) if d.get("left") else None,
            right=FormulaTree.from_dict(d.get("right")) if d.get("right") else None,
        )


def random_tree(depth=0, max_depth=6):
    """随机生成一棵公式树"""
    if depth >= max_depth or (depth > 0 and random.random() < 0.4):
        # 叶子节点
        if random.random() < 0.1:
            return FormulaTree(constant=random.gauss(0, 1))
        elif random.random() < 0.3:
            return FormulaTree(atom="identity")
        else:
            atom = random.choice(list(ATOM_LIBRARY.keys()))
            return FormulaTree(atom=atom)

    # 内部节点 — 二元操作
    op = random.choice(list(BINARY_OPS.keys()))
    left = random_tree(depth + 1, max_depth)
    right = random_tree(depth + 1, max_depth)
    return FormulaTree(op=op, left=left, right=right)


def mutate_tree(tree, mutation_rate=0.3):
    """变异一棵树"""
    new_tree = tree.clone()
    _mutate_node(new_tree, mutation_rate)
    return new_tree


def _mutate_node(node, rate):
    if random.random() > rate:
        return

    choice = random.random()
    if choice < 0.3:
        # 替换整个子树
        if node.atom or node.constant is not None:
            if random.random() < 0.5:
                node.atom = random.choice(list(ATOM_LIBRARY.keys()))
            else:
                node.constant = random.gauss(0, 1)
    elif choice < 0.6:
        # 交换操作符
        if node.op:
            node.op = random.choice(list(BINARY_OPS.keys()))
    else:
        # 变异子节点
        if node.left:
            _mutate_node(node.left, rate)
        if node.right:
            _mutate_node(node.right, rate)


# ═══════════════════════════════════════════════════════════
# 公式评估器
# ═══════════════════════════════════════════════════════════

class FormulaEvaluator:
    """评估公式在历史数据上的表现"""

    def __init__(self, draws):
        self.draws = draws
        self.n_draws = len(draws)

    def evaluate(self, tree, train_end, test_start):
        """
        评估公式。

        方法: 用公式对33个号码打分，取Top-6与测试集碰撞。
        简化：只对训练集中出现过的号码计算得分。
        """
        train_draws = self.draws[:train_end]
        test_draws = self.draws[train_end:test_start] if test_start <= self.n_draws else []

        if not test_draws or not train_draws:
            return 0.0

        # 对33个号码，用公式打分
        scores = {}
        for n in range(1, 34):
            try:
                v = tree.evaluate(n)
                if not math.isfinite(v):
                    v = 0.0
                scores[n] = v
            except:
                scores[n] = 0.0

        # 按公式值排序，取Top-6
        sorted_nums = sorted(scores.items(), key=lambda x: -x[1])
        top_6_formula = [n for n, _ in sorted_nums[:6]]

        # 碰撞测试集
        total_hits = 0
        for draw in test_draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            total_hits += len(set(top_6_formula) & set(reds))

        return total_hits / max(len(test_draws) * 6, 1)

    def cross_validate(self, tree, n_windows=10, window_size=500, step=50):
        """快速交叉验证 — 减少窗口数和轮数"""
        scores = []
        for i in range(min(n_windows, 8)):
            train_end = window_size + i * step
            test_start = train_end + 10
            if test_start >= self.n_draws:
                break
            try:
                score = self.evaluate(tree, train_end, test_start)
                if math.isfinite(score) and score > 0:
                    scores.append(score)
            except:
                pass

        if not scores:
            return 0.0, 0.0
        return np.mean(scores), np.std(scores)


# ═══════════════════════════════════════════════════════════
# 公式进化器 V0.2 — 无限搜索空间
# ═══════════════════════════════════════════════════════════

class FormulaEvolverV2:
    """公式进化器 V0.2 — 使用随机树生成 + 交叉变异"""

    def __init__(self, draws):
        self.draws = draws
        self.evaluator = FormulaEvaluator(draws)
        self.population = []
        self.archive = []  # 历史存档
        self.best_formula = None
        self.best_fitness = 0

    def evolve(self, n_generations=50, population_size=200, crossover_rate=0.4,
               mutation_rate=0.5, tournament_size=5):
        """
        进化公式。

        核心循环:
        1. 随机生成种群（无限搜索空间）
        2. 评估每棵树的 fitness
        3. 锦标赛选择
        4. 交叉（两棵树交换子树）
        5. 变异
        6. 精英保留
        7. 重复
        """
        print(f"🧬 公式进化器 V0.2: {n_generations}代, 种群{population_size}")
        print(f"   搜索空间: {len(ATOM_LIBRARY)}个原子 × {len(BINARY_OPS)}个操作符")
        print(f"   数据: {len(self.draws)} 期")
        print()

        # 初始化种群
        for _ in range(population_size):
            tree = random_tree(depth=0, max_depth=random.randint(3, 8))
            fitness, std = self.evaluator.cross_validate(tree, n_windows=15)
            self.population.append({
                "tree": tree,
                "fitness": fitness,
                "std": std,
                "stable_fitness": fitness - std,  # 稳定性加权
            })

        for gen in range(n_generations):
            # 排序
            self.population.sort(key=lambda x: -x["stable_fitness"])

            best = self.population[0]
            print(f"  代{gen+1:3d}: best_fitness={best['fitness']:.4f} ± {best['std']:.4f} "
                  f"stable={best['stable_fitness']:.4f} | tree: {best['tree']}")

            # 更新最佳
            if best['fitness'] > self.best_fitness:
                self.best_fitness = best['fitness']
                self.best_formula = best

            # 存档
            self.archive.append({
                "generation": gen + 1,
                "best_fitness": best['fitness'],
                "best_std": best['std'],
                "best_tree": best['tree'].to_dict(),
            })

            # 新一代
            new_population = []

            # 精英保留（前5%）
            elite_count = max(1, population_size // 20)
            for i in range(elite_count):
                new_population.append(copy.deepcopy(self.population[i]))

            # 繁殖
            while len(new_population) < population_size:
                # 锦标赛选择
                parent1 = self._tournament()
                parent2 = self._tournament()

                if random.random() < crossover_rate:
                    # 交叉 — 交换子树
                    child1, child2 = self._crossover(parent1, parent2)
                    new_population.append(child1)
                    new_population.append(child2)
                else:
                    # 复制 + 变异
                    child1 = mutate_tree(parent1["tree"], mutation_rate)
                    child2 = mutate_tree(parent2["tree"], mutation_rate)
                    fitness1, std1 = self.evaluator.cross_validate(child1, n_windows=10)
                    fitness2, std2 = self.evaluator.cross_validate(child2, n_windows=10)
                    new_population.append({"tree": child1, "fitness": fitness1, "std": std1, "stable_fitness": fitness1 - std1})
                    new_population.append({"tree": child2, "fitness": fitness2, "std": std2, "stable_fitness": fitness2 - std2})

            self.population = new_population

        return self.best_formula, self.archive

    def _tournament(self):
        """锦标赛选择"""
        tournament = random.sample(self.population, min(5, len(self.population)))
        return max(tournament, key=lambda x: x["stable_fitness"])

    def _crossover(self, parent1, parent2):
        """树交叉 — 随机交换子树"""
        child1 = parent1["tree"].clone()
        child2 = parent2["tree"].clone()

        # 在 child1 中找一个随机节点，替换为 child2 的子树
        if random.random() < 0.5 and child1.atom:
            child1.atom = random.choice(list(ATOM_LIBRARY.keys()))
        if random.random() < 0.5 and child2.atom:
            child2.atom = random.choice(list(ATOM_LIBRARY.keys()))

        # 变异
        child1 = mutate_tree(child1, 0.2)
        child2 = mutate_tree(child2, 0.2)

        fitness1, std1 = self.evaluator.cross_validate(child1, n_windows=10)
        fitness2, std2 = self.evaluator.cross_validate(child2, n_windows=10)

        return (
            {"tree": child1, "fitness": fitness1, "std": std1, "stable_fitness": fitness1 - std1},
            {"tree": child2, "fitness": fitness2, "std": std2, "stable_fitness": fitness2 - std2},
        )


# ═══════════════════════════════════════════════════════════
# 主函数
# ════════════════════════════════════════════════

def run_evolution():
    draws = load_history()
    print(f"数据: {len(draws)} 期")

    evolver = FormulaEvolverV2(draws)
    best, archive = evolver.evolve(
        n_generations=30,
        population_size=100,
        crossover_rate=0.5,
        mutation_rate=0.3,
    )

    print(f"\n🏆 最佳公式: {best['tree']}")
    print(f"   Fitness: {best['fitness']:.4f} ± {best['std']:.4f}")

    # 保存
    output = {
        "best_formula": best["tree"].to_dict(),
        "best_fitness": best["fitness"],
        "best_std": best["std"],
        "archive": archive[:10],  # 只保存前10代
    }
    with open(str(_PROJECT_ROOT / "evolved_formulas_v2.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n📄 结果已保存: evolved_formulas_v2.json")


if __name__ == "__main__":
    run_evolution()
