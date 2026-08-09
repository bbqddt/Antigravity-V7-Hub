# logic_alignment.py - Antigravity Hermes Alignment Module
import json
import os
import pandas as pd
from datetime import datetime
from collections import Counter
from pathlib import Path


def run_alignment(csv_path=None):
    """
    碰撞分析：对比预测与真实开奖
    Args:
        csv_path: 可选，指定CSV数据路径
    """
    _ROOT = Path(__file__).resolve().parent

    # 自动搜索数据文件
    if csv_path is None:
        candidates = [
            _ROOT / "data" / "lottery_history.csv",
            _ROOT / "data" / "ssq_history.csv",
            _ROOT / "data" / "ssq_history_full.csv",
        ]
        for c in candidates:
            if c.exists():
                csv_path = str(c)
                break
        if csv_path is None:
            print("❌ 未找到数据文件")
            return

    try:
        df = pd.read_csv(csv_path)
        decision_file = _ROOT / "latest_decision.json"
        if not decision_file.exists():
            decision_file = _ROOT / "latest_decision_enhanced.json"
        with open(decision_file, "r", encoding="utf-8") as f:
            decision = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # 从决策文件中获取目标期号
    target_period = decision.get("target_period", decision.get("period"))
    print(f">>> [Hermes Alignment] Target Period: {target_period}")

    # 提取真实开奖
    actual_reds = set()
    actual_blue = None
    for _, row in df.iterrows():
        period = str(row.get('period', row.get('id', '')))
        if period == str(target_period):
            # 尝试多种列名格式
            for col_prefix in ['r', 'red']:
                vals = []
                for i in range(1, 7):
                    val = row.get(f'{col_prefix}{i}')
                    if val is not None:
                        vals.append(int(val))
                if vals:
                    actual_reds = set(vals)
                    break
            actual_blue = int(row.get('b', row.get('blue', 0)))
            break

    if not actual_reds:
        print(f"❌ 数据库中无 {target_period} 期的开奖记录！")
        return

    print(f">>> [Truth Source] Reds: {sorted(actual_reds)} | Blue: {actual_blue}")

    # 碰撞分析
    results = []
    all_pred_reds = []

    predictions_list = decision.get("predictions", decision.get("audit_report", []))
    for entry in predictions_list:
        if isinstance(entry, dict):
            pred_reds = set(entry.get("reds", entry.get("红球", [])))
            pred_blue = int(entry.get("blue", entry.get("蓝球", 0)))
        else:
            continue

        red_hits = pred_reds & actual_reds
        blue_hit = (pred_blue == actual_blue)

        results.append({
            "预测": sorted(pred_reds),
            "命中红球": sorted(red_hits),
            "命中红球数": len(red_hits),
            "蓝球命中": blue_hit
        })
        all_pred_reds.extend(list(pred_reds))

    # 统计摘要
    avg_hits = sum(r["命中红球数"] for r in results) / len(results) if results else 0
    missed_actual = actual_reds - set(all_pred_reds)

    # 生成报告
    report = f"# Antigravity {target_period}期引力碰撞报告\n"
    report += f"> 时间: {datetime.now().isoformat()}\n\n"
    report += f"## 碰撞结果\n"
    report += "| 预测 | 命中 | 蓝球 |\n|---|---|---|\n"
    for r in results:
        blue_mark = "OK" if r["蓝球命中"] else "MISS"
        report += f"| {r['预测']} | {r['命中红球']} ({r['命中红球数']}) | {blue_mark} |\n"

    report += f"\n## 演进指标\n"
    report += f"- **平均红球命中**: {avg_hits:.2f}\n"
    report += f"- **全盲号码 (物理失焦)**: `{sorted(missed_actual)}`\n"

    with open("evolution_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print(">>> report generated: evolution_report.md")

    # 更新演进 Prompt
    try:
        with open("v7_evolved_prompt.json", "r", encoding="utf-8") as f:
            prompt_data = json.load(f)

        new_lesson = f"## {target_period}期复盘教训 (Hermes 审计结果):\n"
        new_lesson += f"- 真实开奖: {sorted(actual_reds)} + {actual_blue}\n"
        new_lesson += f"- 平均命中: {avg_hits:.2f}/6, 蓝球{'全部命中' if avg_hits > 0 else '全军覆没'}\n"
        new_lesson += f"- 关键盲区: {sorted(missed_actual)} (物理失焦)\n"

        prompt_str = prompt_data["prompt"]
        if "复盘教训" in prompt_str:
            prompt_str = new_lesson + "\n\n" + prompt_str
        else:
            prompt_str = new_lesson + "\n\n" + prompt_str

        prompt_data["prompt"] = prompt_str
        prompt_data["evolution_basis"] = f"{target_period}期复盘: 盲区{sorted(missed_actual)}"
        prompt_data["target_period"] = str(int(target_period) + 1) if target_period.isdigit() else target_period

        with open("v7_evolved_prompt.json", "w", encoding="utf-8") as f:
            json.dump(prompt_data, f, ensure_ascii=False, indent=2)
        print(">>> Prompt evolved: v7_evolved_prompt.json")
    except Exception as e:
        print(f"Prompt update failed: {e}")


if __name__ == "__main__":
    run_alignment()
