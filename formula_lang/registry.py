# -*- coding: utf-8 -*-
"""
Antigravity 公式语言 — 原语注册表 V1.0

核心理念:
- 每个原语和公式都有完整的生命周期追踪
- 记录起源、性能、变异后代、父原语
- 支持持久化和恢复

用法:
    from formula_lang.registry import PrimitiveRegistry

    reg = PrimitiveRegistry()
    reg.register(primitive, performance=None)
    reg.evolve(formula, draws, n_generations=10)
    reg.save("formula_lang/registry.json")
"""
import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

from formula_lang.primitive import Primitive, get_default_primitives
from formula_lang.grammar import Formula, FormulaGrammar
from formula_lang.evaluator import FormulaEvaluator
from formula_lang.evaluator_v3 import FormulaEvaluatorV3
from formula_lang.mutator import PrimitiveMutator

_PROJECT_ROOT = Path(__file__).resolve().parent


class PrimitiveRegistry:
    """
    原语注册表 — 管理所有原语和公式的生命周期。

    状态:
        alive: 正在使用的原语/公式
        archived: 已归档的（被淘汰但保留记录）
        eliminated: 已淘汰的（记录失败原因）
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or str(_PROJECT_ROOT / "registry.json")
        self.alive: Dict[str, Any] = {}  # uuid -> 原语或公式
        self.archived: Dict[str, Any] = {}
        self.eliminated: Dict[str, Dict] = {}  # uuid -> {reason, performance}
        self.formula_archive: List[Dict] = []  # 历史公式记录
        self.stats = {
            "total_created": 0,
            "total_eliminated": 0,
            "best_formula": None,
            "best_fitness": 0,
            "last_updated": None,
        }

    def register_primitive(self, primitive: Primitive) -> str:
        """注册一个新原语"""
        self.alive[primitive.uuid] = primitive
        self.stats["total_created"] += 1
        self.stats["last_updated"] = datetime.now().isoformat()
        return primitive.uuid

    def register_formula(self, formula: Formula, performance: Optional[Dict] = None) -> str:
        """注册一个新公式"""
        key = f"formula_{formula.name}_{len(self.alive)}"
        self.alive[key] = {
            "formula": formula,
            "performance": performance or {},
            "registered_at": datetime.now().isoformat(),
        }

    def eliminate(self, uuid: str, reason: str = "low_performance") -> bool:
        """淘汰一个原语/公式"""
        if uuid in self.alive:
            item = self.alive.pop(uuid)
            self.eliminated[uuid] = {
                "item": item if not isinstance(item, Primitive) else item.to_dict(),
                "reason": reason,
                "eliminated_at": datetime.now().isoformat(),
            }
            self.stats["total_eliminated"] += 1
            return True
        return False

    def archive(self, uuid: str) -> bool:
        """归档一个原语/公式（保留但不使用）"""
        if uuid in self.alive:
            item = self.alive.pop(uuid)
            self.archived[uuid] = {
                "item": item,
                "archived_at": datetime.now().isoformat(),
            }
            return True
        return False

    def get_alive_primitives(self) -> List[Primitive]:
        """获取所有存活的原语"""
        result = []
        for v in self.alive.values():
            if isinstance(v, Primitive):
                result.append(v)
            elif isinstance(v, dict) and "primitive" in v:
                result.append(v["primitive"])
        return result

    def get_alive_formulas(self) -> List[Dict]:
        """获取所有存活的公式"""
        return [v for v in self.alive.values()
                if isinstance(v, dict) and "formula" in v]

    def evolve(self, draws: Any, n_generations: int = 10,
               population_size: int = 20,
               survival_threshold: float = 0.1) -> Dict:
        """
        进化一代公式 — 生成→评估→选择→变异→再生成。

        Args:
            draws: 历史数据
            n_generations: 进化代数
            population_size: 每代种群大小
            survival_threshold: 存活阈值（低于此的淘汰）

        Returns:
            进化结果摘要
        """
        mutator = PrimitiveMutator()
        evaluator = FormulaEvaluatorV3()  # V3.2: dual metric (Brier + Hits)
        rng = random.Random()

        # 初始化: 从注册表中获取存活原语
        alive_prims = self.get_alive_primitives()
        if not alive_prims:
            # 如果没有，创建默认原语
            alive_prims = get_default_primitives()
            for p in alive_prims:
                self.register_primitive(p)

        results = {"generations": []}

        for gen in range(n_generations):
            # 1. 生成公式（随机组合原语）
            population = []
            for _ in range(population_size):
                n_prims = rng.randint(2, min(4, len(alive_prims)))
                selected = rng.sample(alive_prims, n_prims)
                op = rng.choice(["resonance", "cascade", "phase_align", "weighted_sum"])
                formula = getattr(FormulaGrammar, op)(selected, name=f"gen{gen}_formula{len(population)}")
                population.append(formula)

            # 2. 评估
            eval_results = evaluator.evaluate_batch(population, draws, n_windows=8, window_size=300, step=30)

            # 3. 排序
            scored = []
            for i, formula in enumerate(population):
                name = f"gen{gen}_formula{i}"
                perf = eval_results.get(name, eval_results.get(formula.name, {}))
                scored.append((formula, perf))

            scored.sort(key=lambda x: -x[1].get("combined_score", x[1].get("avg_hits", 0)))

            # 4. 记录最佳
            best_formula, best_perf = scored[0]
            results["generations"].append({
                "generation": gen + 1,
                "best_formula": best_formula.name,
                "best_combined_score": best_perf.get("combined_score", best_perf.get("avg_hits", 0)),
                "best_avg_hits": best_perf.get("avg_hits", 0),
                "best_avg_brier": best_perf.get("avg_brier", 0),
                "stable": best_perf.get("stability", 0),
            })

            if best_perf.get("combined_score", 0) > self.stats.get("best_fitness", 0):
                self.stats["best_formula"] = best_formula.name
                self.stats["best_fitness"] = best_perf.get("combined_score", best_perf.get("avg_hits", 0))

            # 5. 选择前30%
            n_survivors = max(1, len(scored) // 3)
            survivors = scored[:n_survivors]

            # 6. 变异 + 再生成下一代
            new_population = []
            for formula, perf in survivors:
                # 变异原语
                for p in formula.primitives:
                    if rng.random() < 0.3:
                        mutated = mutator.mutate(p, draws, rng)
                        self.register_primitive(mutated)
                        # 替换
                        idx = formula.primitives.index(p)
                        formula.primitives[idx] = mutated

                # 也可能重新组合
                if rng.random() < 0.5:
                    n_prims = rng.randint(2, min(4, len(self.get_alive_primitives())))
                    selected = rng.sample(self.get_alive_primitives(), n_prims)
                    op = rng.choice(["resonance", "cascade", "phase_align"])
                    new_formula = getattr(FormulaGrammar, op)(selected, name=f"mutated_gen{gen}")
                    new_population.append(new_formula)
                else:
                    new_population.append(formula)

            alive_prims = [p for f, _ in survivors for p in f.primitives]
            alive_prims = list(set(alive_prims))

        # 保存进化结果
        self.formula_archive.extend(results["generations"])
        self._save()

        return results

    def save(self, path: Optional[str] = None):
        """保存到文件"""
        p = path or self.path
        data = {
            "alive": {k: (v.to_dict() if isinstance(v, Primitive) else v) for k, v in self.alive.items()},
            "archived": self.archived,
            "eliminated": self.eliminated,
            "formula_archive": self.formula_archive[-50:],  # 只保留最近50条
            "stats": self.stats,
            "updated_at": datetime.now().isoformat(),
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: Optional[str] = None):
        """从文件加载"""
        p = path or self.path
        if not Path(p).exists():
            return

        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.alive = data.get("alive", {})
        self.archived = data.get("archived", {})
        self.eliminated = data.get("eliminated", {})
        self.formula_archive = data.get("formula_archive", [])
        self.stats = data.get("stats", self.stats)

    def _save(self):
        """内部保存"""
        self.save()

    def summary(self) -> Dict:
        """获取注册表摘要"""
        return {
            "alive_count": len(self.alive),
            "archived_count": len(self.archived),
            "eliminated_count": len(self.eliminated),
            "total_created": self.stats.get("total_created", 0),
            "total_eliminated": self.stats.get("total_eliminated", 0),
            "best_formula": self.stats.get("best_formula"),
            "best_fitness": self.stats.get("best_fitness", 0),
            "last_updated": self.stats.get("last_updated"),
        }
