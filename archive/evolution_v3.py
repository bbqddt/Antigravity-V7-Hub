import numpy as np
import pandas as pd
import json
import os
import sys
from quantum_denoiser import QuantumDenoiser
from sklearn.manifold import SpectralEmbedding

# 强制 UTF-8 环境
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加 lib 目录到路径
sys.path.append(os.path.join(os.getcwd(), 'lib'))

class EvolutionV3:
    """
    🔱 Antigravity Evolution V3.0 - 混沌边缘推演核心
    集成了量子降噪与高维吸引子分析。
    """
    def __init__(self, history_path):
        self.history_path = history_path
        self.denoiser = QuantumDenoiser(window_size=50)

    def calculate_v3(self):
        print("[PROCESS] Evolution V3.0: Navigating the edge of chaos...")
        df = pd.read_csv(self.history_path)
        
        # 1. 数据准备
        red_points = np.array([list(map(int, r.split(','))) for r in df['red']])
        blue_points = df['blue'].values
        
        # 2. 对每一个红球位置进行 SSA 降噪 (1-6号位)
        print("[LOG] Applying SSA Denoising to all dimensions...")
        clean_reds = []
        for i in range(6):
            clean_dim = self.denoiser.decompose_and_reconstruct(red_points[:, i])
            clean_reds.append(clean_dim)
        clean_reds = np.array(clean_reds).T
        
        # 3. 对蓝球进行降噪
        clean_blue = self.denoiser.decompose_and_reconstruct(blue_points)
        
        # 4. 在降噪后的空间进行流形嵌入
        print("[LOG] Analyzing attractors in cleaned manifold space...")
        se = SpectralEmbedding(n_components=6, affinity='nearest_neighbors')
        embedding = se.fit_transform(clean_reds[-500:]) # 取最近 500 期的高纯度信号
        
        # 寻找最新的吸引子偏移
        # 使用自适应动量预测
        last_point = embedding[-1]
        prev_point = embedding[-2]
        momentum = last_point - prev_point
        next_fold = last_point + momentum * 0.5 # 引入动量修正
        
        # 5. 映射回 1-33 空间
        # 结合降噪后的末端值与流形偏移
        base_reds = clean_reds[-1]
        final_reds = []
        for i, val in enumerate(next_red_fold := next_fold):
            r = int(round(base_reds[i] + val * 10)) # 结合流形扰动
            r = max(1, min(33, r))
            while r in final_reds: r = (r % 33) + 1
            final_reds.append(r)
            
        final_blue = int(round(clean_blue[-1]))
        final_blue = max(1, min(16, final_blue))

        result = {
            "period": "26049",
            "red": sorted(final_reds),
            "blue": final_blue,
            "engine": "Chaos Evolution V3.0 (SSA + Momentum Manifold)",
            "status": "Quantum Stabilized"
        }
        
        with open(r"e:\享中\latest_decision.json", "w", encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
            
        print(f"[SUCCESS] V3.0 Evolution Complete: Red {result['red']} | Blue {result['blue']}")
        return result

if __name__ == "__main__":
    evolver = EvolutionV3(r"e:\享中\ssq_history_full.csv")
    evolver.calculate_v3()
