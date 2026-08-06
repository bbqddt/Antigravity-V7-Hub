# -*- coding: utf-8 -*-
"""
双色球分布预测 Walk-Forward 回测 (CRPS) - 科学版
核心原则：
1. 公平基线：所有基线只能用训练数据，不能作弊
2. 正确建模：预测分布参数而非分位数，避免分位数塌缩
3. 多基线对比：Engine 必须同时击败所有基线才算有信号
4. 真实随机性：双色球本质随机，基线极强是正常现象
"""

import sys
import math
import json
import os
import random
import argparse
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# Fix Windows encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

try:
    from scipy.stats import norm, beta
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from data_layer import load_history, Draw


# ═══════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════
INITIAL_WINDOW = 500
RANDOM_SEED = 42
N_QUANTILES = 99  # 评估用密集分位数

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

TARGET_SPECS = {
    "red_sum":    {"type": "normal",    "range": (21, 189)},      # 和值 ~ 正态
    "odd_ratio":  {"type": "beta",      "range": (0, 1)},         # 奇偶比 ~ Beta
    "high_ratio": {"type": "beta",      "range": (0, 1)},         # 大小比 ~ Beta
    "span":       {"type": "normal",    "range": (5, 32)},        # 跨度 ~ 正态
    "ac_value":   {"type": "poisson",   "range": (0, 10)},        # AC值 ~ 泊松近似
}

TARGET_NAMES = list(TARGET_SPECS.keys())


# ═══════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class DistributionTarget:
    period: int
    red_sum: int
    odd_ratio: float
    high_ratio: float
    span: int
    ac_value: int

    @staticmethod
    def from_draw(draw: Draw) -> "DistributionTarget":
        reds = sorted(draw.reds)
        red_sum = sum(reds)
        odd_count = sum(1 for r in reds if r % 2 == 1)
        high_count = sum(1 for r in reds if r > 17)
        span = reds[-1] - reds[0]
        diffs = set(abs(reds[j] - reds[i]) for i in range(6) for j in range(i+1, 6))
        ac_value = max(0, len(diffs) - 5)
        return DistributionTarget(
            period=draw.period,
            red_sum=red_sum,
            odd_ratio=odd_count / 6.0,
            high_ratio=high_count / 6.0,
            span=span,
            ac_value=ac_value
        )

    def to_array(self) -> np.ndarray:
        return np.array([self.red_sum, self.odd_ratio, self.high_ratio, self.span, self.ac_value])


@dataclass
class DistParams:
    """分布参数容器"""
    # normal: (mu, sigma)
    # beta: (alpha, beta)
    # poisson: (lambda)
    params: Dict[str, Tuple]
    
    def get_dist(self, name: str):
        spec = TARGET_SPECS[name]
        p = self.params[name]
        if spec["type"] == "normal":
            return norm(*p) if HAS_SCIPY else None
        elif spec["type"] == "beta":
            return beta(*p) if HAS_SCIPY else None
        elif spec["type"] == "poisson":
            from scipy.stats import poisson
            return poisson(*p) if HAS_SCIPY else None
        return None


@dataclass
class RoundResult:
    period: int
    train_size: int
    crps: Dict[str, float]           # engine crps per target
    crps_avg: float
    baseline_crps: Dict[str, Dict[str, float]]  # baseline_name -> target -> crps
    p_values: Dict[str, float]       # per target p-value
    model_weights: Dict[str, float]


@dataclass
class BacktestResult:
    engine_crps: Dict[str, float]
    baseline_crps: Dict[str, Dict[str, float]]
    rounds: List[RoundResult]
    statistical_summary: Dict[str, Any]
    config: Dict[str, Any]
    feature_importance: Dict[str, float]


# ═══════════════════════════════════════════════════════════
# CRPS 计算 - 解析解版本（更准确、更快）
# ═══════════════════════════════════════════════════════════

def crps_normal(y: float, mu: float, sigma: float) -> float:
    """正态分布 CRPS 解析解"""
    if sigma <= 0:
        return abs(y - mu)
    z = (y - mu) / sigma
    # CRPS = σ * [z(2Φ(z)-1) + 2φ(z) - 1/√π]
    if HAS_SCIPY:
        phi = norm.pdf(z)
        Phi = norm.cdf(z)
        return sigma * (z * (2*Phi - 1) + 2*phi - 1/math.sqrt(math.pi))
    # 无 scipy 近似
    return abs(y - mu) * 0.5 + sigma * 0.3


def crps_beta(y: float, a: float, b: float) -> float:
    """Beta 分布 CRPS 数值积分"""
    if a <= 0 or b <= 0:
        return abs(y - 0.5)
    if not HAS_SCIPY:
        return abs(y - a/(a+b)) * 0.5
    # 数值积分
    xs = np.linspace(0, 1, 200)
    cdf = beta.cdf(xs, a, b)
    indicator = (xs >= y).astype(float)
    return np.trapz((cdf - indicator)**2, xs)


def crps_poisson(y: int, lam: float) -> float:
    """泊松分布 CRPS"""
    if lam <= 0:
        return abs(y)
    if not HAS_SCIPY:
        return abs(y - lam) * 0.5
    from scipy.stats import poisson
    # 截断求和
    max_k = max(int(lam + 5*math.sqrt(lam)), y + 10)
    ks = np.arange(0, max_k+1)
    cdf = poisson.cdf(ks, lam)
    indicator = (ks >= y).astype(float)
    return np.sum((cdf - indicator)**2)


def compute_crps(target: np.ndarray, params: DistParams) -> Dict[str, float]:
    """计算所有目标的 CRPS"""
    crps = {}
    names = ["red_sum", "odd_ratio", "high_ratio", "span", "ac_value"]
    for i, name in enumerate(names):
        spec = TARGET_SPECS[name]
        y = target[i]
        p = params.params[name]
        if spec["type"] == "normal":
            crps[name] = crps_normal(target[i], p[0], p[1])
        elif spec["type"] == "beta":
            crps[name] = crps_beta(target[i], p[0], p[1])
        elif spec["type"] == "poisson":
            crps[name] = crps_poisson(int(target[i]), p[0])
        else:
            crps[name] = 1.0
    crps["avg"] = np.mean(list(crps.values()))
    return crps


# ═══════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class DistributionTarget:
    period: int
    red_sum: int
    odd_ratio: float
    high_ratio: float
    span: int
    ac_value: int

    @staticmethod
    def from_draw(draw: Draw):
        reds = sorted(draw.reds)
        red_sum = sum(reds)
        odd_count = sum(1 for r in reds if r % 2 == 1)
        high_count = sum(1 for r in reds if r > 17)
        span = reds[-1] - reds[0]
        diffs = set(abs(reds[j] - reds[i]) for i in range(6) for j in range(i+1, 6))
        ac_value = max(0, len(diffs) - 5)
        return DistributionTarget(
            period=draw.period,
            red_sum=red_sum,
            odd_ratio=odd_count / 6.0,
            high_ratio=high_count / 6.0,
            span=span,
            ac_value=ac_value
        )
    
    def to_array(self):
        return np.array([self.red_sum, self.odd_ratio, self.high_ratio, self.span, self.ac_value])


# ═══════════════════════════════════════════════════════════
# 基线模型
# ═══════════════════════════════════════════════════════════

class EmpiricalBaseline:
    """基线1：经验分布（历史数据拟合分布参数）"""
    
    def __init__(self):
        self.params = None
    
    def fit(self, targets: List):
        # 拟合每个目标的分布参数
        data = {name: [] for name in TARGET_SPECS}
        for t in targets:
            arr = t.to_array()
            for i, name in enumerate(TARGET_SPECS):
                if name == "ac_value":
                    data[name].append(int(arr[i]))
                else:
                    data[name].append(float(arr[i]))
        
        params = {}
        for name, spec in TARGET_SPECS.items():
            vals = np.array(data[name])
            vals = vals[np.isfinite(vals)]
            if spec["type"] == "normal":
                mu = np.mean(vals)
                sigma = max(np.std(vals), 1e-3)
                params[name] = (float(mu), float(sigma))
            elif spec["type"] == "beta":
                # Beta 参数估计
                v_min, v_max = spec["range"]
                vals_norm = (vals - v_min) / (v_max - v_min)
                vals_norm = np.clip(vals_norm, 1e-6, 1-1e-6)
                mean = np.mean(vals_norm)
                var = max(np.var(vals_norm), 1e-6)
                # method of moments
                common = mean * (1 - mean) / var - 1
                alpha = mean * common
                beta_param = (1 - mean) * common
                params[name] = (max(alpha, 0.1), max(beta_param, 0.1))
            elif spec["type"] == "poisson":
                lam = max(np.mean(vals), 0.1)
                params[name] = (float(lam),)
        self.params = params
    
    def predict(self) -> DistParams:
        return DistParams(self.params.copy())


class TheoreticalBaseline:
    """基线2：理论分布（固定参数，不学习）"""
    
    def __init__(self):
        # 双色球理论分布参数
        self.params = {
            "red_sum":    (105.0, 15.0),    # 正态 N(105, 15²)
            "odd_ratio":  (3.0, 3.0),       # Beta(3,3) ≈ 均匀偏中心
            "high_ratio": (3.0, 3.0),       # Beta(3,3)
            "span":       (24.0, 6.0),      # 正态 N(24, 6²)
            "ac_value":   (5.0,),           # Poisson(5)
        }
    
    def fit(self, targets):
        pass  # 不学习
    
    def predict(self):
        return DistParams(self.params.copy())


class Lag1Baseline:
    """基线3：滞后1期（上一期值）"""
    
    def __init__(self):
        self.last = None
    
    def fit(self, targets):
        if targets:
            self.last = targets[-1]
    
    def predict(self):
        if self.last is None:
            # 回退到理论
            return TheoreticalBaseline().predict()
        # 构造退化分布：方差极小
        params = {}
        arr = self.last.to_array()
        for i, name in enumerate(TARGET_SPECS):
            spec = TARGET_SPECS[name]
            val = arr[i]
            if spec["type"] == "normal":
                params[name] = (float(val), 0.5)
            elif spec["type"] == "beta":
                v = max(0.001, min(0.999, val))
                params[name] = (v * 100, (1-v) * 100)
            elif spec["type"] == "poisson":
                params[name] = (max(val, 0.1),)
        return DistParams(params)


class UniformBaseline:
    """基线4：均匀分布（最大熵）"""
    
    def fit(self, targets): pass
    
    def predict(self):
        params = {
            "red_sum":    (105.0, 48.0),    # 方差极大
            "odd_ratio":  (1.0, 1.0),       # Uniform
            "high_ratio": (1.0, 1.0),
            "span":       (18.5, 7.8),      # 大方差
            "ac_value":   (5.0,),
        }
        return DistParams(params)


# ═══════════════════════════════════════════════════════════
# CRPS 计算
# ═══════════════════════════════════════════════════════════

def crps_normal(y: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        return abs(y - mu)
    z = (y - mu) / sigma
    if HAS_SCIPY:
        phi = norm.pdf(z)
        Phi = norm.cdf(z)
        return sigma * (z * (2*Phi - 1) + 2*phi - 1/math.sqrt(math.pi))
    return abs(y - mu) * 0.5


def crps_beta(y: float, a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        return abs(y - 0.5)
    if not HAS_SCIPY:
        return abs(y - a/(a+b)) * 0.5
    xs = np.linspace(0, 1, 200)
    cdf = beta.cdf(xs, a, b)
    indicator = (xs >= y).astype(float)
    return np.trapz((cdf - indicator)**2, xs)


def crps_poisson(y: int, lam: float) -> float:
    if lam <= 0:
        return abs(y)
    if not HAS_SCIPY:
        return abs(y - lam) * 0.5
    from scipy.stats import poisson
    max_k = max(int(lam + 5*math.sqrt(lam)), y + 10)
    ks = np.arange(0, max_k+1)
    cdf = poisson.cdf(ks, lam)
    indicator = (ks >= y).astype(float)
    return np.sum((cdf - indicator)**2)


def compute_all_crps(target: np.ndarray, params: DistParams) -> Dict[str, float]:
    crps = {}
    names = ["red_sum", "odd_ratio", "high_ratio", "span", "ac_value"]
    for i, name in enumerate(names):
        spec = TARGET_SPECS[name]
        y = target[i]
        p = params.params[name]
        if spec["type"] == "normal":
            crps[name] = crps_normal(target[i], p[0], p[1])
        elif spec["type"] == "beta":
            crps[name] = crps_beta(target[i], p[0], p[1])
        elif spec["type"] == "poisson":
            crps[name] = crps_poisson(int(target[i]), p[0])
        else:
            crps[name] = 1.0
    crps["avg"] = np.mean(list(crps.values()))
    return crps


# ═══════════════════════════════════════════════════════════
# 特征工程
# ═══════════════════════════════════════════════════════════

FEATURE_WINDOWS = [10, 20, 50, 100, 200]

def extract_features(draws: List[Draw], end_idx: int) -> Dict[str, float]:
    recent = draws[max(0, end_idx - 200):end_idx]
    if len(recent) < 10:
        return {}
    
    targets = [DistributionTarget.from_draw(d) for d in recent]
    features = {}
    
    for w in FEATURE_WINDOWS:
        if len(targets) < w:
            continue
        window = targets[-w:]
        
        for name in TARGET_SPECS:
            vals = [getattr(t, name) for t in window]
            features[f"{name}_mean_{w}"] = np.mean(vals)
            features[f"{name}_std_{w}"] = np.std(vals)
            features[f"{name}_trend_{w}"] = vals[-1] - vals[0] if w > 1 else 0
        
        if w == FEATURE_WINDOWS[0]:
            last = targets[-1]
            for name in TARGET_SPECS:
                features[f"last_{name}"] = getattr(last, name)
    
    return features


def prepare_dataset(draws: List[Draw], end_idx: int):
    X_list, y_dict = [], {n: [] for n in TARGET_SPECS}
    for i in range(max(0, end_idx-200), end_idx):
        feat = extract_features(draws, i)
        if not feat:
            continue
        target = DistributionTarget.from_draw(draws[i])
        X_list.append(feat)
        arr = target.to_array()
        for i, name in enumerate(TARGET_SPECS):
            y_dict[name].append(arr[i])
    
    if not X_list:
        return np.array([]), {}, []
    
    all_keys = sorted(set().union(*[f.keys() for f in X_list]))
    X = np.array([[f.get(k, 0) for k in all_keys] for f in X_list])
    y_arrays = {n: np.array(v) for n, v in y_dict.items()}
    return X, y_arrays, list(X_list[0].keys()) if X_list else []


# ═══════════════════════════════════════════════════════════
# Engine 模型 - 预测分布参数
# ═══════════════════════════════════════════════════════════

class ParamModel:
    """预测单个目标的分布参数"""
    
    def __init__(self, name: str, use_lgb: bool = True):
        self.name = name
        self.spec = TARGET_SPECS[name]
        self.use_lgb = use_lgb and HAS_LGB
        self.models = {}
        self.feature_names = []
        self.param_names = self._get_param_names()
    
    def _get_param_names(self):
        if self.spec["type"] == "normal":
            return ["mu", "log_sigma"]
        elif self.spec["type"] == "beta":
            return ["log_alpha", "log_beta"]
        elif self.spec["type"] == "poisson":
            return ["log_lambda"]
        return ["param"]
    
    def _transform_y(self, y: np.ndarray) -> Dict[str, np.ndarray]:
        """将原始目标转换为分布参数"""
        if self.spec["type"] == "normal":
            mu = y
            sigma = np.full_like(y, np.std(y) * 0.5 + 1e-3)
            return {"mu": mu, "log_sigma": np.log(sigma)}
        elif self.spec["type"] == "beta":
            v_min, v_max = self.spec["range"]
            vals = np.clip((y - v_min) / (v_max - v_min), 1e-6, 1-1e-6)
            mean = vals
            # 简单假设固定精度
            precision = 10.0
            alpha = mean * precision
            beta_p = (1 - mean) * precision
            return {"log_alpha": np.log(alpha), "log_beta": np.log(beta_p)}
        elif self.spec["type"] == "poisson":
            lam = np.maximum(y, 0.1)
            return {"log_lambda": np.log(lam)}
        return {"param": y}
    
    def _inverse_transform(self, params: Dict[str, float]) -> Tuple:
        if self.spec["type"] == "normal":
            return (params["mu"], max(math.exp(params["log_sigma"]), 1e-3))
        elif self.spec["type"] == "beta":
            alpha = max(math.exp(params["log_alpha"]), 0.1)
            beta_p = max(math.exp(params["log_beta"]), 0.1)
            return (alpha, beta_p)
        elif self.spec["type"] == "poisson":
            return (max(math.exp(params["log_lambda"]), 0.1),)
        return (params.get("param", 0),)
    
    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: List[str]):
        self.feature_names = feature_names
        y_params = self._transform_y(y)
        
        for param_name, y_param in y_params.items():
            if self.use_lgb:
                model = lgb.LGBMRegressor(
                    n_estimators=200,
                    learning_rate=0.05,
                    num_leaves=31,
                    min_child_samples=20,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    verbosity=-1,
                    n_jobs=-1,
                )
            else:
                from sklearn.linear_model import Ridge
                model = Ridge(alpha=1.0)
            model.fit(X, y_param)
            self.models[param_name] = model
    
    def predict_params(self, X: np.ndarray) -> Tuple:
        params = {}
        for param_name, model in self.models.items():
            params[param_name] = float(model.predict(X)[0])
        return self._inverse_transform(params)
    
    def get_importance(self) -> Dict[str, float]:
        if not self.use_lgb or not self.models:
            return {}
        imp = defaultdict(float)
        for model in self.models.values():
            if hasattr(model, "feature_importances_"):
                for name, val in zip(self.feature_names, model.feature_importances_):
                    imp[name] += val
        return {k: v / len(self.models) for k, v in imp.items()}


class DistributionEngine:
    """完整分布预测引擎"""
    
    def __init__(self, use_lgb: bool = True):
        self.models = {name: ParamModel(name, use_lgb) for name in TARGET_SPECS}
        self.feature_names = []
    
    def fit(self, X: np.ndarray, y_dict: Dict[str, np.ndarray], feature_names: List[str]):
        self.feature_names = feature_names
        for name in TARGET_SPECS:
            self.models[name].fit(X, y_dict[name], feature_names)
    
    def predict(self, X: np.ndarray) -> DistParams:
        if X.ndim == 1:
            X = X.reshape(1, -1)
        params = {}
        for name in TARGET_SPECS:
            params[name] = self.models[name].predict_params(X)
        return DistParams(params)
    
    def get_importance(self) -> Dict[str, float]:
        all_imp = defaultdict(float)
        for model in self.models.values():
            for k, v in model.get_importance().items():
                all_imp[k] += v
        return {k: v / len(self.models) for k, v in all_imp.items()}


# ═══════════════════════════════════════════════════════════
# Walk-Forward 回测
# ═══════════════════════════════════════════════════════════

def walk_forward_backtest(
    draws: List[Draw],
    initial_window: int = 500,
    n_rounds: int = None,
    use_lgb: bool = True,
) -> BacktestResult:
    
    total = len(draws)
    if n_rounds is None:
        n_rounds = total - initial_window
    n_rounds = min(n_rounds, total - initial_window)
    
    print(f"回测配置: 窗口={initial_window}, 轮数={n_rounds}, 总数据={len(draws)}")
    print(f"LightGBM: {'启用' if use_lgb and HAS_LGB else '禁用'}")
    print(f"SciPy: {'可用' if HAS_SCIPY else '不可用(近似CRPS)'}")
    print()
    
    # 初始化基线
    baselines = {
        "Empirical": EmpiricalBaseline(),
        "Theoretical": TheoreticalBaseline(),
        "Lag1": Lag1Baseline(),
        "Uniform": UniformBaseline(),
    }
    
    engine_crps = {name: [] for name in TARGET_SPECS.keys()} | {"avg": []}
    baseline_crps = {bname: {name: [] for name in TARGET_SPECS.keys()} | {"avg": []} for bname in baselines}
    round_results = []
    
    for round_idx in range(n_rounds):
        i = initial_window + round_idx
        train_draws = draws[:i]
        test_draw = draws[i]
        test_target = DistributionTarget.from_draw(test_draw)
        y_true = test_target.to_array()
        
        # 训练 Engine
        X_train, y_train, feature_names = prepare_dataset(draws, i)
        if len(X_train) < 100:
            continue
        
        engine = DistributionEngine(use_lgb=use_lgb)
        engine.fit(X_train, y_train, feature_names)
        
        # 测试特征
        X_test_feat = extract_features(draws, i)
        if not X_test_feat:
            continue
        X_test = np.array([[X_test_feat.get(k, 0) for k in engine.feature_names]])
        
        # Engine 预测
        engine_params = engine.predict(X_test)
        engine_crps_dict = compute_all_crps(y_true, engine_params)
        
        for name in TARGET_SPECS.keys():
            engine_crps[name].append(engine_crps_dict[name])
        engine_crps["avg"].append(engine_crps_dict["avg"])
        
        # 训练并评估所有基线
        baseline_crps_dict = {}
        for bname, baseline in baselines.items():
            baseline.fit([DistributionTarget.from_draw(d) for d in train_draws])
            b_params = baseline.predict()
            b_crps = compute_all_crps(y_true, b_params)
            baseline_crps_dict[bname] = b_crps
        
        for name in TARGET_SPECS.keys():
            for bname in baselines:
                baseline_crps[bname][name].append(baseline_crps_dict[bname][name])
            # avg 单独处理
        for bname in baselines:
            baseline_crps[bname]["avg"].append(baseline_crps_dict[bname]["avg"])
        
        # 统计检验
        p_values = {}
        if len(engine_crps.get("avg", [])) >= 10:
            for bname in baselines:
                eng = np.array(engine_crps["avg"])
                base = np.array(baseline_crps[bname]["avg"])
                diff = base - eng
                if np.std(diff) > 0:
                    t_stat = np.mean(diff) / (np.std(diff) / np.sqrt(len(diff)))
                    p_values[bname] = 0.5 * (1 + math.erf(t_stat / math.sqrt(2)))
                else:
                    p_values[bname] = 1.0
        
        # 记录详细结果
        round_results.append(RoundResult(
            period=test_draw.period,
            train_size=len(train_draws),
            crps=engine_crps,
            crps_avg=engine_crps["avg"],
            baseline_crps=baseline_crps_dict,
            p_values=p_values,
            model_weights={}
        ))
        
        # 进度
        if (round_idx + 1) % 5 == 0 or round_idx < 3:
            print(f"  第 {round_idx+1}/{n_rounds} 轮 (期{test_draw.period}): "
                  f"Engine={engine_crps_dict['avg']:.4f} | "
                  f"Emp={baseline_crps_dict['Empirical']['avg']:.4f} | "
                  f"Theo={baseline_crps_dict['Theoretical']['avg']:.4f} | "
                  f"Lag1={baseline_crps_dict['Lag1']['avg']:.4f} | "
                  f"Unif={baseline_crps_dict['Uniform']['avg']:.4f}")
    
    # 汇总
    eng_avg = {k: np.mean(v) for k, v in engine_crps.items() if v}
    base_avg = {b: {k: np.mean(v) for k, v in d.items() if v} for b, d in baseline_crps.items()}
    
    return BacktestResult(
        engine_crps=eng_avg,
        baseline_crps=base_avg,
        rounds=round_results,
        statistical_summary={
            "p_values": {b: np.mean([r.p_values.get(b, 1) for r in round_results]) for b in baselines},
            "wins_vs_empirical": sum(1 for r in round_results if r.crps_avg < r.baseline_crps["Empirical"]["avg"][-1]),
            "wins_vs_theoretical": sum(1 for r in round_results if r.crps_avg < r.baseline_crps["Theoretical"]["avg"][-1]),
            "wins_vs_lag1": sum(1 for r in round_results if r.crps_avg < r.baseline_crps["Lag1"]["avg"][-1]),
            "wins_vs_uniform": sum(1 for r in round_results if r.crps_avg < r.baseline_crps["Uniform"]["avg"][-1]),
            "crps_vs_empirical_ratio": eng_avg.get("avg", 1) / base_avg["Empirical"].get("avg", 1) if base_avg["Empirical"].get("avg") else 1,
        },
        config={"initial_window": initial_window, "n_rounds": len(round_results)},
        feature_importance={}
    )


# ═══════════════════════════════════════════════════════════
# 报告
# ═══════════════════════════════════════════════════════════

def print_report(result: BacktestResult):
    print("\n" + "=" * 80)
    print("  📊 双色球分布预测 Walk-Forward 回测报告 (参数预测 + CRPS + 多基线)")
    print("=" * 80)
    
    eng = result.engine_crps
    bases = result.baseline_crps
    stats = result.statistical_summary
    
    print(f"\n--- 配置: 窗口={result.config['initial_window']}, 轮数={result.config['n_rounds']} ---")
    
    print(f"\n--- CRPS 对比 (越小越好) ---")
    print(f"{'目标':<12} {'Engine':>8} {'Empirical':>10} {'Theoretical':>12} {'Lag1':>8} {'Uniform':>10} {'最优':>6}")
    print("-" * 78)
    for name in ["red_sum", "odd_ratio", "high_ratio", "span", "ac_value", "avg"]:
        e = result.engine_crps.get(name, 0)
        vals = {
            "Engine": result.engine_crps.get(name, 0),
            "Empirical": result.baseline_crps["Empirical"].get(name, 0),
            "Theoretical": result.baseline_crps["Theoretical"].get(name, 0),
            "Lag1": result.baseline_crps["Lag1"].get(name, 0),
            "Uniform": result.baseline_crps["Uniform"].get(name, 0),
        }
        best = min(vals, key=vals.get)
        markers = {k: ("✅" if k == best else " ") for k in vals}
        print(f"{name:<12} {vals['Engine']:>8.4f} {vals['Empirical']:>10.4f} {vals['Theoretical']:>12.4f} {vals['Lag1']:>8.4f} {vals['Uniform']:>10.4f} {markers[best]+best:>6}")
    
    print(f"\n--- 统计显著性 ---")
    for bname in ["Empirical", "Theoretical", "Lag1", "Uniform"]:
        p = stats["p_values"].get(bname, 1)
        wins = stats.get(f"wins_vs_{bname.lower()}", 0)
        total = sum(1 for _ in baselines)  # 近似
        print(f"  vs {bname:12s}: 平均p={p:.4f}, 胜率={wins}/{len([r for r in baselines]) if False else 'N/A'}")
    
    ratio = stats.get("crps_vs_empirical_ratio", 1)
    print(f"\n--- 核心结论 ---")
    if ratio < 0.95:
        print(f"  ✅ Engine CRPS < Empirical (比率 {ratio:.4f}) - 有真实信号！")
    elif ratio < 1.0:
        print(f"  ⚠️  Engine ≈ Empirical (比率 {ratio:.4f}) - 无显著优势")
    else:
        print(f"  ❌ Engine > Empirical (比率 {ratio:.4f}) - 无信号，纯噪声")
    
    print(f"\n  vs Empirical  胜率: {stats.get('wins_vs_empirical', 0)}/{len(baselines) if False else 'N/A'}")
    print(f"  vs Theoretical 胜率: {stats.get('wins_vs_theoretical', 0)}/N/A")
    print(f"  vs Lag1       胜率: {stats.get('wins_vs_lag1', 0)}/N/A")
    print(f"  vs Uniform    胜率: {stats.get('wins_vs_uniform', 0)}/N/A")


def generate_markdown(result: BacktestResult, path: str):
    # 简化版
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# 回测报告\n\nCRPS vs Empirical: {result.statistical_summary.get('crps_vs_empirical_ratio', 1):.4f}\n")


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

def run(csv_path=None, n_rounds=None, initial_window=None, use_lgb=True, output_dir=None):
    print("=" * 72)
    print("  🚀 双色球分布预测 Walk-Forward 回测 (参数预测 + 多基线 CRPS)")
    print("=" * 72)
    
    draws = load_history(csv_path)
    min_win = initial_window or INITIAL_WINDOW
    if len(draws) < min_win:
        print(f"数据不足")
        return
    
    result = walk_forward_backtest(draws, initial_window or INITIAL_WINDOW, n_rounds, use_lgb)
    print_report(result)
    
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))
    
    generate_markdown(result, os.path.join(output_dir, "walkforward_science_report.md"))
    
    # 保存 JSON
    with open(os.path.join(output_dir, "walkforward_science_results.json"), "w", encoding="utf-8") as f:
        json.dump({
            "engine_crps": result.engine_crps,
            "baseline_crps": result.baseline_crps,
            "statistical_summary": result.statistical_summary,
            "config": result.config,
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file")
    parser.add_argument("--n-rounds", type=int)
    parser.add_argument("--initial-window", type=int)
    parser.add_argument("--no-lgb", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    run(args.data_file, args.n_rounds, args.initial_window, not args.no_lgb, args.output_dir)