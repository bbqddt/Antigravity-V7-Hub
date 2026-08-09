# -*- coding: utf-8 -*-
"""
nonlinear_warp - LLM 提案生成的原语
类别: 混沌
逻辑: 引入可微非线性变换：tanh(k*x)、sign(x)*abs(x)^p、或可学习的有理函数 (Pade 近似)。打破 LTI 假设，捕捉收益率分布的峰态/厚尾及非对称杠杆效应。
"""
import numpy as np
from formula_lang.primitive import Primitive

class nonlinear_warp(Primitive):
    """引入可微非线性变换：tanh(k*x)、sign(x)*abs(x)^p、或可学习的有理函数。打破 LTI 假设，捕捉峰态/厚尾及非对称效应。"""
    
    def __init__(self, warp_type: int = 1, k: float = 2.0, p: float = 1.5):
        super().__init__(
            name="nonlinear_warp",
            category="混沌",
            description="可微非线性变换：tanh、power、rational 等",
            parameters={"warp_type": warp_type, "k": k, "p": p},
            origin="auto"
        )
        self.warp_type = warp_type
        self.k = k
        self.p = p
    
    def compute(self, draws) -> np.ndarray:
        if not draws:
            return np.ones(33) / 33
        
        # 计算基础特征：每个号码的近期出现偏离度
        recent = 30
        reds_history = np.array([d.reds for d in draws[-recent:]])
        freq = np.zeros(34)
        for period_reds in reds_history:
            for n in period_reds:
                if 1 <= n <= 33:
                    freq[n] += 1
        
        expected = 6.0 * recent / 33.0
        x = (freq[1:34] - expected) / (expected + 1e-6)  # 标准化偏离
        
        scores = np.ones(33) / 33
        
        if self.warp_type == 1:
            # tanh 压缩
            scores = np.tanh(self.k * x)
        elif self.warp_type == 2:
            # sign * abs^p
            scores = np.sign(x) * np.abs(x) ** self.p
        elif self.warp_type == 3:
            # 有理函数 Pade 近似
            scores = x / (1 + self.k * np.abs(x))
        else:
            scores = x
        
        # 归一化到 [0, 1] 范围
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        if scores.sum() > 0:
            scores = scores / scores.sum()
        return scores

from formula_lang.primitive import PrimitiveFactory
PrimitiveFactory.nonlinear_warp = staticmethod(lambda **kwargs: nonlinear_warp(**kwargs))