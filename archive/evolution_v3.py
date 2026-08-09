# -*- coding: utf-8 -*-
"""
Antigravity Evolution V3.0 — 混沌边缘推演核心

修复：
1. 路径改为相对项目根目录
2. 修复 walrus operator bug（next_red_fold 未定义）
3. 期号动态计算
4. 输出格式兼容
"""
import numpy as np
import pandas as pd
import json
import os
import sys
from pathlib import Path

# ─── 相对路径 ─────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent

try:
    from quantum_denoiser import QuantumDenoiser
except ImportError:
    # 降级：提供简易降噪器
    class QuantumDenoiser:
        def __init__(self, window_size=50):
            self.window_size = window_size
        def decompose_and_reconstruct(self, series):
            # 简单移动平均降噪
            s = pd.Series(series)
            return s.rolling(window=min(self.window_size, len(s)), min_periods=1).mean().values

try:
    from sklearn.manifold import SpectralEmbedding
except ImportError:
    SpectralEmbedding = None

# 强制 UTF-8 环境
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class EvolutionV3:
    def __init__(self, history_path=None):
        if history_path is None:
            candidates = [
                _PROJECT_ROOT / "data" / "lottery_history.csv",
                _PROJECT_ROOT / "data" / "ssq_history.csv",
                _PROJECT_ROOT / "ssq_history_full.csv",
            ]
            for c in candidates:
                if c.exists():
                    history_path = str(c)
                    break
            if history_path is None:
                print("❌ 未找到历史数据文件")
                return
        self.history_path = history_path
        self.denoiser = QuantumDenoiser(window_size=50)

    def calculate_v3(self):
        print("[PROCESS] Evolution V3.0: Navigating the edge of chaos...")
        df = pd.read_csv(self.history_path)

        # 1. 数据准备
        red_points = np.array([list(map(int, r.split(','))) for r in df['red']])
        blue_points = df['blue'].values.astype(float)

        # 2. 对每一个红球位置进行 SSA 降噪
        print("[LOG] Applying SSA Denoising to all dimensions...")
        clean_reds = []
        for i in range(6):
            clean_dim = self.denoiser.decompose_and_reconstruct(red_points[:, i])
            clean_reds.append(clean_dim)
        clean_reds = np.array(clean_reds).T

        # 3. 对蓝球进行降噪
        clean_blue = self.denoiser.decompose_and_reconstruct(blue_points)

        # 4. 流形嵌入
        if SpectralEmbedding is not None:
            print("[LOG] Analyzing attractors in cleaned manifold space...")
            se = SpectralEmbedding(n_components=6, affinity='nearest_neighbors')
            embedding = se.fit_transform(clean_reds[-min(500, len(clean_reds)):])

            last_point = embedding[-1]
            prev_point = embedding[-2]
            momentum = last_point - prev_point
            next_fold = last_point + momentum * 0.5
        else:
            # 降级：使用动量法
            print("[LOG] sklearn unavailable, using momentum fallback...")
            last_red = clean_reds[-1]
            prev_red = clean_reds[-2]
            next_fold = last_red + (last_red - prev_red) * 0.5

        # 5. 映射回 1-33 空间
        base_reds = clean_reds[-1]
        final_reds = []
        for i in range(min(6, len(next_fold))):
            r = int(round(base_reds[i] + next_fold[i] * 10))
            r = max(1, min(33, r))
            while r in final_reds:
                r = (r % 33) + 1
            final_reds.append(r)

        final_blue = int(round(clean_blue[-1]))
        final_blue = max(1, min(16, final_blue))

        # 动态期号
        latest_period = int(df['period'].iloc[0])
        next_period = latest_period + 1

        result = {
            "period": str(next_period),
            "red": sorted(final_reds),
            "blue": final_blue,
            "engine": "Chaos Evolution V3.0 (SSA + Momentum Manifold)",
            "status": "Quantum Stabilized"
        }

        # 输出
        output_path = _PROJECT_ROOT / "latest_decision.json"
        with open(str(output_path), "w", encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print(f"[SUCCESS] V3.0 Evolution Complete: Red {result['red']} | Blue {result['blue']}")
        return result


if __name__ == "__main__":
    evolver = EvolutionV3()
    if evolver.history_path:
        evolver.calculate_v3()
