# -*- coding: utf-8 -*-
"""
Formula Evolution Engine — 公式进化引擎

第一性原理：
- 双色球开奖是可计算的
- 每个公式是对开奖规则的一个假设
- 用历史数据测试公式，命中率高的公式存活并繁殖
- 低命中率的公式被淘汰
- 不停进化，直到找到能稳定命中的公式

核心机制：
1. 种群：每代生成 N 个公式（原语组合）
2. 评估：用 walk-forward 测试每个公式的命中率
3. 选择：保留 Top-K 公式
4. 繁殖：变异 + 交叉产生新一代
5. 精英保留：最佳公式直接进入下一代
6. 记录：每次进化的最佳结果持久化到磁盘
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os, json, copy, math, random
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from dataclasses import dataclass, field

sys.path.insert(0, 'E:/享中')
from data_layer import load_history, Draw
from formula_lang.primitive import get_default_primitives
from formula_lang.grammar import Formula, FormulaGrammar
from formula_lang.mutator import PrimitiveMutator

# ─── 配置 ─────────────────────────────────────────────
POPULATION_SIZE = 200        # 每代公式数量
ELITE_COUNT = 20             # 精英保留数
MUTATION_RATE = 0.4          # 变异概率
CROSSOVER_RATE = 0.3         # 交叉概率
N_GENERATIONS = 100          # 总代数
WALK_FORWARD_WINDOWS = 20   # walk-forward 窗口数
WINDOW_SIZE = 500            # 训练窗口大小
WINDOW_STEP = 50             # 步进

EVOLUTION_STATE_FILE = 'E:/享中/evolution_state_v18.json'
BEST_FORMULAS_FILE = 'E:/享中/best_formulas_v18.json'

# ─── 数据结构 ─────────────────────────────────────────

@dataclass
class FormulaResult:
    """单个公式的评估结果"""
    formula: Formula
    avg_hits: float            # 平均命中数 (0-6)
    std_hits: float            # 命中数标准差
    max_hits: int              # 最大命中数
    min_hits: int              # 最小命中数
    p_value: float             # t检验p值
    rounds: int                # 验证轮数
    stability: float           # avg - std
    fitness: float             # 综合适应度 = avg_hits * 0.6 + stability * 0.4

    def to_dict(self):
        return {
            "name": self.formula.name,
            "avg_hits": round(self.avg_hits, 4),
            "std_hits": round(self.std_hits, 4),
            "max_hits": self.max_hits,
            "min_hits": self.min_hits,
            "p_value": round(self.p_value, 4),
            "rounds": self.rounds,
            "stability": round(self.stability, 4),
            "fitness": round(self.fitness, 4),
            "operators": self.formula.operators,
            "primitive_names": [p.name for p in self.formula.primitives],
        }


def evaluate_formula_walk_forward(formula, draws, n_windows=WALK_FORWARD_WINDOWS,
                                   window_size=WINDOW_SIZE, step=WINDOW_STEP):
    """Walk-forward 评估一个公式的命中率"""
    per_round_hits = []

    for w in range(n_windows):
        train_end = window_size + w * step
        test_start = train_end + 10
        test_end = min(test_start + 10, len(draws))

        if test_end <= test_start:
            break

        try:
            pred_top6 = formula.rank_top_6(draws[:train_end])
            actual_hits = 0
            for draw in draws[test_start:test_end]:
                actual_reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
                actual_hits += len(set(pred_top6) & set(actual_reds))

            per_round_hits.append(actual_hits)
        except Exception:
            per_round_hits.append(0)

    if not per_round_hits:
        return None

    avg = sum(per_round_hits) / len(per_round_hits)
    std = (sum((h - avg) ** 2 for h in per_round_hits) / max(len(per_round_hits) - 1, 1)) ** 0.5
    max_h = max(per_round_hits)
    min_h = min(per_round_hits)

    # t检验 vs 随机基线 1.09
    se = std / (len(per_round_hits) ** 0.5) if std > 0 else 1
    t_stat = (avg - 1.09) / se if se > 0 else 0
    p_value = 0.5 * (1 - math.erf(abs(t_stat) / math.sqrt(2))) * 2

    return FormulaResult(
        formula=formula,
        avg_hits=avg,
        std_hits=std,
        max_hits=max_h,
        min_hits=min_h,
        p_value=p_value,
        rounds=len(per_round_hits),
        stability=avg - std,
        fitness=avg * 0.6 + max(0, avg - std) * 0.4,
    )


# ─── 公式生成器 ───────────────────────────────────────

def generate_formula_population(primitives, population_size, rng):
    """生成一代新的公式种群"""
    formulas = []
    operators = ["resonance", "weighted_sum", "cascade", "phase_align"]

    for i in range(population_size):
        # 随机选择2-4个原语
        n_prims = rng.randint(2, min(4, len(primitives)))
        selected = rng.sample(primitives, n_prims)

        # 随机选择组合算子
        op = rng.choice(operators)

        try:
            if op == "resonance":
                weights = [rng.uniform(0.2, 0.8) for _ in range(len(selected))]
                total = sum(weights)
                weights = [w / total for w in weights]
                formula = FormulaGrammar.resonance(selected, weights=weights,
                                                   name=f"evo_{i}")
            elif op == "weighted_sum":
                weights = [rng.uniform(0.1, 0.9) for _ in range(len(selected))]
                total = sum(weights)
                weights = [w / total for w in weights]
                formula = FormulaGrammar.weighted_sum(selected, weights=weights,
                                                       name=f"evo_{i}")
            elif op == "cascade":
                thresholds = [rng.uniform(0.1, 0.5) for _ in range(len(selected) - 1)]
                formula = FormulaGrammar.cascade(selected, thresholds=thresholds,
                                                  name=f"evo_{i}")
            else:  # phase_align
                offsets = [rng.uniform(0.2, 0.8) for _ in range(len(selected) - 1)]
                formula = FormulaGrammar.phase_align(selected, offsets=offsets,
                                                      name=f"evo_{i}")
            formulas.append(formula)
        except Exception:
            continue

    return formulas


# ─── 变异与交叉 ───────────────────────────────────────

mutator_instance = PrimitiveMutator()

def mutate_formula(formula, draws, rng, generation):
    """变异一个公式"""
    new_prims = []
    for p in formula.primitives:
        if rng.random() < MUTATION_RATE:
            try:
                mutated = mutator_instance.mutate(p, draws, rng, generation=generation)
                new_prims.append(mutated)
            except Exception:
                new_prims.append(p)
        else:
            new_prims.append(p)

    # 可能替换一个原语
    if new_prims and rng.random() < 0.2:
        idx = rng.randint(0, len(new_prims) - 1)
        new_prims[idx] = copy.deepcopy(rng.choice(get_default_primitives()))

    return Formula(
        name=f"{formula.name}_m",
        primitives=new_prims,
        operators=list(formula.operators),
        parameters=dict(formula.parameters),
    )


def crossover_formulas(f1, f2, rng):
    """交叉两个公式"""
    # 交换原语子集
    all_prims = list(f1.primitives) + list(f2.primitives)
    n_new = rng.randint(2, min(4, len(all_prims)))
    selected = rng.sample(all_prims, n_new)

    if len(selected) < 2:
        return f1

    op = rng.choice(["resonance", "weighted_sum"])
    try:
        if op == "resonance":
            weights = [rng.uniform(0.2, 0.8) for _ in range(len(selected))]
            total = sum(weights)
            weights = [w / total for w in weights]
            return FormulaGrammar.resonance(selected, weights=weights, name=f"xover_{f1.name[:15]}")
        else:
            return FormulaGrammar.weighted_sum(selected, name=f"xover_{f1.name[:15]}")
    except Exception:
        return f1


# ─── 进化主循环 ───────────────────────────────────────

def load_evolution_state():
    """加载进化状态（断点续训）"""
    if os.path.exists(EVOLUTION_STATE_FILE):
        with open(EVOLUTION_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_evolution_state(gen, best_result, all_results, population):
    """保存进化状态"""
    state = {
        "generation": gen,
        "best_formula": best_result.to_dict(),
        "top_10": [r.to_dict() for r in sorted(all_results, key=lambda x: -x.fitness)[:10]],
        "population_size": len(population),
        "timestamp": datetime.now().isoformat(),
    }
    with open(EVOLUTION_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 保存最佳公式列表
    all_best = load_best_formulas()
    all_best.append(best_result.to_dict())
    # 去重
    seen = set()
    unique_best = []
    for b in all_best:
        if b["name"] not in seen:
            seen.add(b["name"])
            unique_best.append(b)
    with open(BEST_FORMULAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique_best[:100], f, ensure_ascii=False, indent=2)


def load_best_formulas():
    if os.path.exists(BEST_FORMULAS_FILE):
        with open(BEST_FORMULAS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def run_evolution(draws, primitives, start_gen=0, max_gens=N_GENERATIONS):
    """运行进化循环"""
    rng = random.Random(42 + start_gen)

    # 初始化种群
    print(f"\n{'='*72}")
    print(f"  GONGSHI EVOLUTION ENGINE V18 — Generation {start_gen+1} to {max_gens}")
    print(f"{'='*72}")
    print(f"Population: {POPULATION_SIZE}, Elites: {ELITE_COUNT}, Generations: {max_gens}")
    print(f"Data: {len(draws)} periods (#{draws[0].period} ~ #{draws[-1].period})")
    print(f"Primitives: {len(primitives)}")
    print()

    # 初始种群
    population = generate_formula_population(primitives, POPULATION_SIZE, rng)
    print(f"Initial population: {len(population)} formulas")

    best_overall = None
    best_fitness_overall = -999
    generation_history = []

    for gen in range(start_gen, max_gens):
        gen_start = datetime.now()

        # 1. 评估整个种群
        results = []
        for i, formula in enumerate(population):
            res = evaluate_formula_walk_forward(formula, draws)
            if res:
                results.append(res)

        if not results:
            print(f"  Gen {gen+1}: No valid results, regenerating...")
            population = generate_formula_population(primitives, POPULATION_SIZE, rng)
            continue

        # 2. 排序
        results.sort(key=lambda x: -x.fitness)
        avg_fitness = sum(r.fitness for r in results) / len(results)
        best = results[0]

        # 3. 记录
        if best.fitness > best_fitness_overall:
            best_fitness_overall = best.fitness
            best_overall = best

        elapsed = (datetime.now() - gen_start).total_seconds()

        generation_history.append({
            "generation": gen + 1,
            "best_fitness": best.fitness,
            "best_avg_hits": best.avg_hits,
            "best_std": best.std_hits,
            "best_max": best.max_hits,
            "avg_fitness": avg_fitness,
            "p_value": best.p_value,
        })

        # 打印进度
        if gen % 5 == 0 or gen == max_gens - 1:
            print(f"  Gen {gen+1:>3}/{max_gens}: "
                  f"best_fit={best.fitness:.3f} "
                  f"(hits={best.avg_hits:.2f}±{best.std_hits:.2f}, "
                  f"max={best.max_hits}, p={best.p_value:.3f}), "
                  f"best_all={best_fitness_overall:.3f}, "
                  f"time={elapsed:.0f}s")

        # 4. 选择精英
        survivors = results[:ELITE_COUNT]

        # 5. 生成新一代
        new_population = []

        # 精英保留
        for s in survivors:
            new_population.append(copy.deepcopy(s.formula))

        # 变异
        for s in random.sample(survivors, min(len(survivors), ELITE_COUNT)):
            child = mutate_formula(s.formula, draws, rng, generation=gen)
            new_population.append(child)

        # 交叉
        for _ in range(int(POPULATION_SIZE * CROSSOVER_RATE)):
            if len(survivors) >= 2:
                f1, f2 = rng.sample(survivors, 2)
                child = crossover_formulas(f1.formula, f2.formula, rng)
                new_population.append(child)

        # 补充随机新生成（保持多样性）
        while len(new_population) < POPULATION_SIZE:
            new_pop = generate_formula_population(primitives, POPULATION_SIZE - len(new_population), rng)
            new_population.extend(new_pop)

        population = new_population[:POPULATION_SIZE]

        # 6. 保存状态
        if gen % 10 == 0 or gen == max_gens - 1:
            save_evolution_state(gen + 1, best, results, population)

    # 最终输出
    print(f"\n{'='*72}")
    print(f"  BEST FORMULA FOUND")
    print(f"{'='*72}")
    if best_overall:
        print(f"  Name: {best_overall.formula.name}")
        print(f"  Fitness: {best_fitness_overall:.3f}")
        print(f"  Avg Hits: {best_overall.avg_hits:.2f} +/- {best_overall.std_hits:.2f}")
        print(f"  Max Hits: {best_overall.max_hits}/6")
        print(f"  Min Hits: {best_overall.min_hits}/6")
        print(f"  P-value: {best_overall.p_value:.4f}")
        print(f"  Stability: {best_overall.stability:.2f}")
        print(f"  Primitives: {[p.name for p in best_overall.formula.primitives]}")
        print(f"  Operators: {best_overall.formula.operators}")

        # 输出最终预测
        pred = best_overall.formula.rank_top_6(draws)
        print(f"\n  Latest Prediction Top-6: {pred}")
        if len(draws) >= 1:
            last = draws[-1]
            actual = last.reds
            hits = len(set(pred) & set(actual))
            print(f"  Actual:       {sorted(actual)}")
            print(f"  Hits: {hits}/{len(pred)}")

    # Save full history
    with open('E:/享中/evolution_history_v18.json', 'w', encoding='utf-8') as f:
        json.dump({
            "config": {
                "population_size": POPULATION_SIZE,
                "elite_count": ELITE_COUNT,
                "mutation_rate": MUTATION_RATE,
                "crossover_rate": CROSSOVER_RATE,
                "generations": N_GENERATIONS,
                "walk_forward_windows": WALK_FORWARD_WINDOWS,
            },
            "history": generation_history,
            "best_formula": best_overall.to_dict() if best_overall else None,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nHistory saved to evolution_history_v18.json")

    return best_overall


if __name__ == "__main__":
    print("Loading history...")
    draws = load_history()
    print(f"Loaded {len(draws)} draws")

    primitives = get_default_primitives()
    print(f"Using {len(primitives)} primitives")

    # 检查是否已有进化状态
    state = load_evolution_state()
    start_gen = 0
    if state:
        start_gen = state.get("generation", 0)
        print(f"Resuming from generation {start_gen}")

    best = run_evolution(draws, primitives, start_gen=start_gen, max_gens=N_GENERATIONS)
