# -*- coding: utf-8 -*-
"""
Walk-Forward Distribution Backtest for 双色球
目标：预测红球统计分布（和值、奇偶比、大小比、跨度），而非具体号码
评估指标：CRPS (Continuous Ranked Probability Score)
核心理念：单点预测必死，分布预测可验证
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
    print("⚠️  LightGBM 未安装，将使用简单线性回归作为兜底")

from data_layer import load_history, Draw


# ═══════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════
INITIAL_WINDOW = 500
MIN_WINDOW = 200
RANDOM_SEED = 42
N_RANDOM_ROUNDS = 100
N_QUANTILES = 9  # 分位数回归：0.1, 0.2, ..., 0.9

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


# ═══════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════

@dataclass
class DistributionTarget:
    """单期的分布目标值"""
    period: int
    red_sum: int           # 红球和值 (21-189)
    odd_ratio: float       # 奇数比例 (0-1, 步长 1/6)
    high_ratio: float      # 大数比例 (0-1, >17 为大)
    span: int              # 跨度 (max-min, 5-32)
    ac_value: int          # AC值 (复杂度)

    @staticmethod
    def from_draw(draw: Draw) -> "DistributionTarget":
        reds = sorted(draw.reds)
        red_sum = sum(reds)
        odd_count = sum(1 for r in reds if r % 2 == 1)
        high_count = sum(1 for r in reds if r > 17)
        span = reds[-1] - reds[0]
        
        # AC值计算
        diffs = set()
        for i in range(6):
            for j in range(i+1, 6):
                diffs.add(abs(reds[j] - reds[i]))
        ac_value = len(diffs) - 5  # 标准AC值定义
        
        return DistributionTarget(
            period=draw.period,
            red_sum=red_sum,
            odd_ratio=odd_count / 6.0,
            high_ratio=high_count / 6.0,
            span=span,
            ac_value=max(0, ac_value)
        )


@dataclass
class QuantilePrediction:
    """分位数预测结果"""
    quantiles: Dict[float, float]  # {0.1: val, 0.2: val, ..., 0.9: val}
    median: float
    mean: float
    std: float


@dataclass
class DistributionPrediction:
    """单期的完整分布预测"""
    period: int
    red_sum: QuantilePrediction
    odd_ratio: QuantilePrediction
    high_ratio: QuantilePrediction
    span: QuantilePrediction
    ac_value: QuantilePrediction


@dataclass
class RoundResult:
    period: int
    train_size: int
    crps_red_sum: float
    crps_odd_ratio: float
    crps_high_ratio: float
    crps_span: float
    crps_ac_value: float
    crps_avg: float
    random_crps_avg: float
    random_median_crps: float
    p_value: float
    model_weights: Dict[str, float]


@dataclass
class BacktestResult:
    engine: Dict[str, float]
    random_baseline: Dict[str, float]
    rounds: List[RoundResult]
    statistical_summary: Dict[str, float]
    config: Dict[str, Any]
    feature_importance: Dict[str, Dict[str, float]]


# ═══════════════════════════════════════════════════════════
# CRPS 计算 (核心评估指标)
# ═══════════════════════════════════════════════════════════

QUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
TARGET_NAMES = ["red_sum", "odd_ratio", "high_ratio", "span", "ac_value"]

def crps_quantile(y_true: float, quantiles: Dict[float, float]) -> float:
    """
    从分位数预测计算 CRPS
    CRPS = ∫ (F_pred(x) - F_true(x))^2 dx
    离散近似：sum over quantiles of (q - I(y_true <= q_val))^2 * delta_q
    """
    if not quantiles:
        return 1.0
    
    # 确保分位数单调
    sorted_q = sorted(quantiles.items())
    qs = [q for q, _ in sorted_q]
    vals = [v for _, v in sorted_q]
    
    # 修正单调性
    for i in range(1, len(vals)):
        if vals[i] < vals[i-1]:
            vals[i] = vals[i-1]
    
    crps = 0.0
    for i, (q, v) in enumerate(zip(qs, vals)):
        # 梯形积分近似
        if i == 0:
            width = qs[i] - 0
        elif i == len(qs) - 1:
            width = 1 - qs[i-1]
        else:
            width = (qs[i] - qs[i-1]) / 2 + (qs[i+1] - qs[i]) / 2 if i < len(qs)-1 else (qs[i] - qs[i-1])
        
        indicator = 1.0 if y_true <= v else 0.0
        crps += (q - indicator) ** 2 * width
    
    return crps


def crps_ensemble(y_true: float, samples: List[float]) -> float:
    """从样本集合计算 CRPS (用于随机基线)"""
    if not samples:
        return 1.0
    samples = sorted(samples)
    n = len(samples)
    crps = abs(y_true - samples[0]) + abs(y_true - samples[-1])
    for i in range(1, n):
        crps += 2 * (i / n - 0.5) * (samples[i] - samples[i-1])
    return crps / n


def compute_all_crps(pred: DistributionPrediction, target: DistributionTarget) -> Dict[str, float]:
    return {
        "red_sum": crps_quantile(target.red_sum, pred.red_sum.quantiles),
        "odd_ratio": crps_quantile(target.odd_ratio, pred.odd_ratio.quantiles),
        "high_ratio": crps_quantile(target.high_ratio, pred.high_ratio.quantiles),
        "span": crps_quantile(target.span, pred.span.quantiles),
        "ac_value": crps_quantile(target.ac_value, pred.ac_value.quantiles),
    }


# ═══════════════════════════════════════════════════════════
# 特征工程
# ═══════════════════════════════════════════════════════════

FEATURE_WINDOWS = [10, 20, 50, 100, 200]

def extract_features(draws: List[Draw], end_idx: int, windows: List[int] = None) -> Dict[str, float]:
    """从历史开奖数据提取特征"""
    if windows is None:
        windows = FEATURE_WINDOWS
    
    recent = draws[max(0, end_idx - max(windows)):end_idx]
    if len(recent) < min(windows):
        return {}
    
    targets = [DistributionTarget.from_draw(d) for d in recent]
    features = {}
    
    for w in windows:
        if len(targets) < w:
            continue
        window_targets = targets[-w:]
        
        # 红球和值统计
        sums = [t.red_sum for t in window_targets]
        features[f"sum_mean_{w}"] = np.mean(sums)
        features[f"sum_std_{w}"] = np.std(sums)
        features[f"sum_min_{w}"] = np.min(sums)
        features[f"sum_max_{w}"] = np.max(sums)
        features[f"sum_trend_{w}"] = sums[-1] - sums[0] if w > 1 else 0
        
        # 奇偶比
        odds = [t.odd_ratio for t in window_targets]
        features[f"odd_mean_{w}"] = np.mean(odds)
        features[f"odd_std_{w}"] = np.std(odds)
        
        # 大小比
        highs = [t.high_ratio for t in window_targets]
        features[f"high_mean_{w}"] = np.mean(highs)
        features[f"high_std_{w}"] = np.std(highs)
        
        # 跨度
        spans = [t.span for t in window_targets]
        features[f"span_mean_{w}"] = np.mean(spans)
        features[f"span_std_{w}"] = np.std(spans)
        
        # AC值
        acs = [t.ac_value for t in window_targets]
        features[f"ac_mean_{w}"] = np.mean(acs)
        features[f"ac_std_{w}"] = np.std(acs)
        
        # 最近一期
        if w == windows[0]:
            last = targets[-1]
            features["last_sum"] = last.red_sum
            features["last_odd"] = last.odd_ratio
            features["last_high"] = last.high_ratio
            features["last_span"] = last.span
            features["last_ac"] = last.ac_value
    
    # 跨窗口特征
    if len(targets) >= max(windows):
        all_sums = [t.red_sum for t in targets]
        features["sum_long_trend"] = all_sums[-1] - all_sums[0]
        features["sum_accel"] = (all_sums[-1] - all_sums[-min(10, len(all_sums))]) - \
                                (all_sums[-min(10, len(all_sums))] - all_sums[-min(20, len(all_sums))]) if len(all_sums) >= 20 else 0
    
    return features


def prepare_dataset(draws: List[Draw], start_idx: int, end_idx: int) -> Tuple[np.ndarray, Dict[str, np.ndarray], List[str]]:
    """准备训练数据 X, {y_target: y_array}, feature_names"""
    X_list = []
    y_dict = {name: [] for name in TARGET_NAMES}
    valid_indices = []
    
    for i in range(start_idx, end_idx):
        feat = extract_features(draws, i)
        if not feat:
            continue
        
        target = DistributionTarget.from_draw(draws[i])
        X_list.append(feat)
        y_dict["red_sum"].append(target.red_sum)
        y_dict["odd_ratio"].append(target.odd_ratio)
        y_dict["high_ratio"].append(target.high_ratio)
        y_dict["span"].append(target.span)
        y_dict["ac_value"].append(target.ac_value)
        valid_indices.append(i)
    
    if not X_list:
        return np.array([]), {}, []
    
    # 对齐特征列
    all_keys = set()
    for f in X_list:
        all_keys.update(f.keys())
    feature_names = sorted(all_keys)
    
    X = np.array([[f.get(k, 0.0) for k in feature_names] for f in X_list])
    y_arrays = {name: np.array(y_dict[name]) for name in TARGET_NAMES}
    
    return X, y_arrays, feature_names


# ═══════════════════════════════════════════════════════════
# 分位数回归模型
# ═══════════════════════════════════════════════════════════

class QuantileModel:
    """单目标分位数回归模型"""
    
    def __init__(self, target_name: str, use_lgb: bool = True):
        self.target_name = target_name
        self.use_lgb = use_lgb and HAS_LGB
        self.models = {}
        self.feature_names = []
    
    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: List[str]):
        self.feature_names = feature_names
        
        for q in QUANTILES:
            if self.use_lgb:
                model = lgb.LGBMRegressor(
                    objective="quantile",
                    alpha=q,
                    n_estimators=300,
                    learning_rate=0.05,
                    num_leaves=31,
                    min_child_samples=20,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=RANDOM_SEED,
                    verbosity=-1,
                    n_jobs=-1,
                )
                model.fit(X, y)
            else:
                # 简单线性回归兜底：用中位数 + 残差分位数
                from sklearn.linear_model import LinearRegression
                model = LinearRegression()
                model.fit(X, y)
            self.models[q] = model
    
    def predict_quantiles(self, X: np.ndarray) -> Dict[float, float]:
        preds = {}
        for q, model in self.models.items():
            preds[q] = float(model.predict(X)[0])
        # 确保单调性
        sorted_q = sorted(preds.items())
        for i in range(1, len(sorted_q)):
            if sorted_q[i][1] < sorted_q[i-1][1]:
                sorted_q[i] = (sorted_q[i][0], sorted_q[i-1][1])
        return dict(sorted_q)
    
    def get_feature_importance(self) -> Dict[str, float]:
        if not self.use_lgb or not self.models:
            return {}
        # 平均所有分位数的重要度
        imp = defaultdict(float)
        for model in self.models.values():
            if hasattr(model, "feature_importances_"):
                for name, val in zip(self.feature_names, model.feature_importances_):
                    imp[name] += val
        return {k: v / len(self.models) for k, v in imp.items()}


class DistributionPredictor:
    """完整的分布预测器（5个目标各自建模）"""
    
    def __init__(self, use_lgb: bool = True):
        self.models = {name: QuantileModel(name, use_lgb) for name in TARGET_NAMES}
        self.feature_names = []
    
    def fit(self, X: np.ndarray, y_dict: Dict[str, np.ndarray], feature_names: List[str]):
        self.feature_names = feature_names
        for name in TARGET_NAMES:
            self.models[name].fit(X, y_dict[name], feature_names)
    
    def predict(self, X: np.ndarray) -> DistributionPrediction:
        """预测单期的完整分布"""
        # X shape: (1, n_features) 或 (n_features,)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        result = DistributionPrediction(period=0,  # 稍后填入
            red_sum=QuantilePrediction({}, 0, 0, 0),
            odd_ratio=QuantilePrediction({}, 0, 0, 0),
            high_ratio=QuantilePrediction({}, 0, 0, 0),
            span=QuantilePrediction({}, 0, 0, 0),
            ac_value=QuantilePrediction({}, 0, 0, 0))
        
        for name in TARGET_NAMES:
            quantiles = self.models[name].predict_quantiles(X)
            vals = list(quantiles.values())
            qp = QuantilePrediction(
                quantiles=quantiles,
                median=quantiles[0.5],
                mean=np.mean(vals),
                std=np.std(vals)
            )
            setattr(result, name, qp)
        
        return result
    
    def get_all_feature_importance(self) -> Dict[str, Dict[str, float]]:
        return {name: model.get_feature_importance() for name, model in self.models.items()}


# ═══════════════════════════════════════════════════════════
# 朴素基线生成（基于训练数据的简单统计，不作弊）
# ═══════════════════════════════════════════════════════════

class NaiveBaseline:
    """朴素基线：只用训练数据的历史统计量预测，不作弊"""
    
    def __init__(self):
        self.stats = {}
    
    def fit(self, draws: List[Draw]):
        """从历史数据计算经验分布"""
        targets = [DistributionTarget.from_draw(d) for d in draws]
        
        # 计算经验分位数
        self.stats = {}
        for name in TARGET_NAMES:
            vals = [getattr(t, name) for t in targets]
            sorted_vals = sorted(vals)
            self.stats[name] = {
                "vals": vals,
                "sorted": sorted_vals,
                "mean": np.mean(vals),
                "std": np.std(vals),
                "quantiles": {q: sorted_vals[int(q * (len(sorted_vals) - 1))] for q in QUANTILES},
            }
    
    def predict(self) -> DistributionPrediction:
        """基于经验分布预测"""
        pred = DistributionPrediction(period=0,
            red_sum=QuantilePrediction({}, 0, 0, 0),
            odd_ratio=QuantilePrediction({}, 0, 0, 0),
            high_ratio=QuantilePrediction({}, 0, 0, 0),
            span=QuantilePrediction({}, 0, 0, 0),
            ac_value=QuantilePrediction({}, 0, 0, 0))
        
        for name in TARGET_NAMES:
            stat = self.stats.get(name, {})
            quantiles = stat.get("quantiles", {})
            mean = stat.get("mean", 0)
            std = stat.get("std", 0)
            
            # 平滑分位数
            smoothed = {}
            for q in QUANTILES:
                if q in stat.get("quantiles", {}):
                    smoothed[q] = stat["quantiles"][q]
                else:
                    # 插值
                    qs = sorted(stat.get("quantiles", {}).keys())
                    if not qs:
                        smoothed[q] = mean
                    else:
                        # 简单线性插值
                        idx = int(q * (len(stat.get("sorted", [mean])) - 1))
                        smoothed[q] = stat["sorted"][min(idx, len(stat["sorted"])-1)]
            
            qp = QuantilePrediction(
                quantiles=smoothed,
                median=stat.get("quantiles", {}).get(0.5, mean),
                mean=mean,
                std=std
            )
            setattr(pred, name, qp)
        
        return pred


def create_naive_baseline(train_draws: List[Draw]) -> NaiveBaseline:
    """创建并训练朴素基线"""
    baseline = NaiveBaseline()
    baseline.fit(train_draws)
    return baseline


# ═══════════════════════════════════════════════════════════
# Walk-Forward 回测主流程
# ═══════════════════════════════════════════════════════════

def walk_forward_distribution_backtest(
    draws: List[Draw],
    initial_window: int = 500,
    n_rounds: int = None,
    n_random: int = 100,
    use_lgb: bool = True,
) -> BacktestResult:
    
    total = len(draws)
    if n_rounds is None:
        n_rounds = total - initial_window
    n_rounds = min(n_rounds, total - initial_window)
    
    print(f"回测配置: 窗口={initial_window}, 轮数={n_rounds}, 总数据={total}")
    print(f"LightGBM: {'启用' if use_lgb and HAS_LGB else '禁用(回退线性)'}")
    print()
    
    engine_crps = {name: [] for name in TARGET_NAMES + ["avg"]}
    random_crps = {name: [] for name in TARGET_NAMES + ["avg"]}
    round_results = []
    
    for round_idx in range(n_rounds):
        i = initial_window + round_idx
        train_data = draws[:i]
        test_draw = draws[i]
        test_target = DistributionTarget.from_draw(test_draw)
        
        # 准备训练数据
        X_train, y_train, feature_names = prepare_dataset(draws, 0, i)
        if len(X_train) < 100:
            print(f"  第 {round_idx+1} 轮: 训练数据不足 ({len(X_train)})，跳过")
            continue
        
        # 训练模型
        predictor = DistributionPredictor(use_lgb=use_lgb)
        predictor.fit(X_train, y_train, feature_names)
        
        # 准备测试特征
        X_test_feat = extract_features(draws, i)
        if not X_test_feat:
            continue
        X_test = np.array([[X_test_feat.get(k, 0.0) for k in predictor.feature_names]])
        
        # Engine 预测
        engine_pred = predictor.predict(X_test)
        engine_pred.period = test_draw.period
        
        # 计算 CRPS
        engine_crps_dict = compute_all_crps(engine_pred, test_target)
        engine_avg_crps = np.mean(list(engine_crps_dict.values()))
        
        for name in TARGET_NAMES:
            engine_crps[name].append(engine_crps_dict[name])
        engine_crps["avg"].append(engine_avg_crps)
        
        # 朴素基线（基于训练数据的经验分布，不作弊）
        naive_baseline = create_naive_baseline(train_data)
        naive_pred = naive_baseline.predict()
        naive_crps_dict = compute_all_crps(naive_pred, test_target)
        naive_avg_crps = np.mean(list(naive_crps_dict.values()))
        
        for name in TARGET_NAMES:
            random_crps[name].append(naive_crps_dict[name])
        random_crps["avg"].append(naive_avg_crps)
        
        # 统计检验
        p_val = 1.0
        if len(engine_crps["avg"]) >= 10:
            eng_arr = np.array(engine_crps["avg"])
            rnd_arr = np.array(random_crps["avg"])
            # 单侧 t 检验：Engine CRPS < Random CRPS
            diff = rnd_arr - eng_arr  # 正值表示 Engine 更好
            if np.std(diff) > 0:
                t_stat = np.mean(diff) / (np.std(diff) / np.sqrt(len(diff)))
                p_val = 0.5 * (1 + math.erf(t_stat / math.sqrt(2)))
        
        round_results.append(RoundResult(
            period=test_draw.period,
            train_size=len(train_data),
            crps_red_sum=engine_crps_dict["red_sum"],
            crps_odd_ratio=engine_crps_dict["odd_ratio"],
            crps_high_ratio=engine_crps_dict["high_ratio"],
            crps_span=engine_crps_dict["span"],
            crps_ac_value=engine_crps_dict["ac_value"],
            crps_avg=engine_avg_crps,
            random_crps_avg=naive_avg_crps,
            random_median_crps=naive_avg_crps,
            p_value=p_val,
            model_weights={}
        ))
        
        # === 逐轮详细诊断 ===
        if round_idx < 5 or round_idx % 5 == 0:
            print(f"\n  🔍 第 {round_idx+1} 轮 (期号 {test_draw.period}) 诊断:")
            print(f"    真实值: sum={test_target.red_sum}, odd={test_target.odd_ratio:.2f}, high={test_target.high_ratio:.2f}, span={test_target.span}, ac={test_target.ac_value}")
            for name in TARGET_NAMES:
                eng_qp = getattr(engine_pred, name)
                naive_qp = getattr(naive_pred, name)
                true_val = getattr(test_target, name)
                print(f"    {name}: 真值={true_val:.2f} | Engine分位数={list(eng_qp.quantiles.values())} | Naive分位数={list(naive_qp.quantiles.values())} | EngineCRPS={engine_crps_dict[name]:.4f} | NaiveCRPS={naive_crps_dict[name]:.4f}")
        
        # 进度
        if (round_idx + 1) % 5 == 0:
            print(f"  已完成 {round_idx+1}/{n_rounds} 轮 | Engine CRPS: {engine_avg_crps:.4f} | Naive: {naive_avg_crps:.4f} | p={p_val:.4f}")
    
    # 汇总
    eng_avg = {name: np.mean(vals) for name, vals in engine_crps.items() if vals}
    rnd_avg = {name: np.mean(vals) for name, vals in random_crps.items() if vals}
    
    # 获取特征重要度（最后一轮模型）
    feature_importance = predictor.get_all_feature_importance() if 'predictor' in locals() else {}
    
    result = BacktestResult(
        engine=eng_avg,
        random_baseline=rnd_avg,
        rounds=round_results,
        statistical_summary={
            "p_value_significant": sum(1 for r in round_results if r.p_value < 0.05) / len(round_results) if round_results else 0,
            "mean_p_value": np.mean([r.p_value for r in round_results]) if round_results else 1.0,
            "wins_over_random": sum(1 for r in round_results if r.crps_avg < r.random_crps_avg),
            "crps_vs_random_ratio": eng_avg.get("avg", 1) / rnd_avg.get("avg", 1) if rnd_avg.get("avg", 1) > 0 else 1.0,
        },
        config={
            "initial_window": initial_window,
            "n_rounds": len(round_results),
            "n_random_rounds": 100,
        },
        feature_importance=feature_importance,
    )
    
    return result


# ═══════════════════════════════════════════════════════════
# 报告生成
# ═══════════════════════════════════════════════════════════

def print_distribution_report(result: BacktestResult):
    eng = result.engine
    rnd = result.random_baseline
    stats = result.statistical_summary
    
    print("\n" + "=" * 72)
    print("  📊 分布预测 Walk-Forward 回测报告 (CRPS)")
    print("=" * 72)
    
    print(f"\n--- 配置 ---")
    print(f"  初始窗口: {result.config['initial_window']} 期")
    print(f"  回测轮数: {result.config['n_rounds']}")
    
    print(f"\n--- Engine CRPS (越小越好) ---")
    for name in TARGET_NAMES:
        e = result.engine.get(name, 0)
        r = result.random_baseline.get(name, 0)
        ratio = e / r if r > 0 else 1
        status = "✅" if ratio < 0.95 else ("⚠️" if ratio < 1.05 else "❌")
        print(f"  {name:10s}: Engine={eng.get(name,0):.4f} | Random={result.random_baseline.get(name,0):.4f} | Ratio={e/result.random_baseline.get(name,1):.4f} {status}")
    
    e_avg = eng.get("avg", 0)
    r_avg = result.random_baseline.get("avg", 1)
    ratio_avg = e_avg / r_avg if r_avg > 0 else 1
    status_avg = "✅" if ratio_avg < 0.95 else ("⚠️" if ratio_avg < 1.05 else "❌")
    print(f"  {'平均':10s}: Engine={e_avg:.4f} | Random={result.random_baseline.get('avg',0):.4f} | Ratio={ratio_avg:.4f} {status_avg}")
    
    stats = result.statistical_summary
    print(f"\n--- 统计显著性 ---")
    print(f"  显著优于随机 (p<0.05) 轮数占比: {stats['p_value_significant']:.2%}")
    print(f"  平均 p 值: {stats['mean_p_value']:.4f}")
    print(f"  CRPS 胜过随机轮数: {stats['wins_over_random']}/{result.config['n_rounds']}")
    print(f"  CRPS 比率 (Engine/Random): {stats['crps_vs_random_ratio']:.4f}  (<1.0 表示更好)")
    
    # 结论
    ratio = stats['crps_vs_random_ratio']
    print(f"\n--- 结论 ---")
    if ratio < 0.95:
        print(f"  ✅ CRPS 比率 {ratio:.4f} < 0.95，分布预测显著优于随机")
    elif ratio < 1.0:
        print(f"  ⚠️  CRPS 比率 {ratio:.4f} ≈ 1.0，与随机相当")
    else:
        print(f"  ❌ CRPS 比率 {ratio:.4f} > 1.0，差于随机")
    
    # 特征重要度
    if result.feature_importance:
        print(f"\n--- 特征重要度 Top 10 (各目标平均) ---")
        all_imp = defaultdict(float)
        for target_imp in result.feature_importance.values():
            for k, v in target_imp.items():
                all_imp[k] += v
        for k, v in sorted(all_imp.items(), key=lambda x: -x[1])[:10]:
            print(f"  {k:<25s}: {v:.2f}")


def generate_markdown_report(result: BacktestResult, output_path: str):
    eng = result.engine
    rnd = result.random_baseline
    stats = result.statistical_summary
    
    lines = []
    lines.append("# 📊 双色球分布预测 Walk-Forward 回测报告 (CRPS)")
    lines.append(f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> **配置**: 初始窗口={result.config['initial_window']}, 回测轮数={result.config['n_rounds']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📈 Engine vs Random CRPS 对比")
    lines.append("")
    lines.append("| 目标 | Engine CRPS | Random CRPS | Ratio | 状态 |")
    lines.append("|------|-------------|-------------|-------|------|")
    for name in TARGET_NAMES:
        e = result.engine.get(name, 0)
        r = result.random_baseline.get(name, 0)
        ratio = e / r if r > 0 else 1
        status = "✅" if ratio < 0.95 else ("⚠️" if ratio < 1.05 else "❌")
        lines.append(f"| {name} | {result.engine.get(name,0):.4f} | {result.random_baseline.get(name,0):.4f} | {ratio:.4f} | {status} |")
    e_avg = result.engine.get("avg", 0)
    r_avg = result.random_baseline.get("avg", 1)
    ratio_avg = e_avg / r_avg if r_avg > 0 else 1
    status_avg = "✅" if ratio_avg < 0.95 else ("⚠️" if ratio_avg < 1.05 else "❌")
    lines.append(f"| **平均** | **{e_avg:.4f}** | **{result.random_baseline.get('avg',0):.4f}** | **{ratio_avg:.4f}** | {status_avg} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📊 统计显著性")
    lines.append("")
    lines.append(f"- 显著优于随机 (p<0.05) 的轮数占比: {stats['p_value_significant']:.2%}")
    lines.append(f"- 平均 p 值: {stats['mean_p_value']:.4f}")
    lines.append(f"- CRPS 胜过随机轮数: {stats['wins_over_random']}/{result.config['n_rounds']}")
    lines.append(f"- CRPS 比率 (Engine/Random): {stats['crps_vs_random_ratio']:.4f}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🎯 理论随机基线")
    lines.append("")
    lines.append("| 指标 | 理论值 |")
    lines.append("|------|--------|")
    lines.append("| 红球和值均值 | 105 |")
    lines.append("| 红球和值标准差 | ~15 |")
    lines.append("| 奇偶比均值 | 0.5 |")
    lines.append("| 大小比均值 | 0.5 |")
    lines.append("| 跨度均值 | ~24 |")
    lines.append("| CRPS 随机基线 (各目标) | 见上表 Random 列 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🔍 结论")
    lines.append("")
    ratio = stats['crps_vs_random_ratio']
    if ratio < 0.95:
        lines.append(f"> ✅ CRPS 比率 {ratio:.4f} < 0.95，分布预测显著优于随机。")
    elif ratio < 1.0:
        lines.append(f"> ⚠️  CRPS 比率 {ratio:.4f} ≈ 1.0，与随机相当。")
    else:
        lines.append(f"> ❌ CRPS 比率 {ratio:.4f} > 1.0，差于随机。")
    lines.append("")
    lines.append("---")
    lines.append(f'*"分布才是真相，单点只是噪声的一个采样。"*')
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

def run(csv_path=None, n_rounds=None, initial_window=None, use_lgb=True, output_dir=None):
    print("=" * 72)
    print("  🚀 双色球分布预测 Walk-Forward 回测 (CRPS)")
    print("=" * 72)
    
    draws = load_history(csv_path)
    min_win = initial_window or 500
    if len(draws) < min_win:
        print(f"数据量不足 ({len(draws)} 期)，需要至少 {min_win} 期。")
        return
    
    result = walk_forward_distribution_backtest(
        draws,
        initial_window=initial_window or 500,
        n_rounds=n_rounds,
        use_lgb=use_lgb,
    )
    
    print_distribution_report(result)
    
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))
    
    report_path = os.path.join(output_dir, "walkforward_distribution_report.md")
    generate_markdown_report(result, report_path)
    print(f"\n>>> Markdown 报告已保存: {report_path}")
    
    data_path = os.path.join(output_dir, "walkforward_distribution_results.json")
    serializable = {
        "engine": result.engine,
        "random_baseline": result.random_baseline,
        "statistical_summary": result.statistical_summary,
        "config": result.config,
        "rounds": [
            {
                "period": r.period,
                "train_size": r.train_size,
                "crps_red_sum": r.crps_red_sum,
                "crps_odd_ratio": r.crps_odd_ratio,
                "crps_high_ratio": r.crps_high_ratio,
                "crps_span": r.crps_span,
                "crps_ac_value": r.crps_ac_value,
                "crps_avg": r.crps_avg,
                "random_crps_avg": r.random_crps_avg,
                "p_value": r.p_value,
            }
            for r in result.rounds
        ],
        "feature_importance": result.feature_importance,
    }
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    print(f">>> 原始数据已保存: {data_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分布预测 Walk-Forward 回测 (CRPS)")
    parser.add_argument("--data-file", help="CSV 数据文件路径")
    parser.add_argument("--n-rounds", type=int, help="回测轮数")
    parser.add_argument("--initial-window", type=int, help="初始训练窗口大小")
    parser.add_argument("--no-lgb", action="store_true", help="禁用 LightGBM，使用线性回归")
    parser.add_argument("--output-dir", help="输出目录")
    args = parser.parse_args()
    
    run(
        csv_path=args.data_file,
        n_rounds=args.n_rounds,
        initial_window=args.initial_window,
        use_lgb=not args.no_lgb,
        output_dir=args.output_dir,
    )