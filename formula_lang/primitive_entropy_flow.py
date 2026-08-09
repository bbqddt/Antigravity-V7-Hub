# -*- coding: utf-8 -*-
"""
entropy_flow - LLM 提案生成的原语
类别: 信息论
逻辑: 计算滚动近似熵 或排列熵 的一阶差分，量化 '确定性流失/生成' 速率。熵降=结构生成(趋势/模式形成)，熵增=结构破坏(反转/噪声)。
"""
import numpy as np
from formula_lang.primitive import Primitive

class entropy_flow(Primitive):
    """计算滚动近似熵/排列熵的一阶差分，量化确定性流失/生成速率。"""
    
    def __init__(self, window: int = 20, dim: int = 3, lag: int = 1):
        super().__init__(
            name="entropy_flow",
            category="信息论",
            description="滚动近似熵/排列熵差分，量化结构生成/破坏速率",
            parameters={"window": window, "dim": dim, "lag": lag},
            origin="auto"
        )
        self.window = window
        self.dim = dim
        self.lag = lag
    
    def _approx_entropy(self, signal, m=2, r=0.2):
        """计算近似熵"""
        N = len(signal)
        if N < m + 1:
            return 0.0
        
        def _phi(m):
            patterns = [tuple(signal[i:i+m]) for i in range(N - m + 1)]
            counts = {}
            for p in patterns:
                counts[p] = counts.get(p, 0) + 1
            phi = sum(c * np.log(c / (N - m + 1)) for c in counts.values()) / (N - m + 1)
            return phi
        
        return _phi(m) - _phi(m + 1)
    
    def _permutation_entropy(self, signal, m=3, delay=1):
        """计算排列熵"""
        N = len(signal)
        if N < m * delay:
            return 0.0
        
        patterns = {}
        for i in range(N - (m - 1) * delay):
            pattern = tuple(sorted(range(m), key=lambda k: signal[i + k * delay]))
            patterns[pattern] = patterns.get(pattern, 0) + 1
        
        total = sum(patterns.values())
        if total == 0:
            return 0.0
        
        probs = np.array(list(patterns.values())) / total
        return -np.sum(probs * np.log(probs + 1e-10))
    
    def compute(self, draws) -> np.ndarray:
        if not draws or len(draws) < self.window + 5:
            return np.ones(33) / 33
        
        scores = np.ones(33) / 33
        
        # 对每个号码计算出现序列的熵流
        for n in range(1, 34):
            # 构建二进制出现序列
            recent = min(self.window + 10, len(draws))
            signal = np.array([1.0 if n in d.reds else 0.0 for d in draws[-recent:]])
            
            if len(signal) < 10:
                continue
            
            # 计算滚动熵
            entropies = []
            for i in range(len(signal) - self.window + 1):
                window_signal = signal[i:i + self.window]
                # 使用排列熵（更稳健）
                pe = self._permutation_entropy(window_signal, m=self.dim, delay=self.lag)
                entropies.append(pe)
            
            if len(entropies) >= 2:
                # 一阶差分：熵变化率
                entropy_diff = np.diff(entropies)
                # 熵降(负值)=结构生成，熵增(正值)=结构破坏
                mean_diff = np.mean(entropy_diff)
                scores[n-1] = max(0, -mean_diff)  # 熵降得高分
        
        # 归一化
        if scores.sum() > 0:
            scores = scores / scores.sum()
        return scores

from formula_lang.primitive import PrimitiveFactory
PrimitiveFactory.entropy_flow = staticmethod(lambda **kwargs: entropy_flow(**kwargs))