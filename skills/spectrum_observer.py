import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import TSNE
import os
import sys

# 强制 UTF-8 环境
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def generate_spectrum():
    print("[PROCESS] Spectrum Observer V3: Robust visual sensing...")
    history_path = r"e:\享中\ssq_history_full.csv"
    output_dir = r"e:\享中\visuals"
    
    # 路径确保逻辑
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    df = pd.read_csv(history_path)
    
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
    
    heatmap_path = os.path.join(output_dir, "gravity_heatmap.png")
    plt.savefig(heatmap_path)
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
    
    projection_path = os.path.join(output_dir, "manifold_projection.png")
    plt.savefig(projection_path)
    print(f"[SUCCESS] Projection captured: {projection_path}")
    
    plt.close('all')

if __name__ == "__main__":
    try:
        generate_spectrum()
    except Exception as e:
        print(f"[ERROR] Visualization failed: {e}")
