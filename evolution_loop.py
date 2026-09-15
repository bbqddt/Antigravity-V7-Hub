# -*- coding: utf-8 -*-
"""
Antigravity 进化循环 V1.0 — 开发→评估→留优→迭代

核心理念：
1. 不断开发新公式（原语组合）
2. 用全部历史数据评估每个公式的 Brier Score
3. 准确高的公式留用，差的淘汰
4. 留用的公式与新公式组合，生成下一代
5. 一代一代优化，但每代都要过 walk-forward 检验

关键设计：
- 不用短期数据（20期），用全部 3472 期
- 不追求"碰巧命中高"，追求"Brier Score 低"
- 权重缓慢衰减(alpha=0.05)，不让一两期决定生死
- 泛化检验：训练集 vs 测试集的差距不能太大
"""
import sys
import math
import json
import os
import random
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Optional, Any

# Fix Windows GBK encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# 项目根目录
_PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(_PROJECT_ROOT))

from data_layer import load_history, Draw
from formula_lang.primitive import (
    Primitive, get_default_primitives,
    PeriodicEcho, RecencyGradient, SeasonalResonance,
    CooccurrenceAffinity, MutualExclusionScore, PairOrbit,
    BinaryTopology, DigitManifold, PositionSignature,
    SpectralPower, WaveletCoherence,
    SphereProjection, DistanceCluster,
    AttractorDistance, LyapunovSignal,
    SumRangeTracker, GapPatternAnalyzer, TrendReversalDetector,
    ModuloClassDistribution, DigitPairFrequency, AdjacentNumberBias,
    SkewnessSignal, KurtosisSignal, TailRiskSignal,
    LagCorrelation, PeriodicGap, RecurrenceWindow,
    MultiScaleFrequency, ScaleTransition,
    EnvironmentAware, PhaseDetector, RegimeSwitch,
)
from formula_lang.grammar import Formula, FormulaGrammar
from formula_lang.evaluator_v3 import FormulaEvaluatorV3
from formula_lang.weight_manager import FormulaWeightManager


# ─── 配置 ─────────────────────────────────────────────────
GENERATIONS = 20          # 进化代数
FORMULAS_PER_GEN = 50     # 每代生成的公式数
SURVIVAL_RATE = 0.3       # 存活率（前30%进入下一代）
MUTATION_RATE = 0.4       # 变异率（70%直接继承，40%变异）
CROSSOVER_RATE = 0.3      # 交叉率（30%由两个父公式交叉生成）
EWMA_ALPHA = 0.05         # 权重衰减因子
MIN_WEIGHT_RATIO = 0.01   # 最低权重保护
WALK_FORWARD_WINDOWS = 30 # walk-forward 窗口数
WINDOW_SIZE = 500         # 初始训练窗口
STEP = 50                 # 步进


# ─── 公式生成器 ──────────────────────────────────────────

class FormulaGenerator:
    """
    公式生成器 — 从原语库中随机组合生成新公式。

    组合策略：
    1. 单原语公式（简单基线）
    2. 双原语共振（resonance）
    3. 双原语级联（cascade）
    4. 双原语加权和（weighted_sum）
    5. 三原语相位对齐（phase_align）
    """

    def __init__(self, primitives: List[Primitive], rng: random.Random):
        self.primitives = primitives
        self.rng = rng
        self._name_counter = 0

    def _next_name(self, prefix: str) -> str:
        self._name_counter += 1
        return f"{prefix}_{self._name_counter:04d}"

    def generate(self) -> Formula:
        """随机生成一个公式"""
        strategy = self.rng.choices(
            ["single", "resonance", "cascade", "sum", "phase"],
            weights=[0.2, 0.3, 0.15, 0.25, 0.1],
            k=1
        )[0]

        if strategy == "single":
            prim = self.rng.choice(self.primitives)
            return Formula(
                name=self._next_name("P"),
                primitives=[prim],
                operators=[],
                parameters={},
            )

        elif strategy == "resonance":
            p1, p2 = self.rng.sample(self.primitives, 2)
            w1 = self.rng.uniform(0.3, 0.7)
            return FormulaGrammar.resonance(
                [p1, p2],
                weights=[w1, 1 - w1],
                name=self._next_name("R"),
            )

        elif strategy == "cascade":
            p1, p2 = self.rng.sample(self.primitives, 2)
            threshold = self.rng.uniform(0.2, 0.5)
            return FormulaGrammar.cascade(
                [p1, p2],
                thresholds=[threshold],
                name=self._next_name("C"),
            )

        elif strategy == "sum":
            p1, p2 = self.rng.sample(self.primitives, 2)
            w1 = self.rng.uniform(0.3, 0.7)
            return FormulaGrammar.weighted_sum(
                [p1, p2],
                weights=[w1, 1 - w1],
                name=self._next_name("S"),
            )

        else:  # phase
            p1, p2, p3 = self.rng.sample(self.primitives, 3)
            offsets = [self.rng.uniform(0.3, 0.7) for _ in range(2)]
            return FormulaGrammar.phase_align(
                [p1, p2, p3],
                offsets=offsets,
                name=self._next_name("PA"),
            )

    def mutate(self, parent: Formula) -> Formula:
        """变异一个已有公式"""
        if not parent.primitives:
            return self.generate()

        # 策略1: 替换一个原语
        if self.rng.random() < 0.5 and len(parent.primitives) >= 1:
            new_prim = self.rng.choice(self.primitives)
            mutated_prims = list(parent.primitives)
            idx = self.rng.randint(0, len(mutated_prims) - 1)
            mutated_prims[idx] = new_prim
            return Formula(
                name=self._next_name(f"M_{parent.name}"),
                primitives=mutated_prims,
                operators=list(parent.operators),
                parameters=dict(parent.parameters),
            )

        # 策略2: 添加一个原语
        if self.rng.random() < 0.3:
            new_prim = self.rng.choice(self.primitives)
            mutated_prims = list(parent.primitives) + [new_prim]
            # 重新计算权重
            n = len(mutated_prims)
            weights = [1.0 / n] * n
            params = {f"weight_{i}": weights[i] for i in range(n - 1)}
            return Formula(
                name=self._next_name(f"A_{parent.name}"),
                primitives=mutated_prims,
                operators=["sum"] * (n - 1),
                parameters=params,
            )

        # 策略3: 调参数
        mutated = Formula(
            name=self._next_name(f"P_{parent.name}"),
            primitives=list(parent.primitives),
            operators=list(parent.operators),
            parameters=dict(parent.parameters),
        )
        for key in mutated.parameters:
            if isinstance(mutated.parameters[key], float):
                mutated.parameters[key] *= self.rng.gauss(1, 0.15)
                mutated.parameters[key] = max(0.01, min(1.0, mutated.parameters[key]))
        return mutated

    def crossover(self, parent_a: Formula, parent_b: Formula) -> Formula:
        """两个父公式交叉生成子公式"""
        if not parent_a.primitives or not parent_b.primitives:
            return self.generate()

        # 取 A 的部分原语 + B 的部分原语
        all_prims = parent_a.primitives + parent_b.primitives
        n_take = max(1, len(all_prims) // 2)
        chosen = self.rng.sample(all_prims, min(n_take, len(all_prims)))

        if len(chosen) == 1:
            return Formula(
                name=self._next_name(f"X_{parent_a.name[:6]}_{parent_b.name[:6]}"),
                primitives=chosen,
                operators=[],
                parameters={},
            )

        strategy = self.rng.choice(["sum", "resonance"])
        if strategy == "sum":
            n = len(chosen)
            weights = [1.0 / n] * n
            params = {f"weight_{i}": weights[i] for i in range(n - 1)}
            return Formula(
                name=self._next_name(f"X_{parent_a.name[:6]}_{parent_b.name[:6]}"),
                primitives=chosen,
                operators=["sum"] * (n - 1),
                parameters=params,
            )
        else:
            weights = [1.0 / len(chosen)] * len(chosen)
            return FormulaGrammar.resonance(
                chosen,
                weights=weights,
                name=self._next_name(f"X_{parent_a.name[:6]}_{parent_b.name[:6]}"),
            )


# ─── 公式进化循环 ─────────────────────────────────────────

class EvolutionLoop:
    """
    公式进化循环

    流程：
    1. 初始化：从原语库生成第一代公式
    2. 评估：全量历史 walk-forward 评估每个公式
    3. 选择：保留前 SURVIVAL_RATE 的公式
    4. 繁殖：存活公式 + 变异 + 交叉 → 新一代
    5. 重复步骤 2-4，共 GENERATIONS 代
    """

    def __init__(self, draws: List[Draw], rng_seed: int = 42):
        self.draws = draws
        self.rng = random.Random(rng_seed)

        # 获取所有原语
        self.all_primitives = get_default_primitives()
        print(f"[Init] 加载 {len(self.all_primitives)} 个原语")

        # 权重管理器（跨代持久化）
        self.weight_manager = FormulaWeightManager(
            alpha=EWMA_ALPHA, min_weight=MIN_WEIGHT_RATIO
        )

        # 公式库
        self.formula_pool: Dict[str, Formula] = {}  # name -> formula
        self.formula_scores: Dict[str, Dict] = {}   # name -> evaluation result
        self.formula_weights: Dict[str, float] = {} # name -> ewma weight

        # 历史记录
        self.generation_history: List[Dict] = []
        self.best_formulas_overall: List[Dict] = []

    def initialize_generation(self, n: int = FORMULAS_PER_GEN) -> List[Formula]:
        """生成第一代公式"""
        generator = FormulaGenerator(self.all_primitives, self.rng)
        formulas = []
        for _ in range(n):
            f = generator.generate()
            self.formula_pool[f.name] = f
            formulas.append(f)
        print(f"[Gen 0] 初始化 {len(formulas)} 个公式")
        return formulas

    def evolve_generation(self, parents: List[Formula]) -> List[Formula]:
        """
        从父代生成子代。

        策略：
        - 60% 直接继承最优公式
        - 40% 变异
        - 30% 交叉（从变异中选择）
        - 保底：至少生成 FORMULAS_PER_GEN 个公式
        """
        generator = FormulaGenerator(self.all_primitives, self.rng)
        children = []

        if not parents:
            # 种群崩溃，重新初始化
            print("[Evolve] ⚠️  无父代，重新初始化")
            for _ in range(FORMULAS_PER_GEN):
                f = generator.generate()
                self.formula_pool[f.name] = f
                children.append(f)
            return children

        # 保留部分最优公式
        n_elite = max(2, int(len(parents) * 0.6))
        elite = parents[:n_elite]
        for f in elite:
            self.formula_pool[f.name] = f
            children.append(f)

        # 变异
        n_mutate = max(2, int(len(parents) * MUTATION_RATE))
        for _ in range(n_mutate):
            parent = self.rng.choice(elite)
            child = generator.mutate(parent)
            self.formula_pool[child.name] = child
            children.append(child)

        # 交叉
        n_crossover = max(1, int(len(parents) * CROSSOVER_RATE))
        for _ in range(n_crossover):
            if len(elite) >= 2:
                pa, pb = self.rng.sample(elite, 2)
                child = generator.crossover(pa, pb)
                self.formula_pool[child.name] = child
                children.append(child)

        # 保底：如果公式数不够，补充随机生成
        while len(children) < FORMULAS_PER_GEN:
            f = generator.generate()
            self.formula_pool[f.name] = f
            children.append(f)

        print(f"[Evolve] 父代={len(parents)}, 精英={n_elite}, "
              f"变异={n_mutate}, 交叉={n_crossover}, 子代={len(children)}")
        return children

    def evaluate_generation(self, formulas: List[Formula]) -> Dict[str, Dict]:
        """
        评估一代公式：全量历史 walk-forward + Brier Score。
        """
        evaluator = FormulaEvaluatorV3()
        results = evaluator.evaluate_batch(
            formulas,
            self.draws,
            n_windows=WALK_FORWARD_WINDOWS,
            window_size=WINDOW_SIZE,
            step=STEP,
        )

        # 打印评估结果
        print(f"\n--- 评估结果 ({len(results)} 个公式) ---")
        ranked = sorted(results.items(), key=lambda x: x[1].get("red_brier", 999))
        print(f"{'公式':<25} | {'红球Brier':>10} | {'优于随机':>8} | {'稳定性':>8} | {'泛化差距':>10}")
        print("-" * 75)
        for name, r in ranked[:15]:
            avg_b = r.get("red_brier", 0)
            beats = "✅" if r.get("beats_random") else "❌"
            stab = r.get("stability_std", 0)
            gap = r.get("generalization_gap", 0)
            print(f"  {name:<23} | {avg_b:>10.4f} | {beats:>8} | {stab:>8.4f} | {gap:>10.4f}")

        return results

    def select_survivors(self, results: Dict[str, Dict],
                         survival_rate: float = SURVIVAL_RATE) -> List[tuple]:
        """
        选择存活公式：按 Brier Score 排序，保留前 survival_rate。

        额外条件：
        - 泛化差距 < 0.05（放宽阈值）
        - 至少 10 轮验证
        - 保底保留至少 5 个公式，防止种群崩溃
        """
        # 过滤掉不合格的
        valid = {}
        for name, r in results.items():
            gap = r.get("generalization_gap", 1.0)
            rounds = r.get("rounds", 0)
            if gap < 0.05 and rounds >= 10:
                valid[name] = r

        # 按 Brier 排序
        ranked = sorted(valid.items(), key=lambda x: x[1].get("red_brier", 999))

        # 保底：至少保留 5 个，或者 survival_rate 的数量
        n_survive = max(5, int(len(ranked) * survival_rate))

        # 如果有效公式不够，从所有结果中补充
        if len(ranked) < n_survive:
            all_ranked = sorted(results.items(), key=lambda x: x[1].get("red_brier", 999))
            ranked = all_ranked[:n_survive]
        else:
            ranked = ranked[:n_survive]

        print(f"\n[Survive] {len(ranked)}/{len(results)} 公式存活 (阈值: gap<0.05, rounds>=10)")
        for name, r in ranked:
            print(f"  {name}: Brier={r['red_brier']:.4f}, gap={r['generalization_gap']:.4f}")

        return ranked

    def run(self) -> Dict:
        """运行完整的进化循环"""
        print("=" * 72)
        print("  🧬 Antigravity 公式进化循环 V1.0")
        print("=" * 72)
        print(f"代数: {GENERATIONS}, 每代公式: {FORMULAS_PER_GEN}")
        print(f"存活率: {SURVIVAL_RATE}, 变异率: {MUTATION_RATE}, 交叉率: {CROSSOVER_RATE}")
        print(f"Walk-Forward: {WALK_FORWARD_WINDOWS} 窗口, 窗口大小: {WINDOW_SIZE}")
        print(f"全量历史数据: {len(self.draws)} 期 (#{self.draws[0].period} ~ #{self.draws[-1].period})")
        print()

        # 第 0 代：初始化
        current_generation = self.initialize_generation(FORMULAS_PER_GEN)

        best_overall_brier = 999
        best_overall_formula = None

        for gen in range(1, GENERATIONS + 1):
            print(f"\n{'='*72}")
            print(f"  🔄 第 {gen}/{GENERATIONS} 代")
            print(f"{'='*72}")

            # 评估当前代
            results = self.evaluate_generation(current_generation)
            self.formula_scores.update(results)

            # 选择存活
            survivors = self.select_survivors(results)
            survivor_names = [name for name, _ in survivors]
            surviving_formulas = [self.formula_pool[name] for name, _ in survivors]

            # 记录本代统计
            avg_brier = sum(r.get("red_brier", 999) for _, r in survivors) / max(len(survivors), 1)
            best_in_gen = min(survivors, key=lambda x: x[1].get("red_brier", 999))

            gen_record = {
                "generation": gen,
                "formulas_evaluated": len(results),
                "survivors": len(survivors),
                "avg_survivor_brier": round(avg_brier, 6),
                "best_formula": best_in_gen[0],
                "best_brier": best_in_gen[1].get("red_brier", 999),
                "timestamp": datetime.now().isoformat(),
            }
            self.generation_history.append(gen_record)

            print(f"\n[Gen {gen}] 平均 Brier: {avg_brier:.4f}, "
                  f"最佳: {best_in_gen[0]} (Brier={best_in_gen[1].get('red_brier', 0):.4f})")

            # 更新全局最优
            if best_in_gen[1].get("red_brier", 999) < best_overall_brier:
                best_overall_brier = best_in_gen[1]["red_brier"]
                best_overall_formula = best_in_gen[0]
                self.best_formulas_overall.append({
                    "generation": gen,
                    "name": best_in_gen[0],
                    "brier": best_overall_brier,
                    "details": best_in_gen[1],
                })

            # 生成下一代
            if gen < GENERATIONS:
                current_generation = self.evolve_generation(surviving_formulas)

        # 最终报告
        print(f"\n{'='*72}")
        print("  🏆 进化完成 — 最终报告")
        print(f"{'='*72}")
        print(f"\n全局最优公式: {best_overall_formula}")
        print(f"最优 Brier Score: {best_overall_brier:.4f}")
        print(f"随机基线 Brier: 0.139")
        print(f"改善幅度: {(1 - best_overall_brier / 0.139) * 100:.1f}%")

        # 保存结果
        self._save_results()

        return {
            "best_formula": best_overall_formula,
            "best_brier": best_overall_brier,
            "generations": self.generation_history,
            "best_formulas": self.best_formulas_overall,
        }

    def _save_results(self):
        """保存进化结果到文件"""
        output_dir = _PROJECT_ROOT / "evolution_output"
        output_dir.mkdir(exist_ok=True)

        # 保存完整结果
        result_path = output_dir / "evolution_result.json"
        serializable = {
            "best_formula": self.best_formulas_overall[-1]["name"] if self.best_formulas_overall else None,
            "best_brier": self.best_formulas_overall[-1]["brier"] if self.best_formulas_overall else None,
            "total_formulas_generated": len(self.formula_pool),
            "generations": self.generation_history,
            "best_formulas_history": self.best_formulas_overall,
        }
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        print(f"\n>>> 结果已保存: {result_path}")

        # 保存存活公式列表
        survivors_path = output_dir / "surviving_formulas.txt"
        with open(survivors_path, "w", encoding="utf-8") as f:
            f.write("# 存活公式列表（按 Brier Score 排序）\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            ranked = sorted(
                [(n, r) for n, r in self.formula_scores.items()],
                key=lambda x: x[1].get("red_brier", 999)
            )
            for name, r in ranked:
                beats = "✅" if r.get("beats_random") else "❌"
                f.write(f"{name}: Brier={r.get('red_brier', 0):.4f} "
                        f"Stability={r.get('stability_std', 0):.4f} "
                        f"Gap={r.get('generalization_gap', 0):.4f} "
                        f"Rounds={r.get('rounds', 0)} {beats}\n")
        print(f">>> 存活公式已保存: {survivors_path}")


# ─── 入口 ─────────────────────────────────────────────────

def main():
    print("[Data] 加载历史开奖数据...")
    draws = load_history()
    print(f"[Data] 加载 {len(draws)} 期数据 (#{draws[0].period} ~ #{draws[-1].period})")

    loop = EvolutionLoop(draws, rng_seed=42)
    result = loop.run()

    print("\n" + "=" * 72)
    print("  ✅ 进化循环完成")
    print("=" * 72)


if __name__ == "__main__":
    main()
