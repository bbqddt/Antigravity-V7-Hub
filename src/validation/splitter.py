# validation/splitter.py
"""
滚动窗口验证器 - 时间序列专用
防止未来数据泄露，每次只用过去训练预测未来
"""
from typing import Generator, Optional, Tuple
import numpy as np


class WalkForwardSplitter:
    """
    滚动窗口/前进验证分割器
    
    参数:
        n_splits: 分割次数
        test_size: 测试集大小
        gap: 训练/测试间隔期数（防泄露）
        min_train_size: 最小训练集大小
    
    示例:
        splitter = WalkForwardSplitter(n_splits=5, test_size=50, gap=5)
        for train_idx, test_idx in splitter.split(X):
            model.fit(X[train_idx], y[train_idx])
            model.evaluate(X[test_idx], y[test_idx])
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        test_size: int = 50,
        gap: int = 5,
        min_train_size: int = 200
    ):
        self.n_splits = n_splits
        self.test_size = test_size
        self.gap = gap
        self.min_train_size = min_train_size
    
    def split(
        self, 
        X, 
        y=None
    ) -> Generator[Tuple[slice, slice], None, None]:
        """生成训练/测试索引对"""
        n = len(X)
        
        for i in range(self.n_splits):
            test_end = n - i * self.test_size
            test_start = test_end - self.test_size
            train_end = test_start - self.gap
            train_start = max(0, train_end - self.min_train_size)
            
            # 检查训练集是否足够
            if train_end - train_start < self.min_train_size:
                break
            
            # 检查测试集是否有效
            if test_start >= test_end or test_end > n:
                break
            
            yield (
                slice(train_start, train_end),
                slice(test_start, test_end)
            )
    
    def get_n_splits(self, X=None, y=None) -> int:
        """返回实际分割次数"""
        return min(self.n_splits, max(1, (len(X) - self.test_size - self.gap) // (self.test_size + self.gap)))
