import numpy as np
import pandas as pd
import sys

# 强制 UTF-8 环境
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class QuantumDenoiser:
    """
    🔱 Antigravity Quantum Denoiser V1.1 - 强力兼容版
    修正了 NumPy 类型转换冲突，确保全精度浮点运算。
    """
    def __init__(self, window_size=50):
        self.L = window_size

    def decompose_and_reconstruct(self, series):
        """
        执行 SSA 分解与重构
        """
        # 强制转换为浮点数，避免类型冲突
        series = np.array(series, dtype=float)
        N = len(series)
        K = N - self.L + 1
        
        # 1. 嵌入 (Embedding)
        X = np.column_stack([series[i:i+self.L] for i in range(K)])
        
        # 2. 奇异值分解 (SVD)
        # 直接对协方差矩阵进行分解
        U, s, Vh = np.linalg.svd(X @ X.T)
        
        # 3. 提取主成分 (降噪)
        # 强制使用 float 类型的零矩阵
        X_reduced = np.zeros(X.shape, dtype=float)
        
        # 降噪：保留前 3 个奇异值成分 (增强稳定性)
        n_components = 3
        for i in range(min(n_components, len(s))):
            # 重构分量
            Ui = U[:, i].reshape(-1, 1)
            Vi = (X.T @ Ui) / np.sqrt(s[i])
            X_reduced += np.sqrt(s[i]) * (Ui @ Vi.T)
            
        # 4. 对角平均化 (Diagonal Averaging)
        reconstructed = []
        for i in range(N):
            vals = []
            for j in range(max(0, i - K + 1), min(i + 1, self.L)):
                vals.append(X_reduced[j, i - j])
            reconstructed.append(np.mean(vals))
            
        return np.array(reconstructed)

if __name__ == "__main__":
    print("[PROCESS] Quantum Denoiser V1.1: Testing SVD Reconstruction...")
    test_data = np.random.rand(100)
    denoiser = QuantumDenoiser(window_size=30)
    res = denoiser.decompose_and_reconstruct(test_data)
    print(f"[SUCCESS] Reconstruction shape: {res.shape}")
