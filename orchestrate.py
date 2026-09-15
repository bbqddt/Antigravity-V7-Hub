# -*- coding: utf-8 -*-
"""
Antigravity 统一编排系统 V1.0
整合数据更新、非随机性检测、多引擎预测、结果融合
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Fix Windows GBK
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

LOG_DIR = _PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "orchestrate.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("Orchestrator")


def run_full_pipeline(top_k=5):
    """执行完整预测流水线"""
    logger.info("=" * 60)
    logger.info("  Antigravity 统一编排系统 V1.0")
    logger.info("=" * 60)

    # Step 1: 数据更新
    logger.info("\n[1/5] 数据采集...")
    try:
        from data_updater_v2 import main as updater_main
        updater_main()
        logger.info("[OK] 数据采集完成")
    except Exception as e:
        logger.error(f"[FAIL] 数据采集失败: {e}")

    # Step 2: 加载数据
    logger.info("\n[2/5] 加载历史数据...")
    try:
        from data_layer import load_history, get_latest_period
        draws = load_history()
        latest = get_latest_period(draws)
        target = int(latest) + 1
        logger.info(f"[OK] 数据: {len(draws)} 期 | 最新: #{latest} | 目标: #{target}")
    except Exception as e:
        logger.error(f"[FAIL] 数据加载失败: {e}")
        return None

    # Step 3: 非随机性检测
    logger.info("\n[3/5] 非随机性检测...")
    try:
        from nonrandomness_detector import run_detection
        signals = run_detection(draws)
        logger.info(f"[OK] 非随机性检测完成: {len(signals)} 个信号")
    except Exception as e:
        logger.warning(f"[WARN] 非随机性检测异常: {e}")
        signals = {}

    # Step 4: 多引擎预测
    logger.info("\n[4/5] 预测引擎...")
    predictions = []

    # Engine A: Luckcast V15
    try:
        from luckcast_antigravity_v1 import rank_candidates
        logger.info("[LAUNCH] 启动 Luckcast V15...")
        preds = rank_candidates(draws, n_candidates=1000, top_k=top_k)
        for p in preds:
            predictions.append({
                "engine": "Luckcast V15",
                "reds": list(p[0]),
                "blue": int(p[1]),
                "score": float(p[2]) if len(p) > 2 else 0.0,
            })
        logger.info(f"[OK] Luckcast V15: {len(preds)} 组预测")
    except Exception as e:
        logger.error(f"[FAIL] Luckcast V15: {e}")

    # Engine B: Enhanced Predictor
    try:
        from enhanced_predictor import run_prediction
        logger.info("[LAUNCH] 启动 Enhanced V2.0...")
        result = run_prediction(num_groups=top_k, mode="normal")
        if result and "predictions" in result:
            for p in result["predictions"]:
                predictions.append({
                    "engine": "Enhanced V2.0",
                    "reds": p.get("reds", []),
                    "blue": p.get("blue", 0),
                    "score": p.get("score", 0.0),
                })
            logger.info(f"[OK] Enhanced V2.0: {len(result['predictions'])} 组预测")
    except Exception as e:
        logger.error(f"[FAIL] Enhanced V2.0: {e}")

    # Step 5: 融合与输出
    logger.info("\n[5/5] 结果融合...")
    if not predictions:
        logger.error("[FAIL] 所有引擎均未产生预测")
        return None

    # 简单融合：按分数排序，去重
    seen = set()
    unique_preds = []
    for p in sorted(predictions, key=lambda x: x.get("score", 0), reverse=True):
        key = (tuple(sorted(p["reds"])), p["blue"])
        if key not in seen:
            seen.add(key)
            unique_preds.append(p)
        if len(unique_preds) >= top_k:
            break

    # 保存结果
    output = {
        "target_period": target,
        "timestamp": datetime.now().isoformat(),
        "total_engines": len(set(p["engine"] for p in predictions)),
        "total_candidates": len(predictions),
        "groups": [
            {
                "red": sorted(p["reds"]),
                "blue": p["blue"],
                "engine": p["engine"],
                "score": p.get("score", 0.0),
            }
            for p in unique_preds
        ],
    }

    output_path = _PROJECT_ROOT / "latest_prediction.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"[OK] 融合结果: {len(unique_preds)} 组预测已保存")
    logger.info("=" * 60)
    logger.info(f"  预测结果 - 第 {target} 期")
    logger.info("=" * 60)
    for i, p in enumerate(unique_preds, 1):
        red_str = ", ".join(f"{r:02d}" for r in sorted(p["reds"]))
        logger.info(f"  组{i} [{p['engine']}]: 🔴[{red_str}] 🔵{p['blue']:02d} (评分:{p.get('score', 0):.4f})")

    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5, help="输出预测组数")
    args = parser.parse_args()
    run_full_pipeline(top_k=args.top_k)
