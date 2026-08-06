# -*- coding: utf-8 -*-
"""
Antigravity 回测与演化引擎
策略评估 + 自动演化优化
"""

import json
import os
import random
import sys
import logging
import numpy as np
from collections import Counter
from typing import List, Dict, Tuple
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "backtest_evolve.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("BacktestEvolve")

DATA_FILE = _PROJECT_ROOT / "data" / "lottery_history.csv"
RESULTS_FILE = _PROJECT_ROOT / "backtest_results.json"
STATE_FILE = _PROJECT_ROOT / "evolution_state.json"


def load_data():
    import pandas as pd
    df = pd.read_csv(str(DATA_FILE))
    df = df.sort_values("period", ascending=True).reset_index(drop=True)
    return df


def parse_reds(red_str):
    return [int(x.strip()) for x in str(red_str).split(",")]


class Strategy:
    name = "base"

    def __init__(self, df):
        self.df = df

    def generate(self) -> Tuple[List[int], int]:
        raise NotImplementedError


class HotStrategy(Strategy):
    name = "hot"

    def generate(self):
        all_reds = []
        for _, row in self.df.head(50).iterrows():
            all_reds.extend(parse_reds(row["red"]))
        freq = Counter(all_reds)
        hot = sorted(freq.keys(), key=lambda x: freq[x], reverse=True)[:12]
        reds = sorted(random.sample(hot, 6))
        return reds, random.randint(1, 16)


class ColdStrategy(Strategy):
    name = "cold"

    def generate(self):
        recent = set()
        for _, row in self.df.head(20).iterrows():
            recent.update(parse_reds(row["red"]))
        cold = [i for i in range(1, 34) if i not in recent]
        if len(cold) < 6:
            cold = list(range(1, 34))
        reds = sorted(random.sample(cold, 6))
        return reds, random.randint(1, 16)


class RandomStrategy(Strategy):
    name = "random"

    def generate(self):
        reds = sorted(random.sample(range(1, 34), 6))
        return reds, random.randint(1, 16)


STRATEGIES = [HotStrategy, ColdStrategy, RandomStrategy]


def backtest_strategy(strategy_cls, df, test_periods=30):
    """回测单个策略"""
    hits_list = []
    for i in range(test_periods):
        if len(df) < i + 2:
            break
        train_df = df.iloc[:-(i + 1)]
        test_row = df.iloc[-(i + 1)]
        actual_reds = set(parse_reds(test_row["red"]))
        actual_blue = int(test_row["blue"])

        strategy = strategy_cls(train_df)
        pred_reds, pred_blue = strategy.generate()

        red_hits = len(set(pred_reds) & actual_reds)
        blue_hit = 1 if pred_blue == actual_blue else 0
        hits_list.append(red_hits + blue_hit * 0.5)

    return sum(hits_list) / len(hits_list) if hits_list else 0


def run_backtest(test_periods=30):
    """运行回测"""
    logger.info("=" * 50)
    logger.info("  Antigravity 回测与演化系统")
    logger.info("=" * 50)

    df = load_data()
    logger.info(f"数据: {len(df)} 期 | 回测期数: {test_periods}")

    results = {}
    for strategy_cls in STRATEGIES:
        logger.info(f"\n回测策略: {strategy_cls.name}...")
        avg_hits = backtest_strategy(strategy_cls, df, test_periods)
        results[strategy_cls.name] = {
            "avg_hits": round(avg_hits, 3),
            "periods": test_periods,
        }
        logger.info(f"  平均命中: {avg_hits:.3f}/6.5")

    # 找出最佳策略
    best = max(results, key=lambda x: results[x]["avg_hits"])
    logger.info(f"\n🏆 最佳策略: {best} ({results[best]['avg_hits']:.3f})")

    # 保存结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "test_periods": test_periods,
        "results": results,
        "best_strategy": best,
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 回测结果已保存至: {RESULTS_FILE}")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--periods", type=int, default=30)
    args = parser.parse_args()
    run_backtest(args.periods)
