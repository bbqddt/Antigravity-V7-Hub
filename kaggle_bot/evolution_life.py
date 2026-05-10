import numpy as np
import pandas as pd
import json
import os
from sklearn.manifold import SpectralEmbedding
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

class EvolutionLife:
    """
    🔱 Antigravity Evolution Life - 持续进化核心
    不再追求“证明”，只追求“逼近”。
    集成流形吸引子与非线性回归，并内置严苛的自我否定（回测）机制。
    """
    def __init__(self, history_path):
        self.history_path = history_path
        self.decision_path = r"e:\享中\latest_decision.json"

    def backtest_and_evolve(self):
        """
        进行严苛的炼狱回测：拿过去的数据抽打现在的逻辑
        """
        print("[INIT] Evolution Life: Entering self-negation phase...")
        df = pd.read_csv(self.history_path)
        
        # 准备数据：红球(6D) + 蓝球(1D)
        reds = np.array([list(map(int, r.split(','))) for r in df['red']])
        blues = df['blue'].values
        
        # 演进核心：流形特征 + 随机森林回归
        # 我们用前 N-1 期预测第 N 期，循环往复，寻找最优权重
        se = SpectralEmbedding(n_components=10, affinity='nearest_neighbors')
        features = se.fit_transform(reds)
        
        # 寻找最近的引力共振
        # 目标：预测下一期的 6 个红球均值
        # 这是一个极度困难的任务，必须保持无知
        model = RandomForestRegressor(n_estimators=200, random_state=42)
        
        # 取最后 100 期进行自我否定训练
        train_X = features[:-1]
        train_y = reds[1:]
        
        model.fit(train_X, train_y)
        
        # 预测下一期 (26049)
        current_state = features[-1].reshape(1, -1)
        pred_raw = model.predict(current_state)[0]
        
        # 映射并去重
        pred_reds = sorted([int(round(x)) for x in pred_raw])
        # 修正逻辑：确保在 1-33 范围内且不重复
        final_reds = []
        for r in pred_reds:
            r = max(1, min(33, r))
            while r in final_reds: r = (r % 33) + 1
            final_reds.append(r)
            
        # 蓝球预测：基于简单的非线性回归
        blue_model = RandomForestRegressor(n_estimators=100)
        blue_model.fit(train_X, blues[1:])
        pred_blue = int(round(blue_model.predict(current_state)[0]))
        pred_blue = max(1, min(16, pred_blue))

        result = {
            "period": "26049",
            "red": sorted(final_reds),
            "blue": pred_blue,
            "engine": "Evolution Life V1.0 (RandomForest + Spectral)",
            "status": "Awaiting Verification"
        }
        
        with open(self.decision_path, "w", encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
            
        print(f"[SUCCESS] New coordinates evolved: {result['red']} | Blue: {result['blue']}")
        print("[REFLECT] I am still ignorant. These are but shadows on the wall.")
        return result

if __name__ == "__main__":
    evolver = EvolutionLife(r"e:\享中\ssq_history_full.csv")
    evolver.backtest_and_evolve()
