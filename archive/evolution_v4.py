# -*- coding: utf-8 -*-
"""
Antigravity Evolution V4.0 — 连号共振与时空校准核心

修复：
1. 路径改为相对项目根目录
2. 期号动态计算
3. 兼容 sklearn 缺失情况
"""
import numpy as np
import pandas as pd
import json
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent

try:
    from quantum_denoiser import QuantumDenoiser
except ImportError:
    class QuantumDenoiser:
        def __init__(self, window_size=40):
            self.window_size = window_size
        def decompose_and_reconstruct(self, series):
            s = pd.Series(series)
            return s.rolling(window=min(self.window_size, len(s)), min_periods=1).mean().values

try:
    from sklearn.manifold import SpectralEmbedding
except ImportError:
    SpectralEmbedding = None

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class EvolutionV4:
    def __init__(self, history_path=None):
        if history_path is None:
            candidates = [
                _PROJECT_ROOT / "data" / "lottery_history.csv",
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
        self.denoiser = QuantumDenoiser(window_size=40)

    def calculate_v4(self):
        print("[PROCESS] Evolution V4.0: Calibrating spacetime anchors...")
        df = pd.read_csv(self.history_path)

        latest_period = int(df.iloc[0]['period'])
        target_period = latest_period + 1
        print(f"[LOG] Latest observed: {latest_period} | Target: {target_period}")

        # 1. 提取最新特征
        red_points = np.array([list(map(int, r.split(','))) for r in df['red']])

        # 2. 连号特征分析
        def count_consecutive(reds):
            reds = sorted(reds)
            count = 0
            for i in range(len(reds) - 1):
                if reds[i + 1] - reds[i] == 1:
                    count += 1
            return count

        n_recent = min(100, len(red_points))
        consecutive_trend = [count_consecutive(r) for r in red_points[:n_recent]]
        avg_consecutive = np.mean(consecutive_trend)
        print(f"[LOG] Average consecutive trend: {avg_consecutive:.2f}")

        # 3. 蓝球降噪
        blue_points = df['blue'].values.astype(float)
        clean_blue = self.denoiser.decompose_and_reconstruct(blue_points)

        last_blue = blue_points[0]
        blue_diff = last_blue - clean_blue[0]
        target_blue = int(round(clean_blue[0] - blue_diff * 0.5))
        target_blue = max(1, min(16, target_blue))

        # 4. 红球流形预测
        if SpectralEmbedding is not None:
            se = SpectralEmbedding(n_components=6, affinity='nearest_neighbors')
            n_emb = min(500, len(red_points))
            embedding = se.fit_transform(red_points[:n_emb])

            last_point = embedding[0]
            prev_point = embedding[1]
            momentum = last_point - prev_point
            next_fold = last_point + momentum * 0.8
        else:
            # 降级：直接基于最近数据
            print("[LOG] sklearn unavailable, using fallback...")
            last_point = red_points[0]
            prev_point = red_points[1]
            momentum = last_point - prev_point
            next_fold = last_point + momentum * 0.8

        base_reds = red_points[0]
        final_reds = []
        for i in range(min(6, len(next_fold))):
            noise = np.random.normal(0, 1.5)
            r = int(round(base_reds[i] + next_fold[i] * 5 + noise))
            r = max(1, min(33, r))
            while r in final_reds:
                r = (r % 33) + 1
            final_reds.append(r)

        result = {
            "period": str(target_period),
            "red": sorted(final_reds),
            "blue": target_blue,
            "engine": "Evolution V4.0 (Consecutive Calibration)",
            "status": "Reality Synchronized"
        }

        output_path = _PROJECT_ROOT / "latest_decision.json"
        with open(str(output_path), "w", encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print(f"[SUCCESS] V4.0 Evolution Complete: Target {target_period} | Red {result['red']} | Blue {result['blue']}")
        return result


if __name__ == "__main__":
    evolver = EvolutionV4()
    if evolver.history_path:
        evolver.calculate_v4()
