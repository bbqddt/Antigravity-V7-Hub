#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 非随机性先验向量生成器
====================================
将 22 项检测结果压缩为结构化先验向量，供 Luckcast/Enhanced/Evolution 直接注入使用
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any

_PROJECT_ROOT = Path(__file__).resolve().parent

# 先验向量维度定义 (固定 32 维，便于模型输入)
PRIOR_DIM = 32
DIM_NAMES = [
    # Hurst 指数偏离 (6 维，每位一维)
    "hurst_dev_pos1", "hurst_dev_pos2", "hurst_dev_pos3",
    "hurst_dev_pos4", "hurst_dev_pos5", "hurst_dev_pos6",
    # 游程检验 Z-score (6 维)
    "runs_z_pos1", "runs_z_pos2", "runs_z_pos3",
    "runs_z_pos4", "runs_z_pos5", "runs_z_pos6",
    # 互信息 MI lag-1 (6 维)
    "mi_lag1_pos1", "mi_lag1_pos2", "mi_lag1_pos3",
    "mi_lag1_pos4", "mi_lag1_pos5", "mi_lag1_pos6",
    # 排列熵偏离 (6 维)
    "pe_dev_pos1", "pe_dev_pos2", "pe_dev_pos3",
    "pe_dev_pos4", "pe_dev_pos5", "pe_dev_pos6",
    # ACF 积分 (1 维)
    "acf_integral_avg",
    # 跨位置互信息均值 (1 维)
    "cross_mi_avg",
    # 最强信号编码 (1 维，one-hot 索引)
    "strongest_signal_type",
]

# 信号类型编码
SIGNAL_TYPE_MAP = {
    "hurst": 1, "runs": 2, "spectral": 3, "mi": 4,
    "pe": 5, "lz": 6, "skewness": 7, "kurtosis": 8,
    "jb": 9, "cond_entropy": 10, "transfer_entropy": 11,
    "acf_integral": 12, "hurst_diff": 13, "cross_mi": 14,
    "rolling_drift": 15, "interval_ks": 16, "oe_runs": 17,
    "sum_hurst": 18, "sum_acf": 19, "chi_square": 20,
    "pair_acf": 21, "time_reversal": 22, "acf": 23,
}


def load_nonrandomness_results() -> Dict:
    """加载非随机性检测结果"""
    result_file = _PROJECT_ROOT / "nonrandomness_results.json"
    if not result_file.exists():
        return {}
    with open(result_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_position_prior() -> Dict:
    """加载结构化位置先验"""
    prior_file = _PROJECT_ROOT / "position_prior.json"
    if not prior_file.exists():
        return {}
    with open(prior_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_prior_vector() -> np.ndarray:
    """
    构建 32 维先验向量
    
    Returns:
        np.ndarray: shape (32,), 归一化到 [0, 1]
    """
    vector = np.zeros(PRIOR_DIM, dtype=np.float32)
    
    # 1. 优先读取 position_prior.json (结构化、已按位置组织)
    pos_prior = load_position_prior()
    pos_devs = pos_prior.get("position_deviations", {})
    
    if pos_devs:
        # Hurst 偏离 (6 维)
        for i in range(1, 7):
            key = str(i)
            val = pos_devs.get(key, {}).get("hurst_dev", 0)
            vector[i - 1] = min(abs(val) / 0.5, 1.0)  # 归一化：0.5 视为强偏离
        
        # 游程 Z-score (6 维)
        for i in range(1, 7):
            key = str(i)
            val = pos_devs.get(key, {}).get("runs_z", 0)
            vector[5 + i] = min(abs(val) / 3.0, 1.0)  # 归一化：Z>3 视为强
        
        # 互信息 lag-1 (6 维)
        for i in range(1, 7):
            key = str(i)
            val = pos_devs.get(key, {}).get("mi_lag1", 0)
            vector[11 + i] = min(val / 0.5, 1.0)
        
        # 排列熵偏离 (6 维)
        for i in range(1, 7):
            key = str(i)
            val = pos_devs.get(key, {}).get("pe_dev", 0)
            vector[17 + i] = min(val / 0.3, 1.0)
        
        # ACF 积分平均 (1 维)
        acf_vals = []
        for i in range(1, 7):
            key = str(i)
            val = pos_devs.get(key, {}).get("acf_int", 0)
            acf_vals.append(abs(val))
        vector[23] = min(np.mean(acf_vals) / 0.1, 1.0) if acf_vals else 0
        
        # 跨位置互信息平均 (1 维)
        cross_mi_vals = []
        for key, vals in pos_devs.items():
            if "cross_mi" in vals:
                cross_mi_vals.append(vals["cross_mi"])
        vector[24] = min(np.mean(cross_mi_vals) / 0.05, 1.0) if cross_mi_vals else 0
        
        # 最强信号类型 (1 维)
        strongest = pos_prior.get("strongest_signals", [])
        if strongest:
            top_signal = strongest[0]
            signal_type = top_signal.get("test", "hurst")
            vector[25] = SIGNAL_TYPE_MAP.get(signal_type, 0) / len(SIGNAL_TYPE_MAP)
    
    # 2. 回退：读取 nonrandomness_results.json (扁平结构)
    else:
        results = load_nonrandomness_results()
        deviations = results.get("deviations", [])
        
        # 按类型聚合
        by_type = {}
        for d in deviations:
            t = d["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(d["deviation"])
        
        # 填充可映射的维度
        if "hurst" in by_type:
            hurst_devs = by_type["hurst"][:6]
            for i, v in enumerate(hurst_devs):
                vector[i] = min(v / 0.5, 1.0)
        
        if "runs" in by_type:
            runs_devs = by_type["runs"][:6]
            for i, v in enumerate(runs_devs):
                vector[5 + i] = min(v / 3.0, 1.0)
        
        if "mi" in by_type:
            mi_devs = by_type["mi"][:6]
            for i, v in enumerate(mi_devs):
                vector[11 + i] = min(v / 0.5, 1.0)
        
        if "pe" in by_type:
            pe_devs = by_type["pe"][:6]
            for i, v in enumerate(pe_devs):
                vector[17 + i] = min(v / 0.3, 1.0)
        
        if "acf_integral" in by_type:
            vector[23] = min(np.mean(by_type["acf_integral"]) / 0.1, 1.0)
        
        if "cross_mi" in by_type:
            vector[24] = min(np.mean(by_type["cross_mi"]) / 0.05, 1.0)
        
        # 最强信号
        if deviations:
            top = max(deviations, key=lambda x: x["deviation"])
            vector[25] = SIGNAL_TYPE_MAP.get(top["type"], 0) / len(SIGNAL_TYPE_MAP)
    
    # 3. 剩余维度预留 (26-31) 给未来扩展
    # 目前填 0
    
    return vector


def save_prior_vector(vector: np.ndarray, path: Path = None):
    """保存先验向量为 JSON"""
    if path is None:
        path = _PROJECT_ROOT / "prior_vector.json"
    
    data = {
        "vector": vector.tolist(),
        "dim_names": DIM_NAMES,
        "shape": list(vector.shape),
        "dtype": str(vector.dtype),
        "generated_at": str(Path(__file__).stat().st_mtime),
        "version": "1.0",
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"先验向量已保存: {path}")


def load_prior_vector(path: Path = None) -> np.ndarray:
    """加载先验向量"""
    if path is None:
        path = _PROJECT_ROOT / "prior_vector.json"
    
    if not path.exists():
        return np.zeros(PRIOR_DIM, dtype=np.float32)
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return np.array(data["vector"], dtype=np.float32)


# ═══════════════════════════════════════════════════════════════
# 注入接口：供各引擎调用
# ═══════════════════════════════════════════════════════════════

def get_prior_for_luckcast() -> Dict[str, float]:
    """
    为 Luckcast V15 生成维度权重初始化向量
    映射：先验向量前 7 维 -> 7 个预测维度的初始权重偏移
    """
    vec = load_prior_vector()
    # 简单映射：取前 7 维平均作为基础偏移
    base_bias = float(np.mean(vec[:7])) if len(vec) >= 7 else 0.1
    
    return {
        "frequency_bias": base_bias,        # 频率维度
        "omission_bias": base_bias * 0.8,   # 遗漏维度
        "consecutive_bias": base_bias * 0.6, # 连号维度
        "zone_bias": base_bias * 0.7,       # 区间维度
        "ac_bias": base_bias * 0.5,         # AC值维度
        "sum_bias": base_bias * 0.6,        # 和值维度
        "blue_bias": base_bias * 0.4,       # 蓝球维度
    }


def get_prior_for_enhanced() -> Dict[str, Any]:
    """
    为 Enhanced Predictor 生成策略选择先验
    """
    vec = load_prior_vector()
    
    # 基于信号强度调整策略池权重
    signal_strength = float(np.mean(vec[:25])) if len(vec) >= 25 else 0.1
    
    strategy_weights = {
        "hot_core": 1.0 + signal_strength * 0.3,      # 热号策略
        "cold_strike": 1.0 + signal_strength * 0.2,   # 冷号反击
        "balanced": 1.0,                               # 基准
        "zone_control": 1.0 + signal_strength * 0.15, # 区间控制
        "consecutive": 1.0 + signal_strength * 0.1,   # 连号
        "omission": 1.0 + signal_strength * 0.25,     # 遗漏值
    }
    
    # 归一化
    total = sum(strategy_weights.values())
    strategy_weights = {k: v/total for k, v in strategy_weights.items()}
    
    return {
        "strategy_weights": strategy_weights,
        "signal_strength": signal_strength,
        "recommend_exploration": signal_strength > 0.3,
    }


def get_prior_for_evolution() -> Dict[str, Any]:
    """
    为 Formula Evolution 生成适应度函数调节参数
    """
    vec = load_prior_vector()
    signal_strength = float(np.mean(vec[:25])) if len(vec) >= 25 else 0.1
    
    return {
        "fitness_weights": {
            "score": 1.0,
            "beats_random": 0.5 + signal_strength,
            "brier_inverse": 0.3 + signal_strength * 0.5,
            "stability": 0.4 + signal_strength * 0.3,
            "complexity_penalty": 0.2,
        },
        "selection_pressure": 1.0 + signal_strength * 0.5,
        "mutation_rate_base": 0.1 * (1.0 - signal_strength * 0.5),  # 信号强则降低变异
        "elite_ratio": 0.1 + signal_strength * 0.1,
    }


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def main():
    vector = build_prior_vector()
    print(f"先验向量形状: {vector.shape}")
    print(f"非零维度: {np.count_nonzero(vector)} / {PRIOR_DIM}")
    print(f"均值: {np.mean(vector):.4f}, 最大值: {np.max(vector):.4f}")
    print(f"向量: {vector.round(4)}")
    
    save_prior_vector(vector)
    
    # 同时生成三引擎专用配置
    luckcast_cfg = get_prior_for_luckcast()
    enhanced_cfg = get_prior_for_enhanced()
    evolution_cfg = get_prior_for_evolution()
    
    with open(_PROJECT_ROOT / "prior_luckcast.json", 'w', encoding='utf-8') as f:
        json.dump(luckcast_cfg, f, ensure_ascii=False, indent=2)
    with open(_PROJECT_ROOT / "prior_enhanced.json", 'w', encoding='utf-8') as f:
        json.dump(enhanced_cfg, f, ensure_ascii=False, indent=2)
    with open(_PROJECT_ROOT / "prior_evolution.json", 'w', encoding='utf-8') as f:
        json.dump(evolution_cfg, f, ensure_ascii=False, indent=2)
    
    print("三引擎专用先验配置已生成:")
    print(f"  Luckcast: {luckcast_cfg}")
    print(f"  Enhanced: strategy_weights={enhanced_cfg['strategy_weights']}")
    print(f"  Evolution: fitness_weights={evolution_cfg['fitness_weights']}")


if __name__ == "__main__":
    main()