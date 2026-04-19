# -*- coding: utf-8 -*-
"""
Antigravity 自我演进核心：回测对比 + 策略进化报告
从 latest_decision.json 提取历史预测，与 ssq_history_full.csv 的真实开奖进行碰撞校对。
"""
import json
import pandas as pd
from datetime import datetime

# ========== 1. 加载物理基石 ==========
DATA_FILE = "ssq_history_full.csv"
PRED_FILE = "latest_decision.json"

df = pd.read_csv(DATA_FILE)
with open(PRED_FILE, "r", encoding="utf-8") as f:
    decision = json.load(f)

target_period = int(decision["target_period"])
print(f">>> [回测引擎] 目标期号: {target_period}")

# ========== 2. 提取真实开奖 ==========
actual_row = df[df["id"] == target_period]
if actual_row.empty:
    print(f"❌ 数据库中无 {target_period} 期的开奖记录！")
    exit(1)

actual_reds = set(actual_row[["r1","r2","r3","r4","r5","r6"]].values[0].tolist())
actual_blue = int(actual_row["b"].values[0])
print(f">>> [真实开奖] 红球: {sorted(actual_reds)} | 蓝球: {actual_blue}")

# ========== 3. 逐组碰撞校对 ==========
results = []
best_hit = 0
best_group = None

for entry in decision["audit_report"]:
    seq = json.loads(entry["序列"])
    pred_reds = set(seq[:6])
    pred_blue = int(seq[6])
    
    # 计算命中
    red_hits = pred_reds & actual_reds
    blue_hit = (pred_blue == actual_blue)
    
    result = {
        "模型": entry["模型"],
        "组别": entry["组别"],
        "预测红球": sorted(pred_reds),
        "预测蓝球": pred_blue,
        "红球命中": sorted(red_hits),
        "红球命中数": len(red_hits),
        "蓝球命中": "✅" if blue_hit else "❌",
        "扰动值": entry["扰动值"],
    }
    results.append(result)
    
    total_score = len(red_hits) + (1 if blue_hit else 0)
    if total_score > best_hit:
        best_hit = total_score
        best_group = result

# ========== 4. 统计分析 ==========
total_groups = len(results)
avg_red_hits = sum(r["红球命中数"] for r in results) / total_groups
blue_hit_count = sum(1 for r in results if r["蓝球命中"] == "✅")
all_predicted_reds = []
for r in results:
    all_predicted_reds.extend(r["预测红球"])

# 频次分析：哪些数字被多个模型同时预测了
from collections import Counter
freq = Counter(all_predicted_reds)
consensus_nums = {k: v for k, v in freq.items() if v >= 3}  # 至少3组都预测了的数
missed_actual = actual_reds - set(all_predicted_reds)  # 真实号码中完全没有任何组预测到的

# ========== 5. 生成演进报告 ==========
report_lines = []
report_lines.append(f"# 🔬 Antigravity 自我演进复盘报告")
report_lines.append(f"> **复盘时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
report_lines.append(f"> **目标期号**: {target_period}")
report_lines.append(f"> **真实开奖**: 红球 `{sorted(actual_reds)}` | 蓝球 `{actual_blue}`")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("## 📊 逐组校对结果")
report_lines.append("")
report_lines.append("| 模型 | 组别 | 预测红球 | 预测蓝球 | 红球命中 | 命中数 | 蓝球 |")
report_lines.append("|------|------|----------|----------|----------|--------|------|")
for r in results:
    report_lines.append(
        f"| {r['模型']} | {r['组别']} | {r['预测红球']} | {r['预测蓝球']} | {r['红球命中']} | **{r['红球命中数']}** | {r['蓝球命中']} |"
    )

report_lines.append("")
report_lines.append("## 📈 统计摘要")
report_lines.append(f"- **总预测组数**: {total_groups}")
report_lines.append(f"- **红球平均命中**: {avg_red_hits:.1f} / 6")
report_lines.append(f"- **蓝球命中组数**: {blue_hit_count} / {total_groups}")
report_lines.append(f"- **最佳表现组**: {best_group['模型']} {best_group['组别']} (红{best_group['红球命中数']}+蓝{best_group['蓝球命中']})")
report_lines.append("")

report_lines.append("## 🧠 模式洞察与演进方向")
report_lines.append("")
report_lines.append(f"### 共识号码 (≥3组预测)")
if consensus_nums:
    for num, count in sorted(consensus_nums.items(), key=lambda x: -x[1]):
        hit_mark = "✅ 命中" if num in actual_reds else "❌ 未中"
        report_lines.append(f"- **{num}** → 被 {count} 组预测 → {hit_mark}")
else:
    report_lines.append("- 无明显共识，模型间离散度过高")

report_lines.append("")
report_lines.append(f"### 盲区号码 (真实开奖但无任何组预测)")
if missed_actual:
    report_lines.append(f"- **{sorted(missed_actual)}** → 所有模型全部漏判！需要强化对这些区间的关注度！")
else:
    report_lines.append("- 无盲区，所有真实号码至少被1组覆盖 ✅")

# 演进建议
report_lines.append("")
report_lines.append("## 🚀 自我演进策略建议")
report_lines.append("")

if avg_red_hits < 1.5:
    report_lines.append("> [!CAUTION]")
    report_lines.append("> 红球命中率极低（平均 < 1.5），当前模型的统计基石或 Prompt 工程存在严重偏差。")
    report_lines.append("> **建议**: 增加输入数据窗口（从15期扩展到30期），引入频率热力图与遗漏值分析。")
elif avg_red_hits < 2.5:
    report_lines.append("> [!WARNING]")
    report_lines.append("> 红球命中率一般（平均 < 2.5），模型具备一定趋势捕捉能力但精度不足。")
    report_lines.append("> **建议**: 引入连号/同尾检测模块，增加区间均衡约束。")
else:
    report_lines.append("> [!TIP]")
    report_lines.append("> 红球命中率较高（平均 ≥ 2.5），模型趋势感知良好。")
    report_lines.append("> **建议**: 维持当前策略，微调蓝球区间收敛算法。")

if missed_actual:
    report_lines.append("")
    blind_nums = sorted(missed_actual)
    report_lines.append(f"**关键改进点**: 号码 `{blind_nums}` 完全盲区。下次推演需在 Prompt 中增加对'冷号回补'逻辑的强调。")

report_lines.append("")
report_lines.append("---")
report_lines.append(f'*"在每一次失败中校准准星，这就是反重力的意义。" —— The Architect*')

report = "\n".join(report_lines)

# 保存
with open("evolution_report.md", "w", encoding="utf-8") as f:
    f.write(report)

# 控制台输出关键结论
print("\n" + "="*60)
print(f"  复盘完成: {target_period} 期")
print(f"  真实开奖: 红 {sorted(actual_reds)} | 蓝 {actual_blue}")
print(f"  红球平均命中: {avg_red_hits:.1f} / 6")
print(f"  蓝球命中组数: {blue_hit_count} / {total_groups}")
print(f"  最佳组: {best_group['模型']} {best_group['组别']} → 红{best_group['红球命中数']}+蓝{'中' if best_group['蓝球命中']=='✅' else '未中'}")
if missed_actual:
    print(f"  全盲号码: {sorted(missed_actual)}")
print("="*60)
print(f">>> 完整报告已生成: evolution_report.md")
