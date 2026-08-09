# -*- coding: utf-8 -*-
"""
Antigravity 演化预测引擎
基于多策略融合 + 动态权重学习
"""

import json
import os
import random
import sys
import time
import logging
import numpy as np
from collections import Counter
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "evolved_predictor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("EvolvedPredictor")

# 数据路径
DATA_FILE = _PROJECT_ROOT / "data" / "lottery_history.csv"
OUTPUT_FILE = _PROJECT_ROOT / "latest_predictions_evolved.json"
STATE_FILE = _PROJECT_ROOT / "evolved_state.json"


def load_data():
    """加载历史数据"""
    import pandas as pd
    df = pd.read_csv(str(DATA_FILE))
    df = df.sort_values("period", ascending=False).reset_index(drop=True)
    return df


def parse_reds(red_str):
    """解析红球字符串"""
    return [int(x.strip()) for x in str(red_str).split(",")]


class Strategy:
    """策略基类"""
    name = "base"

    def __init__(self, df):
        self.df = df

    def generate(self) -> Tuple[List[int], int]:
        raise NotImplementedError


class HotStrategy(Strategy):
    """热号策略"""
    name = "hot"

    def generate(self):
        all_reds = []
        for _, row in self.df.head(60).iterrows():
            all_reds.extend(parse_reds(row["red"]))
        freq = Counter(all_reds)
        hot = sorted(freq.keys(), key=lambda x: freq[x], reverse=True)[:15]
        reds = sorted(random.sample(hot, 6))
        blue = random.randint(1, 16)
        return reds, blue


class ColdStrategy(Strategy):
    """冷号策略"""
    name = "cold"

    def generate(self):
        all_reds = set()
        for _, row in self.df.head(30).iterrows():
            all_reds.update(parse_reds(row["red"]))
        cold = [i for i in range(1, 34) if i not in all_reds]
        if len(cold) < 6:
            cold = list(set(range(1, 34)) - set(random.sample(list(all_reds), min(20, len(all_reds)))))
        reds = sorted(random.sample(cold, min(6, len(cold))))
        if len(reds) < 6:
            reds = sorted(random.sample(range(1, 34), 6))
        blue = random.randint(1, 16)
        return reds, blue


class BalancedStrategy(Strategy):
    """均衡策略"""
    name = "balanced"

    def generate(self):
        all_reds = []
        for _, row in self.df.head(40).iterrows():
            all_reds.extend(parse_reds(row["red"]))
        freq = Counter(all_reds)
        hot = sorted(freq.keys(), key=lambda x: freq[x], reverse=True)[:10]
        cold = [i for i in range(1, 34) if i not in hot]
        selected = random.sample(hot, 3) + random.sample(cold, 3)
        reds = sorted(selected)
        blue = random.randint(1, 16)
        return reds, blue


class ZoneStrategy(Strategy):
    """区间控制策略"""
    name = "zone"

    def generate(self):
        zones = [list(range(1, 12)), list(range(12, 23)), list(range(23, 34))]
        reds = []
        for zone in zones:
            reds.extend(random.sample(zone, 2))
        reds = sorted(reds)
        blue = random.randint(1, 16)
        return reds, blue


class ConsecutiveStrategy(Strategy):
    """连号策略"""
    name = "consecutive"

    def generate(self):
        start = random.randint(1, 28)
        consecutive = list(range(start, start + random.choice([2, 3])))
        remaining = [i for i in range(1, 34) if i not in consecutive]
        reds = sorted(consecutive + random.sample(remaining, 6 - len(consecutive)))
        blue = random.randint(1, 16)
        return reds, blue


# 策略注册表
STRATEGIES = [
    HotStrategy,
    ColdStrategy,
    BalancedStrategy,
    ZoneStrategy,
    ConsecutiveStrategy,
]


class EvolvedPredictor:
    """演化预测引擎"""

    def __init__(self, df):
        self.df = df
        self.strategies = [cls(df) for cls in STRATEGIES]
        self.weights = self._load_weights()

    def _load_weights(self):
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("weights", {s.name: 1.0 for s in STRATEGIES})
        return {s.name: 1.0 for s in STRATEGIES}

    def _save_weights(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"weights": self.weights, "updated": datetime.now().isoformat()}, f, indent=2)

    def predict(self, num_groups=5) -> List[Dict]:
        """生成预测"""
        predictions = []
        for i in range(num_groups):
            # 按权重选择策略
            strategy_names = list(self.weights.keys())
            weights = [self.weights[n] for n in strategy_names]
            total = sum(weights)
            probs = [w / total for w in weights]
            chosen = np.random.choice(strategy_names, p=probs)

            # 生成号码
            strategy = next(s for s in self.strategies if s.name == chosen)
            reds, blue = strategy.generate()

            predictions.append({
                "group": i + 1,
                "strategy": chosen,
                "reds": reds,
                "blue": blue,
                "score": self.weights[chosen],
            })

        return predictions

    def update_weights(self, actual_reds, actual_blue):
        """根据实际开奖更新权重"""
        for strategy in self.strategies:
            # 模拟评估：如果策略生成的号码与实际重合度高，增加权重
            reds, blue = strategy.generate()
            hits = len(set(reds) & set(actual_reds))
            blue_hit = 1 if blue == actual_blue else 0
            score = hits + blue_hit * 0.5
            self.weights[strategy.name] = 0.9 * self.weights[strategy.name] + 0.1 * score
        self._save_weights()


def run_prediction(num_groups=5, mode="normal"):
    """主预测接口"""
    logger.info("=" * 50)
    logger.info("  Antigravity Evolved Predictor V1.0")
    logger.info("=" * 50)

    df = load_data()
    latest_period = int(df.iloc[0]["period"])
    target_period = latest_period + 1
    logger.info(f"数据: {len(df)} 期 | 最新: #{latest_period} | 目标: #{target_period}")

    predictor = EvolvedPredictor(df)
    predictions = predictor.predict(num_groups)

    # 输出
    output = {
        "target_period": target_period,
        "predictions": predictions,
        "engine": "Evolved Predictor V1.0",
        "timestamp": datetime.now().isoformat(),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"\n预测结果 - 第 {target_period} 期:")
    for p in predictions:
        red_str = ", ".join(f"{r:02d}" for r in p["reds"])
        logger.info(f"  组{p['group']} [{p['strategy']}]: 🔴[{red_str}] 🔵{p['blue']:02d}")

    logger.info(f"\n✅ 预测已保存至: {OUTPUT_FILE}")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--groups", type=int, default=5)
    parser.add_argument("--mode", default="normal")
    args = parser.parse_args()
    run_prediction(args.groups, args.mode)
