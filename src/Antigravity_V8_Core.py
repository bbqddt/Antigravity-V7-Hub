# -*- coding: utf-8 -*-
"""
Antigravity V8 核心引擎
经典预测算法 + 多维度分析
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
        logging.FileHandler(LOG_DIR / "v8_core.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("V8Core")

DATA_FILE = _PROJECT_ROOT / "data" / "lottery_history.csv"
OUTPUT_FILE = _PROJECT_ROOT / "latest_decision_v8.json"


def load_data():
    import pandas as pd
    df = pd.read_csv(str(DATA_FILE))
    df = df.sort_values("period", ascending=False).reset_index(drop=True)
    return df


def parse_reds(red_str):
    return [int(x.strip()) for x in str(red_str).split(",")]


class V8Core:
    """V8 核心引擎"""

    def __init__(self, df):
        self.df = df
        self.all_reds = []
        for _, row in df.head(100).iterrows():
            self.all_reds.extend(parse_reds(row["red"]))
        self.freq = Counter(self.all_reds)

    def score_number(self, num: int, position: int = 0) -> float:
        """号码评分"""
        freq_score = self.freq.get(num, 0) / max(len(self.df), 1)
        # 位置偏好
        pos_bias = 1.0 - abs(position - 2.5) * 0.1
        return freq_score * pos_bias

    def generate_group(self) -> Tuple[List[int], int, float]:
        """生成一组号码"""
        # 从高频号码中选择
        candidates = sorted(self.freq.keys(), key=lambda x: self.freq[x], reverse=True)[:20]
        weights = [self.freq[c] for c in candidates]
        total = sum(weights)
        probs = [w / total for w in weights]

        selected = set()
        while len(selected) < 6:
            choice = np.random.choice(candidates, p=probs)
            selected.add(choice)

        reds = sorted(selected)
        blue = random.randint(1, 16)
        score = sum(self.freq[r] for r in reds) / 100.0

        return reds, blue, score

    def predict(self, num_groups=5) -> List[Dict]:
        predictions = []
        for i in range(num_groups):
            reds, blue, score = self.generate_group()
            predictions.append({
                "group": i + 1,
                "red": [int(r) for r in reds],
                "blue": int(blue),
                "score": float(round(score, 4)),
            })
        return predictions


def run_v8(num_groups=5):
    """主接口"""
    logger.info("=" * 50)
    logger.info("  Antigravity V8 Core Engine")
    logger.info("=" * 50)

    df = load_data()
    latest_period = int(df.iloc[0]["period"])
    target_period = latest_period + 1
    logger.info(f"数据: {len(df)} 期 | 最新: #{latest_period} | 目标: #{target_period}")

    engine = V8Core(df)
    predictions = engine.predict(num_groups)

    output = {
        "target_period": target_period,
        "engine": "V8 Core",
        "groups": predictions,
        "timestamp": datetime.now().isoformat(),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"\n预测结果 - 第 {target_period} 期:")
    for p in predictions:
        red_str = ", ".join(f"{r:02d}" for r in p["red"])
        logger.info(f"  组{p['group']}: 🔴[{red_str}] 🔵{p['blue']:02d} (评分:{p['score']})")

    logger.info(f"\n✅ 预测已保存至: {OUTPUT_FILE}")
    return output


if __name__ == "__main__":
    import sys
    num_groups = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_v8(num_groups)
