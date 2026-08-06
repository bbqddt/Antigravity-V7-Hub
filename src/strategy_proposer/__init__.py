# -*- coding: utf-8 -*-
"""
Antigravity 策略框架 — 包入口

导出:
    - HypothesisTemplate: 假设模板
    - Hypothesis: 假设实例
    - HypothesisGenerator: 假设生成器
    - HypothesisValidator: 假设验证器
    - StrategyRegistry: 策略注册表
"""
from strategy_proposer.hypothesis import (
    HypothesisTemplate,
    Hypothesis,
    generate_hypotheses_from_template,
)
from strategy_proposer.generator import HypothesisGenerator
from strategy_proposer.validator import HypothesisValidator
from strategy_proposer.registry import StrategyRegistry

__all__ = [
    "HypothesisTemplate",
    "Hypothesis",
    "generate_hypotheses_from_template",
    "HypothesisGenerator",
    "HypothesisValidator",
    "StrategyRegistry",
]
