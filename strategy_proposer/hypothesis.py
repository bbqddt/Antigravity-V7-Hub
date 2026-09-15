# -*- coding: utf-8 -*-
"""
Antigravity 策略框架 — 假设系统 V1.0

核心理念:
- 策略不是"设计"的，而是从数据信号中"生长"出来的假设
- 每个假设都是可测试的陈述
- 假设通过验证 → 成为策略
- 假设失败 → 记录原因 → 从失败中学习

用法:
    from strategy_proposer.hypothesis import HypothesisTemplate, Hypothesis
    from strategy_proposer.generator import HypothesisGenerator

    templates = HypothesisTemplate.get_all_templates()
    gen = HypothesisGenerator()
    hypotheses = gen.generate(templates, signals)
"""
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

_PROJECT_ROOT = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════
# 假设模板
# ═══════════════════════════════════════════════════════════

class HypothesisTemplate:
    """
    假设模板 — 带通配符的模式。

    模板定义了假设的结构，填充后变成具体假设。

    模板类型:
        - periodic: 周期性假设
        - correlation: 相关性假设
        - omission: 遗漏假设
        - positional: 位置假设
        - spectral: 频谱假设
        - structural: 结构假设
    """

    _templates: List["HypothesisTemplate"] = []

    def __init__(self, name: str, template_str: str, category: str,
                 signals: Dict[str, str], validation_method: str,
                 priority: int = 5):
        """
        Args:
            name: 模板名称
            template_str: 假设模板字符串（含 {wildcard}）
            category: 类别
            signals: 信号来源 {"hurst": "position_prior", ...}
            validation_method: 验证方法
            priority: 优先级 (1-10)
        """
        self.name = name
        self.template_str = template_str
        self.category = category
        self.signals = signals
        self.validation_method = validation_method
        self.priority = priority
        HypothesisTemplate._templates.append(self)

    def fill(self, params: Dict[str, Any]) -> "Hypothesis":
        """用参数填充模板，生成具体假设"""
        filled_str = self.template_str
        for key, value in params.items():
            filled_str = filled_str.replace("{" + key + "}", str(value))

        h = Hypothesis(
            template_name=self.name,
            template_category=self.category,
            filled_statement=filled_str,
            params=params,
            signals=self.signals,
            validation_method=self.validation_method,
        )
        return h

    @classmethod
    def get_all_templates(cls) -> List["HypothesisTemplate"]:
        """获取所有预定义模板"""
        if not cls._templates:
            cls._init_default_templates()
        return list(cls._templates)

    @classmethod
    def _init_default_templates(cls):
        """初始化默认模板"""
        cls._templates = [
            # 周期性
            HypothesisTemplate(
                name="periodic_resonance",
                template_str="当位置{pos}的Hurst指数在{hurst_range}时，号码{num_set}在{window}期内出现频率显著偏高",
                category="periodic",
                signals={"hurst": "position_prior", "frequency": "historical"},
                validation_method="walk_forward",
                priority=8,
            ),
            HypothesisTemplate(
                name="spectral_cycle",
                template_str="号码{n}在频谱分析中显示出{period}期的周期信号",
                category="periodic",
                signals={"spectral": "nonrandomness_results"},
                validation_method="walk_forward",
                priority=7,
            ),

            # 遗漏
            HypothesisTemplate(
                name="omission_rebound",
                template_str="当号码{n}遗漏超过{omit_threshold}期时，下期出现的概率显著高于基准",
                category="omission",
                signals={"omission": "historical"},
                validation_method="walk_forward",
                priority=9,
            ),
            HypothesisTemplate(
                name="blue_omission_hurst",
                template_str="蓝球在遗漏{omit_days}期后，受Hurst={hurst}的均值回归效应影响，下一期出现概率提升",
                category="omission",
                signals={"omission": "historical", "hurst": "position_prior"},
                validation_method="walk_forward",
                priority=8,
            ),

            # 位置
            HypothesisTemplate(
                name="positional_bias",
                template_str="位置{pos}的号码分布偏向{range_label}区间（{range_min}-{range_max}）",
                category="positional",
                signals={"positional": "position_prior", "distribution": "historical"},
                validation_method="walk_forward",
                priority=7,
            ),
            HypothesisTemplate(
                name="position_correlation",
                template_str="位置{pos_a}和位置{pos_b}的号码存在{corr_type}相关性（r={corr_value}）",
                category="positional",
                signals={"correlation": "nonrandomness_results"},
                validation_method="walk_forward",
                priority=6,
            ),

            # 共现
            HypothesisTemplate(
                name="cooccurrence_pair",
                template_str="号码{n_a}和{n_b}的共现频率为{cooccur_freq}，显著高于期望值{expected}",
                category="cooccurrence",
                signals={"cooccurrence": "historical"},
                validation_method="walk_forward",
                priority=8,
            ),
            HypothesisTemplate(
                name="mutual_exclusion",
                template_str="号码{n_a}和{n_b}表现出互斥关系（共现率{cooccur_rate} << 期望{expected}）",
                category="cooccurrence",
                signals={"cooccurrence": "historical"},
                validation_method="walk_forward",
                priority=7,
            ),

            # 结构
            HypothesisTemplate(
                name="binary_pattern",
                template_str="号码{n}的二进制表示具有{binary_feature}特征，与开奖结果相关",
                category="structural",
                signals={"binary": "number_profiles"},
                validation_method="walk_forward",
                priority=6,
            ),
            HypothesisTemplate(
                name="digit_sum_cluster",
                template_str="数位和在{sum_range}范围内的号码出现频率异常（{freq} vs 期望{expected}）",
                category="structural",
                signals={"digit_sum": "number_profiles"},
                validation_method="walk_forward",
                priority=7,
            ),

            # 蓝球
            HypothesisTemplate(
                name="blue_transition",
                template_str="蓝球从{blue_prev}转移到{blue_next}的概率为{transition_prob}（马尔可夫链）",
                category="blue",
                signals={"transition": "historical"},
                validation_method="walk_forward",
                priority=8,
            ),
            HypothesisTemplate(
                name="blue_hurst_mean_revert",
                template_str="蓝球Hurst={hurst}（强反持久性），遗漏策略在{window}期内有效",
                category="blue",
                signals={"hurst": "position_prior"},
                validation_method="walk_forward",
                priority=9,
            ),
        ]


# ═══════════════════════════════════════════════════════════
# 假设
# ═══════════════════════════════════════════════════════════

class Hypothesis:
    """
    假设 — 从模板填充生成的具体可测试陈述。

    生命周期: proposed → testing → survived/eliminated → evolved → archived
    """

    def __init__(self, template_name: str, template_category: str,
                 filled_statement: str, params: Dict,
                 signals: Dict, validation_method: str):
        self.id = str(uuid.uuid4())[:8]
        self.template_name = template_name
        self.template_category = template_category
        self.statement = filled_statement
        self.params = params
        self.signals = signals
        self.validation_method = validation_method

        # 生命周期
        self.status = "proposed"  # proposed | testing | survived | eliminated | evolved | archived
        self.proposed_at = datetime.now().isoformat()
        self.tested_at: Optional[str] = None
        self.result: Optional[Dict] = None  # {"avg_hits": 2.3, "p_value": 0.03, ...}
        self.elimination_reason: Optional[str] = None
        self.children: List[str] = []  # 衍生假设ID
        self.parent_ids: List[str] = []

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "template_name": self.template_name,
            "statement": self.statement,
            "params": self.params,
            "signals": self.signals,
            "validation_method": self.validation_method,
            "status": self.status,
            "proposed_at": self.proposed_at,
            "tested_at": self.tested_at,
            "result": self.result,
            "elimination_reason": self.elimination_reason,
            "children": self.children,
            "parent_ids": self.parent_ids,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Hypothesis":
        h = cls(
            template_name=d["template_name"],
            template_category="",
            filled_statement=d["statement"],
            params=d.get("params", {}),
            signals=d.get("signals", {}),
            validation_method=d.get("validation_method", "walk_forward"),
        )
        h.id = d["id"]
        h.status = d.get("status", "proposed")
        h.proposed_at = d.get("proposed_at", "")
        h.tested_at = d.get("tested_at")
        h.result = d.get("result")
        h.elimination_reason = d.get("elimination_reason")
        h.children = d.get("children", [])
        h.parent_ids = d.get("parent_ids", [])
        return h

    def __repr__(self):
        return f"<Hypothesis[{self.status}] {self.id}: {self.statement[:60]}...>"


# ═══════════════════════════════════════════════════════════
# 便捷入口
# ═══════════════════════════════════════════════════════════

def generate_hypotheses_from_template(template_name: str, params: Dict) -> Hypothesis:
    """从模板名称和参数生成假设"""
    templates = HypothesisTemplate.get_all_templates()
    for t in templates:
        if t.name == template_name:
            return t.fill(params)
    raise ValueError(f"Unknown template: {template_name}")
