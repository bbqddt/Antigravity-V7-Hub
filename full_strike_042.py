# -*- coding: utf-8 -*-
"""
Antigravity V7.1 全弹道打击脚本
三连击闭环: 入库041 → 回测校对 → PID+奇点引擎 → 042期推演
融合全部武器: PID控制器 + AntiGravityCoreEngine + autoresearch_core蓝球引力场
"""
import pandas as pd
import json
import math
import random
from datetime import datetime
from collections import Counter

# ===================== 第一击: 入库 041 期真实数据 =====================
print("=" * 70)
print("  ⚡ 第一击: MCP 抓取 041 期结果 → 注入物理基石")
print("=" * 70)

DATA_FILE = "ssq_history_full.csv"
df = pd.read_csv(DATA_FILE)

# 041期真实开奖: 02,08,10,17,19,24 + 13 (2026-04-14)
actual_041 = {"id": 2026041, "r1": 2, "r2": 8, "r3": 10, "r4": 17, "r5": 19, "r6": 24, "b": 13, "date": "2026-04-14"}
actual_041_reds = {2, 8, 10, 17, 19, 24}
actual_041_blue = 13

if 2026041 not in df["id"].values:
    df = pd.concat([df, pd.DataFrame([actual_041])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    print(f"  ✅ 041期 [{sorted(actual_041_reds)}] + {actual_041_blue} 已注入 (共 {len(df)} 期)")
else:
    print(f"  ✅ 041期已存在 (共 {len(df)} 期)")

# ===================== 第二击: 回测碰撞校对 =====================
print("\n" + "=" * 70)
print("  ⚡ 第二击: 回测 041 期预测 vs 真实开奖")
print("=" * 70)

with open("latest_decision.json", "r", encoding="utf-8") as f:
    old_decision = json.load(f)

print(f"  真实开奖: 红 {sorted(actual_041_reds)} | 蓝 {actual_041_blue}")
print(f"  预测引擎: {old_decision.get('engine_version', 'unknown')}")
print()

best_score = 0
best_group = ""
hit_records = []

for pred in old_decision.get("predictions", []):
    pred_reds = set(pred["红球"])
    pred_blue = pred["蓝球"]
    red_hits = pred_reds & actual_041_reds
    blue_hit = pred_blue == actual_041_blue
    score = len(red_hits) + (1 if blue_hit else 0)
    
    mark_r = f"红{len(red_hits)}"
    mark_b = "蓝✅" if blue_hit else "蓝❌"
    print(f"  {pred['组别']} [{pred['策略']}]: {sorted(pred_reds)} + {pred_blue} → 命中 {sorted(red_hits)} {mark_r} {mark_b}")
    
    hit_records.append({"group": pred["组别"], "red_hits": len(red_hits), "blue_hit": blue_hit, "score": score})
    if score > best_score:
        best_score = score
        best_group = pred["组别"]

avg_red = sum(h["red_hits"] for h in hit_records) / len(hit_records)
blue_hit_count = sum(1 for h in hit_records if h["blue_hit"])

print(f"\n  ┌─ 统计摘要 ─────────────────────────┐")
print(f"  │ 红球平均命中: {avg_red:.1f} / 6              │")
print(f"  │ 蓝球命中组数: {blue_hit_count} / {len(hit_records)}               │")
print(f"  │ 最佳表现组:   {best_group} (总分 {best_score})        │")
print(f"  └────────────────────────────────────┘")

# 从回测中学习: 计算 PID 误差信号
target_accuracy = 3.0  # 目标: 平均命中 3 个红球
pid_error = target_accuracy - avg_red  # 正值 = 需要加强

# ===================== 第三击: 全武装推演 042 期 =====================
print("\n" + "=" * 70)
print("  ⚡ 第三击: 全武装 042 期推演 (PID + 奇点引擎 + 蓝球引力场)")
print("=" * 70)

# --- 武器1: 统计特征提取 (V7.0 进化版) ---
latest_30 = df.tail(30)
latest_10 = df.tail(10)

all_reds_30 = []
all_blues_30 = []
for _, row in latest_30.iterrows():
    reds = [int(row[f"r{i}"]) for i in range(1, 7)]
    all_reds_30.extend(reds)
    all_blues_30.append(int(row["b"]))

red_freq = Counter(all_reds_30)
hot_reds = [k for k, v in red_freq.most_common(12)]
warm_reds = [k for k, v in red_freq.most_common(20) if k not in hot_reds]
cold_reds = [i for i in range(1, 34) if red_freq.get(i, 0) <= 1]

blue_freq = Counter(all_blues_30)
hot_blues = [k for k, v in blue_freq.most_common(5)]
cold_blues = [i for i in range(1, 17) if blue_freq.get(i, 0) <= 1]

# 遗漏值分析: 哪些号码已经连续多期没出现
last_5_reds = set()
for _, row in df.tail(5).iterrows():
    for i in range(1, 7):
        last_5_reds.add(int(row[f"r{i}"]))
missing_from_recent = [i for i in range(1, 34) if i not in last_5_reds]

print(f"  热号(30期Top12): {hot_reds}")
print(f"  冷号(30期≤1次): {cold_reds}")
print(f"  近5期遗漏号码:   {missing_from_recent[:10]}...")
print(f"  热蓝: {hot_blues} | 冷蓝: {cold_blues}")

# --- 武器2: PID 控制器 (来自 antigravity.py) ---
class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.prev_error, self.integral = 0.0, 0.0
    def compute(self, target, current_val):
        error = target - current_val
        self.integral += error
        derivative = error - self.prev_error
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        self.prev_error = error
        return output

pid = PIDController(kp=0.618, ki=0.1, kd=0.2)
pid_adjustment = pid.compute(target_accuracy, avg_red)
print(f"\n  [PID] 回测误差信号: {pid_error:+.1f} | PID补偿输出: {pid_adjustment:+.2f}")

# PID 指导: 正补偿 = 需要更激进(扩大热号权重), 负补偿 = 需要收敛
hot_weight = max(3, min(6, int(4 + pid_adjustment)))  # 热号选取数量
cold_weight = 6 - hot_weight
print(f"  [PID] 策略调整: 热号取 {hot_weight} 个, 冷/温号取 {cold_weight} 个")

# --- 武器3: AntiGravity Core Engine 奇点计算 (来自 test_proxy.py) ---
def search_singularity(data_matrix, dimensions=6):
    """多模型矩阵的高维塌陷奇点搜索"""
    target_eq = 8.57
    final = []
    for dim in range(dimensions):
        preds = [row[dim] for row in data_matrix if len(row) > dim]
        if not preds: 
            final.append(17.0)
            continue
        mean_p = sum(preds) / len(preds)
        variance = sum((p - mean_p)**2 for p in preds) / len(preds)
        force = math.sqrt(variance)
        # 简化PID收敛到目标均衡
        error = target_eq - mean_p
        eq_point = mean_p + 0.618 * error - force * 0.1
        # 排斥场微调
        repulsion = 0.0
        for i in range(len(preds)):
            for j in range(i+1, len(preds)):
                dist = abs(preds[i] - preds[j])
                repulsion += 1.0 / max(dist**2, 0.01)
        damped = math.log1p(repulsion) * 0.005
        final.append(round(eq_point + damped, 2))
    return final

# 构建"虚拟多模型矩阵": 将最近5期的红球数据视为5个模型的输出
model_matrix = []
for _, row in df.tail(5).iterrows():
    model_matrix.append([float(row[f"r{i}"]) for i in range(1, 7)])

singularity = search_singularity(model_matrix)
print(f"  [奇点引擎] 六维塌陷奇点: {singularity}")
# 将奇点四舍五入为最近的合法号码
singularity_nums = [max(1, min(33, round(s))) for s in singularity]
print(f"  [奇点引擎] 映射号码: {sorted(set(singularity_nums))}")

# --- 武器4: 蓝球引力场 (来自 autoresearch_core.py) ---
global_z = 8.5676  # 蓝球历史平衡点
recent_blues = [int(df.iloc[i]["b"]) for i in range(-5, 0)]
last_blue = recent_blues[-1]
blue_gap = last_blue - global_z

# 蓝球坍缩路径分析
blue_trend = []
for i in range(len(recent_blues) - 1):
    blue_trend.append(recent_blues[i+1] - recent_blues[i])
blue_momentum = sum(blue_trend) / len(blue_trend) if blue_trend else 0

# 引力场预测: 向平衡点回归 + 动量惯性
predicted_blue_raw = last_blue - blue_gap * 0.4 + blue_momentum * 0.3
predicted_blue = max(1, min(16, round(predicted_blue_raw)))

print(f"  [蓝球引力场] 近5期蓝球路径: {recent_blues}")
print(f"  [蓝球引力场] 偏离重心: {blue_gap:+.2f} | 动量: {blue_momentum:+.1f}")
print(f"  [蓝球引力场] 预测蓝球核心: {predicted_blue}")

# ===================== 生成 042 期 5 组预测 =====================
print(f"\n{'─'*70}")
print(f"  🎯 042 期最终预测矩阵 (2026-04-16)")
print(f"{'─'*70}")

random.seed(int(datetime.now().timestamp()))

def gen_group(hot, warm, cold, missing, n_hot, singularity_nums, strategy_name):
    """融合所有武器生成单组预测"""
    pool = list(range(1, 34))
    selected = []
    
    if strategy_name == "singularity":
        # 奇点引擎主导
        base = [x for x in set(singularity_nums) if 1 <= x <= 33]
        selected = random.sample(base, min(4, len(base)))
        fill = [x for x in hot + warm if x not in selected]
        while len(selected) < 6 and fill:
            selected.append(fill.pop(0))
    elif strategy_name == "cold_revenge":
        # 冷号反击 + 遗漏回补
        candidates = list(set(cold + missing[:8]))
        if len(candidates) >= 4:
            selected = random.sample(candidates, 4)
        else:
            selected = candidates[:]
        fill = [x for x in hot if x not in selected]
        while len(selected) < 6:
            selected.append(fill.pop(random.randint(0, max(0, len(fill)-1))))
    else:
        # 热号骨架
        h_pool = [x for x in hot if x not in selected]
        selected = random.sample(h_pool, min(n_hot, len(h_pool)))
        # 温/冷号补位
        supplement = [x for x in (warm + cold + missing[:5]) if x not in selected]
        random.shuffle(supplement)
        while len(selected) < 6 and supplement:
            selected.append(supplement.pop(0))
    
    # 填充到6个
    while len(selected) < 6:
        extra = random.choice([x for x in pool if x not in selected])
        selected.append(extra)
    
    selected = sorted(set(selected))[:6]
    # 如果去重后不足6个
    while len(selected) < 6:
        selected.append(random.choice([x for x in pool if x not in selected]))
        selected = sorted(set(selected))[:6]
    
    # 三区检查
    has_z1 = any(1 <= x <= 11 for x in selected)
    has_z2 = any(12 <= x <= 22 for x in selected)
    has_z3 = any(23 <= x <= 33 for x in selected)
    if not has_z1:
        selected[0] = random.choice(range(1, 12))
    if not has_z2:
        selected[2] = random.choice(range(12, 23))
    if not has_z3:
        selected[5] = random.choice(range(23, 34))
    selected = sorted(set(selected))[:6]
    while len(selected) < 6:
        selected.append(random.choice([x for x in pool if x not in selected]))
        selected = sorted(set(selected))
    
    return selected[:6]

# 蓝球池: 引力场核心 + 热蓝 + 1个冷蓝
blue_candidates = list(set([predicted_blue] + hot_blues[:3] + cold_blues[:1]))

strategies = [
    ("PID热号骨架+冷号回补", "hot", hot_weight),
    ("奇点引擎主导", "singularity", 3),
    ("热冷均衡+遗漏回补", "hot", 3),
    ("冷号反击+引力场", "cold_revenge", 2),
    ("自由覆盖最大离散", "hot", 2),
]

predictions_042 = []
for i, (desc, strat, nh) in enumerate(strategies, 1):
    reds = gen_group(hot_reds, warm_reds, cold_reds, missing_from_recent, nh, singularity_nums, strat)
    
    # 蓝球选择
    if strat == "cold_revenge":
        blue = random.choice(cold_blues) if cold_blues else predicted_blue
    elif strat == "singularity":
        blue = predicted_blue
    else:
        blue = random.choice(blue_candidates)
    
    predictions_042.append({"组别": f"第{i}组", "策略": desc, "红球": reds, "蓝球": blue})
    print(f"  组{i} [{desc}]: {reds} + {blue:02d}")

# ===================== 保存战果 =====================
decision = {
    "target_period": "2026042",
    "engine_version": "V7.1-FullStrike",
    "status": "PID+SINGULARITY+GRAVFIELD",
    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "evolution_basis": f"041期回测: 红{avg_red:.1f}/6, 蓝{blue_hit_count}/{len(hit_records)}, PID补偿={pid_adjustment:+.2f}",
    "backtest_041": {
        "actual_reds": sorted(actual_041_reds),
        "actual_blue": actual_041_blue,
        "avg_red_hits": round(avg_red, 2),
        "blue_hits": blue_hit_count,
        "best_group": best_group,
    },
    "predictions": predictions_042,
}

with open("latest_decision.json", "w", encoding="utf-8") as f:
    json.dump(decision, f, ensure_ascii=False, indent=2)

# 同时生成 evolution_report
report = f"""# 🔬 Antigravity V7.1 演进闭环报告 (041→042)
> **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> **引擎**: V7.1-FullStrike (PID + 奇点引擎 + 蓝球引力场)

## 回测: 041期
- **真实开奖**: 红 `{sorted(actual_041_reds)}` | 蓝 `{actual_041_blue}`
- **红球平均命中**: {avg_red:.1f} / 6
- **蓝球命中**: {blue_hit_count} / {len(hit_records)}
- **PID 补偿信号**: {pid_adjustment:+.2f} (热号权重→{hot_weight})

## 042期推演参数
- 热号: `{hot_reds}`
- 冷号: `{cold_reds}`
- 奇点坐标: `{singularity}`→`{sorted(set(singularity_nums))}`
- 蓝球引力场: 路径 {recent_blues} → 预测核心 `{predicted_blue}`

## 042期预测矩阵
| 组 | 策略 | 红球 | 蓝球 |
|----|------|------|------|
"""
for p in predictions_042:
    report += f"| {p['组别']} | {p['策略']} | {p['红球']} | {p['蓝球']:02d} |\n"
report += f"\n---\n*演进闭环: 回测→PID→奇点→引力场→推演→存档 ✅*\n"

with open("evolution_report.md", "w", encoding="utf-8") as f:
    f.write(report)

print(f"\n{'='*70}")
print(f"  ✅ 042 期全弹道打击完成!")
print(f"  📄 latest_decision.json 已更新")
print(f"  📄 evolution_report.md 已更新")
print(f"  📄 ssq_history_full.csv 已注入 041 期 (共 {len(df)} 期)")
print(f"{'='*70}")
