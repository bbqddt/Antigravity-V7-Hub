import os
import json
import pandas as pd
from datetime import datetime
import glob

DATA_FILE = r"E:\享中\ssq_history_full.csv"
STATE_FILE = r"E:\享中\evolution_state.json"
PRED_FILE = r"E:\享中\latest_predictions_evolved.json"

def apply_reward_punishment():
    print(">>> 启动奖惩结算协议...")
    if not os.path.exists(PRED_FILE) or not os.path.exists(STATE_FILE):
        print("未找到上一期预测文件或状态文件，跳过结算。")
        return

    with open(PRED_FILE, 'r', encoding='utf-8') as f:
        preds = json.load(f)
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    target_period = preds.get("target_period")
    df = pd.read_csv(DATA_FILE)
    actual_row = df[df["period"] == target_period]
    
    if actual_row.empty:
        print(f"数据尚未更新至 {target_period} 期，无法结算。")
        return
        
    if state.get("last_period_evaluated") >= target_period:
        print(f"第 {target_period} 期已结算过，跳过。")
        return

    # 提取真实结果
    actual_reds = set([int(x) for x in str(actual_row.iloc[0]["red"]).split(",")])
    actual_blue = int(actual_row.iloc[0]["blue"])

    print(f"[{target_period} 期] 真实开奖: 红 {sorted(actual_reds)} | 蓝 {actual_blue}")

    # 计分与奖惩
    for group in preds.get("predictions", []):
        strat = group["strategy"]
        pred_reds = set(group["reds"])
        pred_blue = group["blue"]
        
        red_hits = len(pred_reds & actual_reds)
        blue_hit = 1 if pred_blue == actual_blue else 0
        
        reward = (red_hits * 0.1) + (blue_hit * 0.3)
        if red_hits == 0 and not blue_hit:
            reward = -0.1 # 惩罚
            
        if strat in state["strategies"]:
            state["strategies"][strat]["weight"] += reward
            state["strategies"][strat]["total_hits"] += red_hits
            state["strategies"][strat]["usage_count"] += 1
            
            # 保底权重
            state["strategies"][strat]["weight"] = max(0.1, state["strategies"][strat]["weight"])
            print(f"策略 [{strat}] -> 命中红 {red_hits} 蓝 {blue_hit} | 权重变动: {reward:+.2f} -> 当前权重: {state['strategies'][strat]['weight']:.2f}")

    state["last_period_evaluated"] = target_period
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def punish_dead_components():
    print("\n>>> 启动组件监工 (Component Punisher)...")
    # 扫描目录下所有的 py 文件
    py_files = glob.glob(r"E:\享中\*.py")
    active_core_files = [
        "evolved_predictor.py", "auto_pipeline.py", "engine.py", 
        "manual_sync.py", "mcp_harvester.py"
    ]
    
    punished = []
    for filepath in py_files:
        filename = os.path.basename(filepath)
        if filename not in active_core_files:
            # 判断文件最后修改时间，超过 15 天未修改则视为光吃饭不干活
            mtime = os.path.getmtime(filepath)
            days_inactive = (time.time() - mtime) / (24 * 3600)
            if days_inactive > 15:
                punished.append(filename)
                
    if punished:
        print("发现以下低效僵尸组件，执行降权隔离:")
        for p in punished:
            print(f" [隔离] {p} - 连续 {days_inactive:.0f} 天未活跃")
            # 隔离措施：重命名为 .bak 或移动到 archive
            try:
                os.rename(os.path.join(r"E:\享中", p), os.path.join(r"E:\享中", p + ".punished"))
            except:
                pass
    else:
        print("所有核心组件均处于活跃状态。")

if __name__ == "__main__":
    import time
    apply_reward_punishment()
    punish_dead_components()
    print("\n流水线执行完毕。下一步请运行 evolved_predictor.py 生成最新预测。")
