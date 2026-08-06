# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import csv
import random
from typing import List, Dict

import pandas as pd
import streamlit as st

# ===== 反重力模块导入 =====
from luckcast_antigravity_v1 import Draw, rank_candidates, final_score

# =========================
# 页面基础配置
# =========================
st.set_page_config(page_title="Antigravity Command Center", layout="wide")
st.title("Antigravity Command Center - NemoClaw 堡垒 V20.3")
st.caption("交叉火力 + 反重力扰动 + 历史回测一体化堡垒")

# =========================
# 路径配置
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "ssq_history.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "latest_predictions.csv")

os.makedirs(DATA_DIR, exist_ok=True)

# =========================
# Session 初始化
# =========================
if "fortress_log_buf" not in st.session_state:
    st.session_state.fortress_log_buf = []

if "crossfire_results" not in st.session_state:
    st.session_state.crossfire_results = []

if "antigravity_results" not in st.session_state:
    st.session_state.antigravity_results = []

if "backtest_results" not in st.session_state:
    st.session_state.backtest_results = None

if "history_df" not in st.session_state:
    st.session_state.history_df = None

if "history_draws" not in st.session_state:
    st.session_state.history_draws = []

# =========================
# 工具函数
# =========================
def log(msg: str):
    st.session_state.fortress_log_buf.append(msg)

def format_red(nums: List[int]) -> str:
    return " ".join(f"{x:02d}" for x in nums)

def safe_int(x, default=0):
    try:
        return int(x)
    except:
        return default

# =========================
# 历史数据载入
# =========================
def load_history():
    if not os.path.exists(DATA_FILE):
        log(f"⚠ 未找到历史数据文件：{DATA_FILE}")
        st.session_state.history_df = pd.DataFrame()
        st.session_state.history_draws = []
        return

    try:
        df = pd.read_csv(DATA_FILE)
        required = ["r1", "r2", "r3", "r4", "r5", "r6", "blue"]
        for col in required:
            if col not in df.columns:
                raise ValueError(f"缺少字段: {col}")

        draws = []
        for _, row in df.iterrows():
            red = [
                safe_int(row["r1"]), safe_int(row["r2"]), safe_int(row["r3"]),
                safe_int(row["r4"]), safe_int(row["r5"]), safe_int(row["r6"])
            ]
            blue = safe_int(row["blue"])
            try:
                draws.append(Draw(sorted(red), blue))
            except:
                pass

        st.session_state.history_df = df
        st.session_state.history_draws = draws
        log(f"✅ 已载入历史数据 {len(draws)} 期")

    except Exception as e:
        log(f"❌ 历史数据载入失败: {e}")
        st.session_state.history_df = pd.DataFrame()
        st.session_state.history_draws = []

load_history()

# =========================
# 交叉火力模块（简化稳定版）
# =========================
def generate_crossfire_predictions(n=5):
    history = st.session_state.history_draws
    if len(history) < 5:
        return []

    reds_pool = list(range(1, 34))
    blues_pool = list(range(1, 17))
    results = []

    for _ in range(n):
        red = sorted(random.sample(reds_pool, 6))
        blue = random.choice(blues_pool)
        results.append({"red": red, "blue": blue})

    return results

# =========================
# 反重力模块
# =========================
def generate_antigravity_predictions(top_k=5, n_candidates=1000):
    history = st.session_state.history_draws
    if len(history) < 10:
        return []

    ranked = rank_candidates(history, n_candidates=n_candidates, top_k=top_k)
    result = []

    for red, blue, score in ranked:
        result.append({
            "red": red,
            "blue": blue,
            "score": score
        })

    return result

# =========================
# 导出结果
# =========================
def export_predictions():
    rows = []

    for i, x in enumerate(st.session_state.crossfire_results, start=1):
        rows.append({
            "type": "crossfire",
            "rank": i,
            "red": format_red(x["red"]),
            "blue": f'{x["blue"]:02d}',
            "total_score": ""
        })

    for i, x in enumerate(st.session_state.antigravity_results, start=1):
        rows.append({
            "type": "antigravity",
            "rank": i,
            "red": format_red(x["red"]),
            "blue": f'{x["blue"]:02d}',
            "total_score": x["score"]["total_score"]
        })

    if rows:
        pd.DataFrame(rows).to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        return True
    return False

# =========================
# 历史回测
# =========================
def run_backtest(warmup=15, top_k=5):
    history = st.session_state.history_draws
    if len(history) < warmup + 5:
        return None

    details = []

    top1_red2 = 0
    top1_red3 = 0
    top1_blue = 0

    top5_red2 = 0
    top5_red3 = 0
    top5_red4 = 0
    top5_blue = 0

    test_count = 0

    for i in range(warmup, len(history)):
        past = history[:i]
        actual = history[i]

        ranked = rank_candidates(past, n_candidates=600, top_k=top_k)
        if not ranked:
            continue

        test_count += 1

        # Top1
        red1, blue1, _ = ranked[0]
        hit_red1 = len(set(red1) & set(actual.red))
        hit_blue1 = int(blue1 == actual.blue)

        if hit_red1 >= 2:
            top1_red2 += 1
        if hit_red1 >= 3:
            top1_red3 += 1
        if hit_blue1:
            top1_blue += 1

        # Top5
        max_red_hit = 0
        any_blue_hit = 0

        for red, blue, _ in ranked:
            red_hit = len(set(red) & set(actual.red))
            max_red_hit = max(max_red_hit, red_hit)
            if blue == actual.blue:
                any_blue_hit = 1

        if max_red_hit >= 2:
            top5_red2 += 1
        if max_red_hit >= 3:
            top5_red3 += 1
        if max_red_hit >= 4:
            top5_red4 += 1
        if any_blue_hit:
            top5_blue += 1

        details.append({
            "期号": i + 1,
            "实际红球": format_red(actual.red),
            "实际蓝球": f"{actual.blue:02d}",
            "TOP1预测": f"{format_red(red1)} | {blue1:02d}",
            "TOP1红命中": hit_red1,
            "TOP1蓝命中": hit_blue1,
            "TOP5最大红命中": max_red_hit,
            "TOP5蓝命中": any_blue_hit
        })

    if test_count == 0:
        return None

    summary = {
        "回测期数": test_count,
        "TOP1 红2+": (top1_red2, top1_red2 / test_count),
        "TOP1 红3+": (top1_red3, top1_red3 / test_count),
        "TOP1 蓝命中": (top1_blue, top1_blue / test_count),
        "TOP5 红2+": (top5_red2, top5_red2 / test_count),
        "TOP5 红3+": (top5_red3, top5_red3 / test_count),
        "TOP5 红4+": (top5_red4, top5_red4 / test_count),
        "TOP5 蓝命中": (top5_blue, top5_blue / test_count),
    }

    return {
        "summary": summary,
        "details": pd.DataFrame(details)
    }

# =========================
# 左侧控制台（恢复版）
# =========================
st.sidebar.header("🛰 NemoClaw 云端控制台")

crossfire_n = st.sidebar.slider("交叉火力输出组数", 3, 10, 5)
antigravity_candidates = st.sidebar.slider("反重力候选池", 200, 2000, 1000, step=100)
antigravity_topk = st.sidebar.slider("反重力输出 TopK", 3, 10, 5)
backtest_warmup = st.sidebar.slider("历史回测 Warmup 期数", 10, 20, 15)

st.sidebar.markdown("---")
st.sidebar.subheader("☁ 云端一：系统状态")
st.sidebar.write(f"历史样本数：{len(st.session_state.history_draws)}")
st.sidebar.write(f"数据文件：{DATA_FILE}")
st.sidebar.write(f"输出文件：{OUTPUT_FILE}")

st.sidebar.markdown("---")
st.sidebar.subheader("☁ 云端二：最近预测云")
if st.session_state.antigravity_results:
    for i, x in enumerate(st.session_state.antigravity_results[:3], start=1):
        st.sidebar.write(f"#{i} {format_red(x['red'])} | {x['blue']:02d}")
else:
    st.sidebar.write("暂无预测结果")

st.sidebar.markdown("---")

# =========================
# 左侧按钮区
# =========================
if st.sidebar.button("启动交叉火力推演"):
    log(">>> 启动交叉火力推演...")
    st.session_state.crossfire_results = generate_crossfire_predictions(crossfire_n)
    log(f"✨ 交叉火力推演完成，共输出 {len(st.session_state.crossfire_results)} 组")

if st.sidebar.button("运行反重力选号测试"):
    log(">>> 反重力模块启动...")
    st.session_state.antigravity_results = generate_antigravity_predictions(
        top_k=antigravity_topk,
        n_candidates=antigravity_candidates
    )
    log(f"✨ 反重力候选生成完成，共输出 {len(st.session_state.antigravity_results)} 组")

if st.sidebar.button("运行历史回测"):
    if len(st.session_state.history_draws) < 20:
        st.warning("历史数据不足，建议至少 20 期以上再运行历史回测。")
    else:
        log(">>> 启动历史回测...")
        st.session_state.backtest_results = run_backtest(
            warmup=backtest_warmup,
            top_k=antigravity_topk
        )
        log("✅ 历史回测完成")

if st.sidebar.button("一键全系统总攻"):
    log(">>> 一键全系统总攻启动...")
    st.session_state.crossfire_results = generate_crossfire_predictions(crossfire_n)
    st.session_state.antigravity_results = generate_antigravity_predictions(
        top_k=antigravity_topk,
        n_candidates=antigravity_candidates
    )
    if len(st.session_state.history_draws) >= 20:
        st.session_state.backtest_results = run_backtest(
            warmup=backtest_warmup,
            top_k=antigravity_topk
        )
    export_predictions()
    log("🚀 全系统总攻完成")

# =========================
# 主页面布局
# =========================
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("系统日志")
    if st.session_state.fortress_log_buf:
        for line in st.session_state.fortress_log_buf[-20:]:
            st.write(line)
    else:
        st.write("暂无日志")

    st.subheader("数据状态")
    st.write(f"历史样本数：{len(st.session_state.history_draws)}")
    st.write(f"数据文件：{DATA_FILE}")
    st.write(f"预测输出文件：{OUTPUT_FILE}")

with col2:
    if st.session_state.crossfire_results:
        st.subheader("交叉火力推演结果")
        for i, x in enumerate(st.session_state.crossfire_results, start=1):
            st.write(f"{i:02d}. {format_red(x['red'])} | {x['blue']:02d}")

    if st.session_state.antigravity_results:
        st.subheader("反重力选号结果")
        for i, x in enumerate(st.session_state.antigravity_results, start=1):
            sc = x["score"]
            st.write(
                f"{i:02d}. 红球={x['red']} 蓝球={x['blue']} | "
                f"总分={sc['total_score']:.6f} | "
                f"结构={sc['structure_score']} | "
                f"惩罚={sc['anti_uniformity_penalty']}"
            )

        if export_predictions():
            st.success(f"预测结果已导出：{OUTPUT_FILE}")

    if st.session_state.backtest_results:
        st.subheader("历史回测结果")
        summary = st.session_state.backtest_results["summary"]
        st.write(f"回测期数: {summary['回测期数']}")
        st.write(f"TOP1 红2+ : {summary['TOP1 红2+'][0]} ({summary['TOP1 红2+'][1]:.3f})")
        st.write(f"TOP1 红3+ : {summary['TOP1 红3+'][0]} ({summary['TOP1 红3+'][1]:.3f})")
        st.write(f"TOP1 蓝命中: {summary['TOP1 蓝命中'][0]} ({summary['TOP1 蓝命中'][1]:.3f})")
        st.write(f"TOP5 红2+ : {summary['TOP5 红2+'][0]} ({summary['TOP5 红2+'][1]:.3f})")
        st.write(f"TOP5 红3+ : {summary['TOP5 红3+'][0]} ({summary['TOP5 红3+'][1]:.3f})")
        st.write(f"TOP5 红4+ : {summary['TOP5 红4+'][0]} ({summary['TOP5 红4+'][1]:.3f})")
        st.write(f"TOP5 蓝命中: {summary['TOP5 蓝命中'][0]} ({summary['TOP5 蓝命中'][1]:.3f})")

        st.subheader("回测明细")
        st.dataframe(st.session_state.backtest_results["details"], use_container_width=True)