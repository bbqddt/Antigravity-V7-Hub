import numpy as np
import pandas as pd
import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

def permutation_entropy(time_series, order=3, delay=1):
    """
    计算排列熵 (Permutation Entropy)
    用于量化序列的混沌程度。熵值越低，规律性越强。
    """
    x = np.array(time_series)
    hashmult = np.power(order, np.arange(order))
    embedded = np.array([x[i:i+order*delay:delay] for i in range(len(x)-order*delay)])
    sorted_idx = embedded.argsort(kind='quicksort', axis=1)
    hashvalues = (sorted_idx * hashmult).sum(1)
    _, counts = np.unique(hashvalues, return_counts=True)
    probs = counts / counts.sum()
    return -np.sum(probs * np.log2(probs))

class ChaosEngine:
    """
    🔱 Antigravity Chaos Engine - 混沌熵分析引擎
    通过排列熵寻找 20 年历史长河中“最不随机”的时刻。
    """
    def __init__(self, history_path):
        self.history_path = history_path

    def analyze_entropy(self):
        print("[PROCESS] Chaos Engine: Analyzing 20-year Entropy spectrum...")
        df = pd.read_csv(self.history_path)
        
        # 将红球序列化为单一时间序列
        full_series = []
        for r in df['red']:
            full_series.extend([int(n) for n in r.split(',')])
            
        # 计算全局排列熵
        pe = permutation_entropy(full_series, order=4)
        print(f"[LOG] Global Permutation Entropy: {pe:.4f}")
        
        # 局部熵扫描：寻找最近 50 期的规律性波动
        recent_pe = permutation_entropy(full_series[-300:], order=4)
        print(f"[LOG] Recent Phase Entropy (Last 50 periods): {recent_pe:.4f}")
        
        # 演进逻辑：如果最近熵值下降，说明“折叠”正在发生
        is_folding = recent_pe < pe
        print(f"[STATUS] Spacetime Folding Detected: {is_folding}")
        
        # 根据熵值调整推演权重 (此逻辑将注入总控)
        return {
            "global_pe": float(pe),
            "recent_pe": float(recent_pe),
            "is_folding": bool(is_folding)
        }

if __name__ == "__main__":
    engine = ChaosEngine(_PROJECT_ROOT / 'data' / 'lottery_history.csv')
    engine.analyze_entropy()
