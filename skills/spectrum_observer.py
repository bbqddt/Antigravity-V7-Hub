import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import SpectralEmbedding
import os
import sys

# 强制 UTF-8 环境
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class SpectrumObserver:
    """
    🔱 Antigravity Spectrum Observer - 视觉显化引擎
    将 20 年的混沌转化为肉眼可见的“真理频谱”。
    """
    def __init__(self, history_path):
        self.history_path = history_path
        self.output_dir = r"e:\享中\visuals"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def visualize(self):
        print("[PROCESS] Spectrum Observer: Rendering 20-year Spacetime Heatmap...")
        df = pd.read_csv(self.history_path)
        
        # 1. 构造红球矩阵 (3446 x 33)
        matrix = np.zeros((len(df), 33))
        for i, r in enumerate(df['red']):
            nums = [int(n) for n in r.split(',')]
            for n in nums:
                matrix[i, n-1] = 1
        
        # 2. 绘制热力频谱图
        plt.figure(figsize=(15, 8))
        sns.heatmap(matrix[-200:].T, cmap="magma", cbar=False) # 只取最近200期进行高精度展示
        plt.title("Antigravity: Spacetime Gravity Spectrum (Last 200 Periods)", fontsize=15)
        plt.xlabel("Timeline", fontsize=12)
        plt.ylabel("Red Ball Index (1-33)", fontsize=12)
        
        heatmap_path = os.path.join(self.output_dir, "gravity_spectrum.png")
        plt.savefig(heatmap_path)
        print(f"[SUCCESS] Gravity Spectrum saved to: {heatmap_path}")
        
        # 3. 绘制流形折叠散点图
        print("[PROCESS] Spectrum Observer: Projecting Manifold Fold Points...")
        red_points = np.array([list(map(int, r.split(','))) for r in df['red'][-1000:]]) # 取最近1000期进行流形映射
        se = SpectralEmbedding(n_components=2, affinity='nearest_neighbors')
        embedding = se.fit_transform(red_points)
        
        plt.figure(figsize=(10, 10))
        plt.scatter(embedding[:, 0], embedding[:, 1], c=np.arange(len(embedding)), cmap='viridis', alpha=0.6)
        plt.colorbar(label='Timeline (Darker is Older)')
        plt.title("Antigravity: Manifold Fold Topology (2D Projection)", fontsize=15)
        
        manifold_path = os.path.join(self.output_dir, "manifold_topology.png")
        plt.savefig(manifold_path)
        print(f"[SUCCESS] Manifold Topology saved to: {manifold_path}")

if __name__ == "__main__":
    observer = SpectrumObserver(r"e:\享中\ssq_history_full.csv")
    observer.visualize()
