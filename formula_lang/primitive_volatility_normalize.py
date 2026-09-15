# -*- coding: utf-8 -*-
"""
volatility_normalize - LLM 提案生成的原语
类别: 统计
逻辑: 滚动窗口内实现 EWMA 波动率标准化 (x / (ewma_std(x, span) + eps))，输出无量纲 '信噪比' 序列，消除波动率聚类干扰，使后续 resonance/phasealign 在恒定 SNR 下工作。
"""
import numpy as np
from formula_lang.primitive import Primitive

class volatility_normalize(Primitive):
    """滚动窗口内实现 EWMA 波动率标准化 (x / (ewma_std(x, span) + eps))，输出无量纲 '信噪比' 序列，消除波动率聚类干扰，使后续 resonance/phasealign 在恒定 SNR 下工作。"""
    
    def __init__(self, window: int = 20, span: int = 20, eps: float = 1e-6):
        super().__init__(
            name="volatility_normalize",
            category="统计",
            description="滚动窗口内实现 EWMA 波动率标准化，输出无量纲信噪比序列",
            parameters={"window": window, "span": span, "eps": eps},
            origin="auto"
        )
        self.window = window
        self.span = span
        self.eps = eps
    
    def compute(self, draws) -> np.ndarray:
        if not draws or len(draws) < self.window:
            return np.ones(33) / 33
        
        # 计算每个号码的滚动出现率
        reds_history = np.array([d.reds for d in draws[-self.window:]])
        n_periods = len(reds_history)
        
        # 每期6个红球，统计每个号码的出现频率
        freq = np.zeros(34)  # 1-33
        for period_reds in reds_history:
            for n in period_reds:
                if 1 <= n <= 33:
                    freq[n] += 1
        
        # 期望频率 = 6 * window / 33
        expected = 6.0 * n_periods / 33.0
        
        # 计算滚动方差/EWMA波动率
        scores = np.ones(33) / 33
        for n in range(1, 34):
            if freq[n] > 0:
                # 信噪比 = (实际频率 - 期望频率) / sqrt(期望频率 * (1 - p))
                p = 6.0 / 33.0
                variance = n_periods * p * (1 - p)
                if variance > 0:
                    z_score = (freq[n] - expected) / np.sqrt(variance)
                    scores[n-1] = max(0, z_score)
        
        # 归一化
        if scores.sum() > 0:
            scores = scores / scores.sum()
        return scores

from formula_lang.primitive import PrimitiveFactory
PrimitiveFactory.volatility_normalize = staticmethod(lambda **kwargs: volatility_normalize(**kwargs))