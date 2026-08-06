# validation/__init__.py
"""
验证模块 - 提供统计检验、滚动窗口验证、置信区间计算等工具
"""
from .splitter import WalkForwardSplitter
from .significance import mcnemar_test, bootstrap_ci
from .metrics import compute_hit_rate, compute_calibration_mae

__all__ = [
    'WalkForwardSplitter',
    'mcnemar_test',
    'bootstrap_ci',
    'compute_hit_rate',
    'compute_calibration_mae'
]
