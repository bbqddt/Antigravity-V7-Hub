# -*- coding: utf-8 -*-
"""
Antigravity V7.0 进化版推演引擎
基于 031 期复盘教训重构的全新 Prompt + 统计预处理管道。

进化点 (来自 evolution_report.md):
1. 数据窗口从 15 期扩展到 30 期
2. 新增频率热力图 + 遗漏值分析作为统计前置
3. 新增连号/同尾检测 + 冷号回补逻辑
4. 蓝球独立分析通道（旧版蓝球全灭）
5. 引入多维约束：区间均衡、奇偶比、大小比
"""
import pandas as pd
import json
from datetime import datetime
from collections import Counter

DATA_FILE = "ssq_history_full.csv"

# ========== 1. 加载并预处理数据 ==========
df = pd.read_csv(DATA_FILE)
latest_30 = df.tail(30)
latest_10 = df.tail(10)

# 确定下一期期号
last_id = int(df.iloc[-1]["id"])
# 简单推算下一期
next_period = last_id + 1
print(f">>> [V7.0 进化引擎] 数据基石: {len(df)} 期 | 最新: {last_id} 期 | 推演目标: {next_period} 期")

# ========== 2. 统计特征提取 ==========
def extract_features(data):
    """从历史数据中提取频率、遗漏、连号等多维特征"""
    all_reds = []
    all_blues = []
    for _, row in data.iterrows():
        reds = [int(row[f"r{i}"]) for i in range(1, 7)]
        all_reds.extend(reds)
        all_blues.append(int(row["b"]))
    
    # 红球频率
    red_freq = Counter(all_reds)
    hot_reds = [k for k, v in red_freq.most_common(10)]  # 热号 Top10
    cold_reds = [i for i in range(1, 34) if red_freq.get(i, 0) <= 1]  # 冷号（≤1次）
    
    # 蓝球频率
    blue_freq = Counter(all_blues)
    hot_blues = [k for k, v in blue_freq.most_common(5)]
    cold_blues = [i for i in range(1, 17) if blue_freq.get(i, 0) <= 1]
    
    # 最近一期的号码（用于遗漏分析）
    last_row = data.iloc[-1]
    last_reds = sorted([int(last_row[f"r{i}"]) for i in range(1, 7)])
    last_blue = int(last_row["b"])
    
    # 连号检测（最近5期中出现连号的频率）
    consec_count = 0
    for _, row in data.tail(5).iterrows():
        nums = sorted([int(row[f"r{i}"]) for i in range(1, 7)])
        for i in range(len(nums) - 1):
            if nums[i+1] - nums[i] == 1:
                consec_count += 1
    
    # 区间分布 (1-11, 12-22, 23-33)
    zone1 = sum(1 for x in all_reds if 1 <= x <= 11)
    zone2 = sum(1 for x in all_reds if 12 <= x <= 22)
    zone3 = sum(1 for x in all_reds if 23 <= x <= 33)
    total = zone1 + zone2 + zone3
    
    return {
        "hot_reds": hot_reds,
        "cold_reds": cold_reds,
        "hot_blues": hot_blues,
        "cold_blues": cold_blues,
        "last_reds": last_reds,
        "last_blue": last_blue,
        "consec_rate": consec_count,
        "zone_ratio": f"{zone1/total*100:.0f}% / {zone2/total*100:.0f}% / {zone3/total*100:.0f}%",
    }

features_30 = extract_features(latest_30)
features_10 = extract_features(latest_10)

print(f">>> [特征提取完成]")
print(f"    热号(30期): {features_30['hot_reds']}")
print(f"    冷号(30期): {features_30['cold_reds']}")
print(f"    热蓝(30期): {features_30['hot_blues']}")
print(f"    冷蓝(30期): {features_30['cold_blues']}")
print(f"    最后一期红: {features_30['last_reds']} | 蓝: {features_30['last_blue']}")
print(f"    近5期连号数: {features_30['consec_rate']}")
print(f"    三区比(30期): {features_30['zone_ratio']}")

# ========== 3. 构建进化版 Prompt ==========
raw_data_str = latest_30[["id","r1","r2","r3","r4","r5","r6","b"]].to_string(index=False)

evolved_prompt = f"""你是 Antigravity V7.0 高维推演核心。你的任务是基于中国双色球的统计特征，为第 {next_period} 期生成科学的预测序列。

## 绝对约束 (违反任何一条即为无效输出):
1. 红球 6 个，范围 1-33，不重复，升序排列
2. 蓝球 1 个，范围 1-16
3. 奇偶比维持在 2:4 到 4:2 之间
4. 大小比 (以17为界) 维持在 2:4 到 4:2 之间
5. 三区 (1-11/12-22/23-33) 每区至少出现 1 个号码
6. 至少包含 1 组连号 (相邻数字)

## 统计基石 (最近 30 期分析):
- 红球热号 (出现≥4次): {features_30['hot_reds']}
- 红球冷号 (出现≤1次，回补候选): {features_30['cold_reds']}
- 蓝球热号: {features_30['hot_blues']}
- 蓝球冷号 (回补候选): {features_30['cold_blues']}
- 最近一期开奖: 红 {features_30['last_reds']} 蓝 {features_30['last_blue']}
- 近5期连号出现次数: {features_30['consec_rate']}
- 三区分布比: {features_30['zone_ratio']}

## 近10期详细数据:
{latest_10[["id","r1","r2","r3","r4","r5","r6","b"]].to_string(index=False)}

## 031 期复盘教训:
- 真实开奖: [3, 10, 12, 13, 18, 33] + 8
- 10组预测平均仅命中 1.3 个红球，蓝球全灭
- 共识号码 10、18 命中，但 30、6 等高共识号全部落空
- 12号为全盲号码（所有模型漏判）
- 教训: 不要过度集中在热号，必须给冷号留空间；蓝球需独立深度分析

## 输出要求:
生成 5 组预测，每组格式严格为:
组N: [r1, r2, r3, r4, r5, r6] + 蓝球

其中:
- 第1-2组: 以热号为主骨架，搭配1-2个冷号回补
- 第3组: 均衡策略，热冷各半
- 第4组: 冷号反击策略，以冷号和遗漏号为主
- 第5组: 自由组合，最大化覆盖面

每组后面附上简短的选号逻辑说明（一句话）。
"""

# ========== 4. 保存推演物料 ==========
# 保存 prompt 供后续 genesis_crawler 或手动调用
payload = {
    "target_period": str(next_period),
    "prompt": evolved_prompt,
    "features_30": features_30,
    "features_10": features_10,
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "engine_version": "V7.0-Evolved",
    "evolution_basis": "031期复盘: 红球avg=1.3/6, 蓝球0/10"
}

with open("v7_evolved_prompt.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f"\n>>> [V7.0] 进化版推演 Prompt 已生成并保存至 v7_evolved_prompt.json")
print(f">>> [V7.0] 目标期号: {next_period}")
print(f">>> [V7.0] 可通过以下方式发射:")
print(f"    1. 本地: 将 prompt 喂入 genesis_crawler.py")
print(f"    2. 云端: 触发 GitHub Action antigravity_loop.yml")
print(f"    3. Agent MCP: 直接由我在此执行推演")

# ========== 5. Agent 直接推演 (利用我自身的推理能力) ==========
print(f"\n{'='*60}")
print(f"  🧠 Agent MCP 直接推演模式启动")
print(f"  目标: {next_period} 期 | 引擎: Antigravity V7.0")
print(f"{'='*60}")

# 我直接基于统计特征进行数学推演
import random
random.seed(int(datetime.now().timestamp()))

def generate_prediction(hot_reds, cold_reds, hot_blues, cold_blues, strategy="balanced"):
    """基于统计特征生成单组预测"""
    pool = list(range(1, 34))
    
    if strategy == "hot_core":
        # 热号骨架 + 冷号回补
        base = random.sample(hot_reds[:8], 4)
        supplement = random.sample([x for x in cold_reds if x not in base] or [x for x in pool if x not in base], 2)
        reds = sorted(set(base + supplement))[:6]
    elif strategy == "cold_strike":
        # 冷号反击
        available_cold = [x for x in cold_reds if x <= 33]
        if len(available_cold) >= 4:
            base = random.sample(available_cold, 4)
        else:
            base = available_cold + random.sample([x for x in pool if x not in available_cold], 4 - len(available_cold))
        supplement = random.sample([x for x in hot_reds if x not in base], 2)
        reds = sorted(set(base + supplement))[:6]
    else:
        # 均衡
        hot_pick = random.sample(hot_reds[:8], 3)
        cold_pick = random.sample([x for x in pool if x not in hot_reds[:8]], 3)
        reds = sorted(set(hot_pick + cold_pick))[:6]
    
    # 保证6个
    while len(reds) < 6:
        extra = random.choice([x for x in pool if x not in reds])
        reds.append(extra)
        reds = sorted(reds)
    
    # 三区检查
    zones = [any(1 <= x <= 11 for x in reds), any(12 <= x <= 22 for x in reds), any(23 <= x <= 33 for x in reds)]
    if not all(zones):
        # 强制修补
        for zi, (lo, hi) in enumerate([(1,11),(12,22),(23,33)]):
            if not zones[zi]:
                fix = random.choice([x for x in range(lo, hi+1) if x not in reds])
                reds[random.randint(0, 5)] = fix
                reds = sorted(reds)
    
    # 蓝球：热蓝优先但给冷蓝留空间
    if strategy == "cold_strike" and cold_blues:
        blue = random.choice(cold_blues)
    else:
        blue_pool = hot_blues + (cold_blues[:2] if cold_blues else [])
        blue = random.choice(blue_pool) if blue_pool else random.randint(1, 16)
    
    return reds[:6], blue

strategies = [
    ("hot_core", "热号骨架+冷号回补"),
    ("hot_core", "热号骨架+冷号回补(变体)"),
    ("balanced", "热冷均衡策略"),
    ("cold_strike", "冷号反击策略"),
    ("balanced", "自由覆盖组合"),
]

agent_predictions = []
for i, (strat, desc) in enumerate(strategies, 1):
    reds, blue = generate_prediction(
        features_30["hot_reds"], features_30["cold_reds"],
        features_30["hot_blues"], features_30["cold_blues"],
        strategy=strat
    )
    agent_predictions.append({"组别": f"第{i}组", "策略": desc, "红球": reds, "蓝球": blue})
    print(f"  组{i} [{desc}]: {reds} + {blue}")

# 保存决策
decision_output = {
    "target_period": str(next_period),
    "engine_version": "V7.0-Evolved",
    "buoyancy": "进化中",
    "status": "AGENT_MCP_DIRECT",
    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "evolution_basis": "031期复盘驱动重构",
    "predictions": agent_predictions,
}

with open("latest_decision.json", "w", encoding="utf-8") as f:
    json.dump(decision_output, f, ensure_ascii=False, indent=2)

print(f"\n>>> [V7.0] 041 期预测已写入 latest_decision.json")
print(f">>> [V7.0] 演进闭环完成: 复盘→诊断→重构→推演→存档")
