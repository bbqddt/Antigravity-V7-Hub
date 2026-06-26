import numpy as np
import pandas as pd
from sklearn.manifold import SpectralEmbedding
from sklearn.neighbors import NearestNeighbors
import json
import os
import sys

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class ManifoldEngine:
    """
    Antigravity Manifold Engine V2.1 - 兼容版
    """
    def __init__(self, history_csv_path):
        self.history_path = history_csv_path

    def evolve_truth(self):
        print(f"[PROCESS] Engine Evolving with 3445 trajectories...")
        
        df = pd.read_csv(self.history_path)
        
        red_points = []
        for r in df['red']:
            red_points.append([int(n) for n in r.split(',')])
        
        blue_points = df['blue'].values.reshape(-1, 1)
        
        X_red = np.array(red_points)
        X_blue = np.array(blue_points)
        
        # 红球流形
        se_red = SpectralEmbedding(n_components=6, affinity='nearest_neighbors', n_neighbors=20)
        embedding_red = se_red.fit_transform(X_red)
        
        nn = NearestNeighbors(n_neighbors=10)
        nn.fit(embedding_red)
        distances, indices = nn.kneighbors([embedding_red[-1]])
        
        resonance_points = X_red[indices[0]]
        next_red_fold = np.mean(resonance_points, axis=0)
        
        extracted_reds = sorted([(int(abs(val)) % 33) + 1 for val in next_red_fold])
        final_reds = []
        for r in extracted_reds:
            while r in final_reds: r = (r % 33) + 1
            final_reds.append(r)
            
        # 蓝球流形
        se_blue = SpectralEmbedding(n_components=1, affinity='nearest_neighbors', n_neighbors=15)
        embedding_blue = se_blue.fit_transform(X_blue)
        next_blue_fold = np.mean(embedding_blue[-10:])
        final_blue = (int(abs(next_blue_fold * 16)) % 16) + 1

        result = {
            "period": "26049",
            "red": sorted(final_reds),
            "blue": int(final_blue),
            "engine": "Manifold V2.1 (Laplacian Eigenmaps)"
        }
        
        # 先落地，后打印
        with open(r"e:\享中\latest_decision.json", "w", encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
            
        print(f"[SUCCESS] Deduction Complete: Red {result['red']} | Blue {result['blue']}")
        return result

if __name__ == "__main__":
    engine = ManifoldEngine(r"e:\享中\ssq_history_full.csv")
    engine.evolve_truth()
