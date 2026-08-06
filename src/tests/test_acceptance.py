# tests/test_acceptance.py
"""
验收测试 - 验证模型是否达到标准
"""
import pytest
import yaml
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

from validation.splitter import WalkForwardSplitter
from validation.metrics import (
    compute_hit_rate,
    compute_top1_accuracy,
    compute_calibration_mae,
    compute_sharpe_ratio,
    compute_max_drawdown
)
from validation.significance import (
    mcnemar_test,
    bootstrap_ci,
    pass_fail_test
)


@pytest.fixture
def criteria_path():
    return Path("acceptance_criteria.yaml")


@pytest.fixture
def load_criteria(criteria_path):
    with open(criteria_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def test_hit_rate_calculation():
    """测试命中率计算"""
    predictions = [
        {1, 2, 3, 4, 5, 6} for _ in range(10)
    ]
    actuals = [
        {1, 2, 7, 8, 9, 10} for _ in range(10)
    ]
    
    hit_rate = compute_hit_rate(predictions, actuals, k=6)
    assert hit_rate == 2/6, f"期望 {2/6}, 得到 {hit_rate}"


def test_top1_accuracy():
    """测试全中准确率"""
    predictions = [
        {1, 2, 3, 4, 5, 6},
        {1, 2, 3, 4, 5, 6},
        {7, 8, 9, 10, 11, 12}
    ]
    actuals = [
        {1, 2, 3, 4, 5, 6},
        {7, 8, 9, 10, 11, 12},
        {7, 8, 9, 10, 11, 12}
    ]
    
    accuracy = compute_top1_accuracy(predictions, actuals)
    assert accuracy == 1.0, f"期望 1.0, 得到 {accuracy}"


def test_mcnemar_test():
    """测试McNemar检验"""
    model_a = [True, True, False, True, False]
    model_b = [True, False, True, True, False]
    
    result = mcnemar_test(model_a, model_b)
    
    assert 'statistic' in result
    assert 'p_value' in result
    assert 'significant' in result
    assert 'winner' in result


def test_bootstrap_ci():
    """测试Bootstrap置信区间"""
    values = [0.15, 0.16, 0.14, 0.17, 0.15]
    
    result = bootstrap_ci(values, n_bootstrap=1000)
    
    assert 'mean' in result
    assert 'ci_lower' in result
    assert 'ci_upper' in result
    assert result['ci_lower'] <= result['mean'] <= result['ci_upper']


def test_pass_fail_test():
    """测试阈值检查"""
    passed, threshold = pass_fail_test(0.20, ">= 0.15")
    assert passed, "0.20 应该通过 >= 0.15"
    
    passed, threshold = pass_fail_test(0.10, ">= 0.15")
    assert not passed, "0.10 不应该通过 >= 0.15"


def test_walk_forward_splitter():
    """测试滚动窗口分割器"""
    X = np.random.rand(200, 5)
    splitter = WalkForwardSplitter(n_splits=3, test_size=50, gap=5)
    
    splits = list(splitter.split(X))
    assert len(splits) > 0
    
    for train_idx, test_idx in splits:
        train_size = test_idx.stop - test_idx.start
        assert train_size == splitter.test_size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
