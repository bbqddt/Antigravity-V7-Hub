# validation/metrics.py
"""
指标计算工具
"""
from typing import Set, List, Optional
import numpy as np


def compute_hit_rate(
    predictions: List[Set[int]],
    actuals: List[Set[int]],
    k: int = 6
) -> float:
    """
    计算命中率
    
    参数:
        predictions: 预测集合列表，每个集合包含预测的号码
        actuals: 实际集合列表，每个集合包含实际开出的号码
        k: 每期预测/开出号码数量（默认6）
    
    返回:
        命中率 = 总命中数 / (期数 * k)
    """
    if not predictions or not actuals:
        return 0.0
    
    total_hits = 0
    for pred, actual in zip(predictions, actuals):
        if not pred or not actual:
            continue
        total_hits += len(pred & actual)
    
    total_periods = len(predictions)
    return total_hits / max(1, total_periods * k)


def compute_top1_accuracy(
    predictions: List[Set[int]],
    actuals: List[Set[int]]
) -> float:
    """
    计算全中准确率
    
    参数:
        predictions: 预测集合列表
        actuals: 实际集合列表
    
    返回:
        全中率 = 6个号全中的期数 / 总期数
    """
    if not predictions or not actuals:
        return 0.0
    
    full_hits = sum(
        1 for pred, actual in zip(predictions, actuals)
        if pred == actual
    )
    
    return full_hits / len(predictions)


def compute_calibration_mae(
    predicted_probs: List[float],
    actuals: List[bool]
) -> float:
    """
    计算校准误差（平均绝对误差）
    
    参数:
        predicted_probs: 预测概率列表
        actuals: 实际结果列表（True/False）
    
    返回:
        MAE = mean(abs(predicted_prob - actual))
    """
    if not predicted_probs or not actuals:
        return 0.0
    
    if len(predicted_probs) != len(actuals):
        raise ValueError("预测概率和实际结果长度必须相同")
    
    errors = [
        abs(p - (1 if a else 0))
        for p, a in zip(predicted_probs, actuals)
    ]
    
    return float(np.mean(errors))


def compute_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 0.0
) -> float:
    """
    计算夏普比率
    
    参数:
        returns: 每期收益率列表
        risk_free_rate: 无风险利率
    
    返回:
        夏普比率 = (平均收益 - 无风险利率) / 收益标准差
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    arr = np.array(returns)
    excess_returns = arr - risk_free_rate
    std = np.std(arr, ddof=1)
    
    if std == 0:
        return 0.0
    
    return float(np.mean(excess_returns) / std)


def compute_max_drawdown(
    cumulative_returns: List[float]
) -> float:
    """
    计算最大回撤
    
    参数:
        cumulative_returns: 累计收益率列表
    
    返回:
        最大回撤 = 最大峰谷跌幅
    """
    if not cumulative_returns or len(cumulative_returns) < 2:
        return 0.0
    
    peak = cumulative_returns[0]
    max_dd = 0.0
    
    for ret in cumulative_returns:
        if ret > peak:
            peak = ret
        dd = (peak - ret) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    return float(max_dd)
