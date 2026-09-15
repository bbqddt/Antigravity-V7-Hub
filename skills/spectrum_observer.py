import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import TSNE
import os
import sys
from pathlib import Path

# ─── 相对路径 ─────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_HISTORY_PATH = _PROJECT_ROOT / "data" / "lottery_history.csv"
_OUTPUT_DIR = _PROJECT_ROOT / "visuals"

def generate_spectrum():
    print("[PROCESS] Spectrum Observer V3: Robust visual sensing...")

    # 路径确保逻辑
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not _HISTORY_PATH.exists():
        print(f"[ERROR] 历史数据不存在: {_HISTORY_PATH}")
        return

    df = pd.read_csv(str(_HISTORY_PATH))
    
    # 1. 准备数据
    red_data = []
    for r in df['red']:
        red_data.append([int(n) for n in r.split(',')])
    X = np.array(red_data)
    
    # 2. 生成引力热力图 (最近 100 期)
    print("[LOG] Generating Gravity Heatmap...")
    plt.figure(figsize=(15, 8))
    recent_matrix = np.zeros((100, 33))
    for i in range(100):
        for num in red_data[-(100-i)]:
            recent_matrix[i, num-1] = 1
            
    sns.heatmap(recent_matrix.T, cmap="YlGnBu", cbar=False, yticklabels=range(1, 34))
    plt.title("Antigravity: Red Ball Gravity Heatmap (Last 100 Periods)")
    plt.xlabel("Timeline (Backwards)")
    plt.ylabel("Red Ball Number")
    
    heatmap_path = _OUTPUT_DIR / "gravity_heatmap.png"
    plt.savefig(str(heatmap_path))
    print(f"[SUCCESS] Heatmap captured: {heatmap_path}")
    
    # 3. 生成流形投影 (T-SNE)
    print("[LOG] Generating Manifold Projection (T-SNE)...")
    plt.figure(figsize=(10, 10))
    # 使用最精简的参数，确保版本兼容性
    tsne = TSNE(n_components=2, random_state=42)
    X_embedded = tsne.fit_transform(X[-500:]) 
    
    plt.scatter(X_embedded[:, 0], X_embedded[:, 1], c=range(500), cmap='magma', alpha=0.7)
    plt.colorbar(label='Timeline Progression')
    plt.title("Antigravity: Spacetime Manifold Projection (Last 500 Periods)")
    
    projection_path = _OUTPUT_DIR / "manifold_projection.png"
    plt.savefig(str(projection_path))
    print(f"[SUCCESS] Projection captured: {projection_path}")
    
    plt.close('all')

if __name__ == "__main__":
    try:
        generate_spectrum()
    except Exception as e:
        print(f"[ERROR] Visualization failed: {e}")
