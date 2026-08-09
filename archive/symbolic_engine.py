import numpy as np
from gplearn.genetic import SymbolicRegressor
import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

class SymbolicEvolutionEngine:
    """
    🔱 Antigravity Symbolic Evolution - 符号回归演化引擎
    通过遗传算法，不参考人类已知理论，自主演化出解释 20 年历史的纯数学方程。
    """
    def __init__(self, history_path):
        self.history_path = history_path

    def run_evolution(self):
        print("[Antigravity] Symbolic Evolution Started: Searching for Universal Physical Laws...")
        # 1. 加载 20 年真理
        with open(self.history_path, "r", encoding='utf-8') as f:
            data = json.load(f)
        
        # 转化为 X (期数) -> y (红球和值/特定位)
        X = np.array([i for i in range(len(data))]).reshape(-1, 1)
        # 假设我们进化红球和值的解释方程
        y = np.array([sum([int(n) for n in entry['红球'].split(',')]) for entry in data])
        
        # 2. 遗传算法演化 (Symbolic Regression)
        est_gp = SymbolicRegressor(population_size=1000,
                                   generations=10, stopping_criteria=0.01,
                                   p_crossover=0.7, p_subtree_mutation=0.1,
                                   p_hoist_mutation=0.05, p_point_mutation=0.1,
                                   max_samples=0.9, verbose=1,
                                   parsimony_coefficient=0.01, random_state=0)
        
        est_gp.fit(X, y)
        
        print("-" * 40)
        print(f"DONE: Evolution finished! Optimal Equation: {est_gp._program}")
        return str(est_gp._program)

if __name__ == "__main__":
    engine = SymbolicEvolutionEngine(_PROJECT_ROOT / 'history_truth.json')
    engine.run_evolution()
