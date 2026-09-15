# -*- coding: utf-8 -*-
"""
Antigravity 公式语言 — 原语变异器 V2.0 (修复双重变异)

修复的问题:
- V1.0 中 mutate() 内部调用 primitive.mutate() 又再做一层变异
- 导致双重随机化，每代几乎完全随机，退化成无效搜索
- V2.0 只在一处做变异，保持可控的进化压力

核心理念:
- 变异 = 参数微调 (高斯扰动) + 逻辑调整 (窗口/阈值变化)
- 变异幅度随代数递减 (模拟退火策略)
- 保留精英原语，防止退化
"""
import random
import copy
from typing import Optional, Any
from formula_lang.primitive import Primitive


class PrimitiveMutator:
    """原语变异器 V2.0 — 单一变异源，可控进化压力"""

    def __init__(self, logical_rate: float = 0.2, param_rate: float = 0.4,
                 annealing_factor: float = 0.95):
        """
        Args:
            logical_rate: 逻辑级变异概率
            param_rate: 参数级变异概率
            annealing_factor: 退火因子 — 变异幅度随代数递减
        """
        self.logical_rate = logical_rate
        self.param_rate = param_rate
        self.annealing_factor = annealing_factor
        self.current_generation = 0

    def mutate(self, primitive: Primitive, draws: Any,
               rng: Optional[random.Random] = None,
               generation: int = 0) -> Primitive:
        """
        变异一个原语 — 单一变异源。

        不再调用 primitive.mutate()，在这里统一做变异。

        Args:
            primitive: 要变异的原语
            draws: 历史数据（用于指导变异方向）
            rng: 随机数生成器
            generation: 当前代数（用于退火控制变异幅度）

        Returns:
            变异后的新原语
        """
        rng = rng or random.Random()
        mutated = copy.deepcopy(primitive)

        # 退火控制: 变异幅度随代数递减
        annealing = self.annealing_factor ** generation
        param_sigma = 0.2 * annealing  # 从0.2逐渐降到0
        logical_factor_choices = [0.5, 0.7, 1.3, 1.5]  # 去掉2.0，更温和

        # 参数级变异
        if rng.random() < self.param_rate:
            for key in mutated.parameters:
                if isinstance(mutated.parameters[key], (int, float)):
                    if rng.random() < 0.5:
                        # 高斯扰动
                        mutated.parameters[key] *= (1 + rng.gauss(0, param_sigma))
                    else:
                        # 边界内随机重置
                        val = mutated.parameters[key]
                        if 0 < val < 1:
                            mutated.parameters[key] = rng.uniform(0, 1)
                        elif val < 10:
                            mutated.parameters[key] = rng.uniform(val * 0.5, val * 1.5)
                        else:
                            mutated.parameters[key] = max(10, int(rng.gauss(val, val * 0.1)))

        # 逻辑级变异
        if rng.random() < self.logical_rate:
            self._logical_mutate(mutated, rng, logical_factor_choices)

        mutated.parents = [primitive.uuid]
        mutated.birth_time = __import__('datetime').datetime.now().isoformat()
        mutated.origin = "evolved"

        return mutated

    def _logical_mutate(self, primitive: Primitive, rng: random.Random,
                        factor_choices: list):
        """逻辑级变异 — 温和地调整参数"""
        if primitive.category == "temporal":
            for key in ["window", "recent_window", "far_window", "lookback", "season_size"]:
                if key in primitive.parameters and primitive.parameters[key] > 5:
                    factor = rng.choice(factor_choices)
                    primitive.parameters[key] = int(primitive.parameters[key] * factor)
                    break

        elif primitive.category == "relational":
            for key in ["threshold"]:
                if key in primitive.parameters:
                    primitive.parameters[key] = max(0.01,
                        primitive.parameters[key] * rng.uniform(0.5, 1.5))

        elif primitive.category == "spectral":
            for key in ["min_peaks"]:
                if key in primitive.parameters:
                    primitive.parameters[key] = max(1,
                        primitive.parameters[key] + rng.choice([-1, 0, 1]))

        elif primitive.category == "chaotic":
            for key in ["dim", "tau"]:
                if key in primitive.parameters:
                    primitive.parameters[key] = max(2, min(5,
                        primitive.parameters[key] + rng.choice([-1, 0, 1])))

    def breed(self, p1: Primitive, p2: Primitive, draws: Any,
              rng: Optional[random.Random] = None) -> Primitive:
        """杂交两个原语"""
        if p1.category != p2.category:
            return rng.choice([p1, p2]) if rng else p1

        rng = rng or random.Random()
        if rng.random() < 0.5:
            child = copy.deepcopy(p1)
            child.parameters = dict(p2.parameters)
        else:
            child = copy.deepcopy(p2)
            child.parameters = dict(p1.parameters)

        child.parents = [p1.uuid, p2.uuid]
        child.origin = "breed"
        child.birth_time = __import__('datetime').datetime.now().isoformat()
        return child
