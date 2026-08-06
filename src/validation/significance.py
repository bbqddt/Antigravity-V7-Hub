# validation/significance.py
"""
统计显著性检验工具
"""
from typing import List, Dict, Tuple
import numpy as np
from scipy import stats


def mcnemar_test(
    model_a_hits: List[bool], 
    model_b_hits: List[bool],
    alpha: float = 0.05
) -> Dict:
    """
    McNemar检验 - 比较两个模型在同一测试集上的表现
    
    参数:
        model_a_hits: 模型A的命中结果列表
        model_b_hits: 模型B的命中结果列表
        alpha: 显著性水平
    
    返回:
        {
            'statistic': chi2值,
            'p_value': p值,
            'significant': 是否显著,
            'winner': 'A'/'B'/'tie'
        }
    """
    if len(model_a_hits) != len(model_b_hits):
        raise ValueError("两个模型的预测长度必须相同")
    
    # 构建列联表
    a_correct_b_wrong = sum(a and not b for a, b in zip(model_a_hits, model_b_hits))
    b_correct_a_wrong = sum(b and not a for a, b in zip(model_a_hits, model_b_hits))
    
    # McNemar检验统计量（连续修正）
    total_disagreement = a_correct_b_wrong + b_correct_a_wrong
    if total_disagreement == 0:
        return {
            'statistic': 0,
            'p_value': 1.0,
            'significant': False,
            'winner': 'tie',
            'a_only': 0,
            'b_only': 0
        }
    
    chi2 = (abs(a_correct_b_wrong - b_correct_a_wrong) - 1) ** 2 / total_disagreement
    p_value = 1 - stats.chi2.cdf(chi2, df=1)
    
    winner = 'A' if a_correct_b_wrong > b_correct_a_wrong else \
             'B' if b_correct_a_wrong > a_correct_b_wrong else 'tie'
    
    return {
        'statistic': chi2,
        'p_value': p_value,
        'significant': p_value < alpha,
        'winner': winner,
        'a_only': a_correct_b_wrong,
        'b_only': b_correct_a_wrong
    }


def bootstrap_ci(
    metric_values: List[float],
    n_bootstrap: int = 10000,
    confidence: float = 0.95
) -> Dict:
    """
    Bootstrap置信区间估计
    
    参数:
        metric_values: 指标值列表
        n_bootstrap: Bootstrap迭代次数
        confidence: 置信水平
    
    返回:
        {
            'mean': 均值,
            'ci_lower': 置信区间下限,
            'ci_upper': 置信区间上限,
            'std_error': 标准误差
        }
    """
    if len(metric_values) < 2:
        return {
            'mean': metric_values[0] if metric_values else 0,
            'ci_lower': metric_values[0] if metric_values else 0,
            'ci_upper': metric_values[0] if metric_values else 0,
            'std_error': 0
        }
    
    np.random.seed(42)
    bootstrap_means = [
        np.mean(np.random.choice(metric_values, len(metric_values), replace=True))
        for _ in range(n_bootstrap)
    ]
    
    lower_pct = (1 - confidence) * 50
    upper_pct = (1 + confidence) * 50
    
    return {
        'mean': float(np.mean(bootstrap_means)),
        'ci_lower': float(np.percentile(bootstrap_means, lower_pct)),
        'ci_upper': float(np.percentile(bootstrap_means, upper_pct)),
        'std_error': float(np.std(bootstrap_means))
    }


def pass_fail_test(
    metric_value: float,
    threshold: str
) -> Tuple[bool, str]:
    """
    检查指标是否通过阈值测试
    
    参数:
        metric_value: 指标值
        threshold: 阈值表达式，如 ">= 0.15" 或 "<= 0.05"
    
    返回:
        (是否通过, 阈值字符串)
    """
    import re
    match = re.match(r'([><=]+)\s*([\d.]+)', threshold)
    if not match:
        raise ValueError(f"无效的阈值格式: {threshold}")
    
    operator, threshold_value = match.groups()
    threshold_value = float(threshold_value)
    
    if operator == '>=':
        passed = metric_value >= threshold_value
    elif operator == '<=':
        passed = metric_value <= threshold_value
    elif operator == '>':
        passed = metric_value > threshold_value
    elif operator == '<':
        passed = metric_value < threshold_value
    else:
        raise ValueError(f"不支持的操作符: {operator}")
    
    return passed, f"{operator}{threshold_value}"
