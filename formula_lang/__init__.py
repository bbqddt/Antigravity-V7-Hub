# -*- coding: utf-8 -*-
from .primitive_volatility_normalize import volatility_normalize
from .primitive_nonlinear_warp import nonlinear_warp
from .primitive_entropy_flow import entropy_flow
"""
Antigravity 公式语言 — 包入口

导出:
    - Primitive: 原语基类
    - FormulaGrammar: 公式语法
    - PrimitiveFactory: 原语工厂
    - get_default_primitives: 默认原语集合

用法:
    from formula_lang import Primitive, FormulaGrammar, get_default_primitives

    # 获取默认原语
    primes = get_default_primitives()

    # 创建共振公式
    f = FormulaGrammar.resonance(primes[:3])

    # 评估
    scores = f.evaluate_for_all_numbers(draws)
    top6 = f.rank_top_6(draws)
"""
from formula_lang.primitive import (
    Primitive,
    PeriodicEcho,
    RecencyGradient,
    SeasonalResonance,
    CooccurrenceAffinity,
    MutualExclusionScore,
    PairOrbit,
    BinaryTopology,
    DigitManifold,
    PositionSignature,
    SpectralPower,
    WaveletCoherence,
    SphereProjection,
    DistanceCluster,
    AttractorDistance,
    LyapunovSignal,
    # 新增
    SumRangeTracker,
    GapPatternAnalyzer,
    TrendReversalDetector,
    ModuloClassDistribution,
    DigitPairFrequency,
    AdjacentNumberBias,
    SkewnessSignal,
    KurtosisSignal,
    TailRiskSignal,
    LagCorrelation,
    PeriodicGap,
    RecurrenceWindow,
    MultiScaleFrequency,
    ScaleTransition,
    EnvironmentAware,
    PhaseDetector,
    RegimeSwitch,
    MutualInformationPair,
    ResidualSignal,
    ConditionalProbabilityMatrix,
    PrimitiveFactory,
    get_default_primitives,
)

from formula_lang.grammar import (
    Formula,
    FormulaGrammar,
)

__all__ = [
    "entropy_flow",
    "nonlinear_warp",
    "volatility_normalize",
    # 原语
    "Primitive",
    "PeriodicEcho",
    "RecencyGradient",
    "SeasonalResonance",
    "CooccurrenceAffinity",
    "MutualExclusionScore",
    "PairOrbit",
    "BinaryTopology",
    "DigitManifold",
    "PositionSignature",
    "SpectralPower",
    "WaveletCoherence",
    "SphereProjection",
    "DistanceCluster",
    "AttractorDistance",
    "LyapunovSignal",
    # 新增
    "SumRangeTracker",
    "GapPatternAnalyzer",
    "TrendReversalDetector",
    "ModuloClassDistribution",
    "DigitPairFrequency",
    "AdjacentNumberBias",
    "SkewnessSignal",
    "KurtosisSignal",
    "TailRiskSignal",
    "LagCorrelation",
    "PeriodicGap",
    "RecurrenceWindow",
    "MultiScaleFrequency",
    "ScaleTransition",
    "EnvironmentAware",
    "PhaseDetector",
    "RegimeSwitch",
    "MutualInformationPair",
    "ResidualSignal",
    "ConditionalProbabilityMatrix",
    "PrimitiveFactory",
    "get_default_primitives",
    # 语法
    "Formula",
    "FormulaGrammar",
]
