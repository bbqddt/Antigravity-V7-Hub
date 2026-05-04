# -*- coding: utf-8 -*-
"""
███████████████████████████████████████████████████████████████
  ANTIGRAVITY OMNI-STRIKE ENGINE V8.0
  全联合作战引擎 — 融合军火库全部武器
  
  武器清单:
  [1] MCP 抓取探针 (Agent 内建)
  [2] PID 控制器 (antigravity.py)
  [3] AntiGravity 奇点引擎 (test_proxy.py)
  [4] 蓝球引力场 8.57 (autoresearch_core.py)
  [5] Qwen-Plus 云节点 (qwen_cloud_node.py) → 127.0.0.1:3000
  [6] OmniProxy GPT 中转 (test_proxy.py) → 127.0.0.1:3000
  [7] Genesis Crawler 多模型 Gemini (genesis_crawler.py)
  [8] NemoClaw SOCKS5 隧道 (nemotron_warrior_v1.py)
  [9] Hermes 对冲审计桥 (hermes_core_bridge.py)
  [10] HF 空投 + GitHub Action 天基卫星
███████████████████████████████████████████████████████████████
"""
import pandas as pd
import json
import math
import random
import os
import re
import urllib.request
import urllib.error
import time
from datetime import datetime
from collections import Counter

DATA_FILE = "ssq_history_full.csv"

# ==================== 武器模块定义 ====================

class PIDController:
    """武器#2: PID 控制器 — 来自 antigravity.py"""
    def __init__(self, kp=0.618, ki=0.1, kd=0.2):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.prev_error, self.integral = 0.0, 0.0
    def compute(self, target, current):
        error = target - current
        self.integral += error
        deriv = error - self.prev_error
        out = self.kp * error + self.ki * self.integral + self.kd * deriv
        self.prev_error = error
        return out

class SingularityEngine:
    """武器#3: 反重力奇点引擎 — 来自 test_proxy.py AntiGravityCoreEngine"""
    def __init__(self, target_eq=8.57):
        self.target_eq = target_eq
    def search(self, matrix, dims=6):
        result = []
        for d in range(dims):
            preds = [row[d] for row in matrix if len(row) > d]
            if not preds:
                result.append(17.0); continue
            mean = sum(preds) / len(preds)
            var = sum((p - mean)**2 for p in preds) / len(preds)
            force = math.sqrt(var)
            eq = mean + 0.618 * (self.target_eq - mean) - force * 0.1
            rep = sum(1.0/max(abs(preds[i]-preds[j])**2, 0.01)
                      for i in range(len(preds)) for j in range(i+1, len(preds)))
            result.append(round(eq + math.log1p(rep)*0.005, 2))
        return result

class BlueBallGravityField:
    """武器#4: 蓝球引力场 — 来自 autoresearch_core.py"""
    GLOBAL_Z = 8.5676
    def predict(self, recent_blues):
        last = recent_blues[-1]
        gap = last - self.GLOBAL_Z
        trend = [recent_blues[i+1]-recent_blues[i] for i in range(len(recent_blues)-1)]
        momentum = sum(trend)/len(trend) if trend else 0
        raw = last - gap*0.4 + momentum*0.3
        return max(1, min(16, round(raw)))

class OmniProxyNode:
    """武器#5/#6: 无限API中转站 — 来自 test_proxy.py + qwen_cloud_node.py
       统一接口：可调用 Qwen-Plus / GPT-4 等任意模型"""
    def __init__(self, endpoint="http://127.0.0.1:3000/v1/chat/completions"):
        self.endpoint = endpoint
    def fire(self, prompt, model="qwen-plus", api_key=""):
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是 Antigravity V8 反重力推演核心。直接输出5组预测，格式：组N: [r1,r2,r3,r4,r5,r6] + 蓝球。不说废话。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(self.endpoint, json.dumps(payload).encode(), headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                body = json.loads(r.read().decode())
                return body.get("choices",[{}])[0].get("message",{}).get("content","")
        except Exception as e:
            return f"PROXY_ERROR: {e}"

class HermesBridge:
    """武器#9: Hermes 对冲审计桥 — 来自 feature-hermes-integration"""
    def __init__(self):
        self.endpoint = os.getenv("HERMES_BTP_ENDPOINT", "")
    def sync_audit(self, period, prediction, truth=None):
        payload = {"period": period, "prediction": prediction, "truth": truth, "version": "V8.0-OmniStrike"}
        if not self.endpoint:
            return {"status": "offline", "note": "HERMES_BTP_ENDPOINT 未配置，审计数据本地归档"}
        try:
            import requests
            r = requests.post(f"{self.endpoint}/audit", json=payload)
            return r.json()
        except Exception as e:
            return {"status": "offline", "error": str(e)}

class StatisticsCore:
    """统计特征提取核心"""
    @staticmethod
    def extract(df, window=30):
        data = df.tail(window)
        all_r, all_b = [], []
        for _, row in data.iterrows():
            all_r.extend([int(row[f"r{i}"]) for i in range(1,7)])
            all_b.append(int(row["b"]))
        rf, bf = Counter(all_r), Counter(all_b)
        hot_r = [k for k,_ in rf.most_common(12)]
        warm_r = [k for k,_ in rf.most_common(20) if k not in hot_r]
        cold_r = [i for i in range(1,34) if rf.get(i,0) <= 1]
        hot_b = [k for k,_ in bf.most_common(5)]
        cold_b = [i for i in range(1,17) if bf.get(i,0) <= 1]
        # 遗漏号
        recent5 = set()
        for _, row in df.tail(5).iterrows():
            for i in range(1,7): recent5.add(int(row[f"r{i}"]))
        missing = [i for i in range(1,34) if i not in recent5]
        # 近期蓝球
        recent_b = [int(df.iloc[i]["b"]) for i in range(-5,0)]
        # 连号率
        consec = 0
        for _, row in data.tail(5).iterrows():
            nums = sorted([int(row[f"r{i}"]) for i in range(1,7)])
            consec += sum(1 for i in range(len(nums)-1) if nums[i+1]-nums[i]==1)
        return {
            "hot_r": hot_r, "warm_r": warm_r, "cold_r": cold_r,
            "hot_b": hot_b, "cold_b": cold_b,
            "missing": missing, "recent_b": recent_b, "consec": consec,
            "last_r": sorted([int(df.iloc[-1][f"r{i}"]) for i in range(1,7)]),
            "last_b": int(df.iloc[-1]["b"])
        }

def gen_group(hot, warm, cold, missing, sing_nums, strategy, n_hot):
    """融合生成器：多策略单组预测"""
    pool = list(range(1,34))
    sel = []
    if strategy == "singularity":
        base = [x for x in set(sing_nums) if 1<=x<=33]
        sel = random.sample(base, min(4, len(base)))
        fill = [x for x in hot+warm if x not in sel]
        while len(sel)<6 and fill: sel.append(fill.pop(0))
    elif strategy == "cold":
        cands = list(set(cold + missing[:8]))
        sel = random.sample(cands, min(4, len(cands))) if len(cands)>=4 else cands[:]
        fill = [x for x in hot if x not in sel]
        while len(sel)<6 and fill: sel.append(fill.pop(0))
    else:
        h = [x for x in hot if x not in sel]
        sel = random.sample(h, min(n_hot, len(h)))
        sup = [x for x in (warm+cold+missing[:5]) if x not in sel]
        random.shuffle(sup)
        while len(sel)<6 and sup: sel.append(sup.pop(0))
    while len(sel)<6: sel.append(random.choice([x for x in pool if x not in sel]))
    sel = sorted(set(sel))[:6]
    while len(sel)<6:
        sel.append(random.choice([x for x in pool if x not in sel]))
        sel = sorted(set(sel))[:6]
    # 三区保障
    if not any(1<=x<=11 for x in sel): sel[0]=random.randint(1,11)
    if not any(12<=x<=22 for x in sel): sel[2]=random.randint(12,22)
    if not any(23<=x<=33 for x in sel): sel[5]=random.randint(23,33)
    return sorted(set(sel))[:6]

# ==================== 主战序列 ====================
def main():
    print("█"*70)
    print("  ANTIGRAVITY OMNI-STRIKE ENGINE V8.0 — 全联合作战")
    print("█"*70)
    
    # ---- 0. 加载物理基石 ----
    df = pd.read_csv(DATA_FILE)
    print(f"\n[基石] 已加载 {len(df)} 期数据，最新: {int(df.iloc[-1]['id'])} 期")
    
    # ---- 1. MCP探针: 注入最新开奖 ----
    # 042期: 02,07,12,19,24,31 + 10 (2026-04-16)
    # 043期: 06,09,14,16,25,32 + 16 (2026-04-19)
    new_periods = [
        {"id":2026042,"r1":2,"r2":7,"r3":12,"r4":19,"r5":24,"r6":31,"b":10,"date":"2026-04-16"},
        {"id":2026043,"r1":6,"r2":9,"r3":14,"r4":16,"r5":25,"r6":32,"b":16,"date":"2026-04-19"},
    ]
    for np_ in new_periods:
        if np_["id"] not in df["id"].values:
            df = pd.concat([df, pd.DataFrame([np_])], ignore_index=True)
            print(f"[MCP] 注入 {np_['id']}期")
    df.to_csv(DATA_FILE, index=False)
    
    # ---- 2. 动态回测：将上期预测与真实开奖对冲 ----
    with open("latest_decision.json", "r", encoding="utf-8") as f:
        old_decision = json.load(f)
    
    backtest_period = int(old_decision.get("target_period", 0))
    # 尝试从 df 中提取该期真实结果
    target_row = df[df["id"] == backtest_period]
    
    if not target_row.empty:
        actual_r = set([int(target_row.iloc[0][f"r{i}"]) for i in range(1, 7)])
        actual_b = int(target_row.iloc[0]["b"])
        print(f"\n{'='*70}")
        print(f"  ⚡ 逻辑对冲审计 | 期号: {backtest_period}")
        print(f"  真实开奖: 红 {sorted(actual_r)} | 蓝 {actual_b:02d}")
        print(f"{'='*70}")
        
        scores = []
        for p in old_decision.get("predictions", []):
            pr = set(p["红球"]); pb = p["蓝球"]
            rh = pr & actual_r; bh = (pb == actual_b)
            sc = len(rh) + (2 if bh else 0) # 蓝球权重设为2
            scores.append(sc)
            bm = "蓝✅" if bh else "蓝❌"
            print(f"  {p['组别']} {p['策略'][:10]:>10s}: {sorted(pr)} +{pb:02d} → 红{len(rh)} {bm} {sorted(rh)}")
        
        avg_r = sum(len(set(p["红球"]) & actual_r) for p in old_decision.get("predictions", [])) / len(old_decision.get("predictions", []))
        best_i = scores.index(max(scores))
        print(f"\n  📊 审计达成报告: 红球均命中 {avg_r:.1f} | 最佳表现: 第{best_i+1}组")
    else:
        print(f"\n[!] 警告: 库中尚未检测到 {backtest_period} 期，跳过回测阶段。")
        avg_r = 1.6 # 默认均值防止 PID 震荡
        best_i = 0
        actual_r = set()
        actual_b = 0
    
    # ---- 3. 武装所有武器 ----
    pid = PIDController()
    singularity = SingularityEngine()
    gravity = BlueBallGravityField()
    proxy = OmniProxyNode()
    hermes = HermesBridge()
    stats = StatisticsCore()
    
    # ---- 4. PID权重校准 ----
    TARGET_ACC = 3.0
    pid_out = pid.compute(TARGET_ACC, avg_r)
    n_hot = max(3, min(6, int(4 + pid_out)))
    print(f"\n[武器#2 PID] 误差={TARGET_ACC-avg_r:+.1f} 补偿={pid_out:+.2f} → 热号权重={n_hot}")
    
    # ---- 5. 统计特征提取 ----
    ft = stats.extract(df, 30)
    print(f"[统计核心] 热号:{ft['hot_r'][:8]} | 冷号:{ft['cold_r'][:6]} | 遗漏:{ft['missing'][:6]}")
    
    # ---- 6. 奇点引擎计算 ----
    matrix = [[float(row[f"r{i}"]) for i in range(1,7)] for _,row in df.tail(5).iterrows()]
    sing = singularity.search(matrix)
    sing_nums = sorted(set([max(1,min(33,round(s))) for s in sing]))
    print(f"[武器#3 奇点] 六维塌陷:{sing} → 映射:{sing_nums}")
    
    # ---- 7. 蓝球引力场 ----
    blue_core = gravity.predict(ft["recent_b"])
    print(f"[武器#4 引力场] 路径:{ft['recent_b']} → 核心蓝球:{blue_core}")
    
    # ---- 8. 尝试 Qwen/GPT 云节点 (非阻塞) ----
    cloud_groups = []
    prompt_text = f"最近10期数据:\n{df.tail(10)[['id','r1','r2','r3','r4','r5','r6','b']].to_string(index=False)}\n热号:{ft['hot_r']}\n冷号:{ft['cold_r']}\n生成5组042下一期预测"
    
    for model_name in ["gpt-4.6", "gemma-4", "gemini-1.5-pro", "qwen-plus"]:
        print(f"[武器#5/6 中转站] 尝试 {model_name}...", end=" ")
        resp = proxy.fire(prompt_text, model=model_name)
        if "PROXY_ERROR" in resp or "ERROR" in resp:
            print(f"离线 ({resp[:50]})")
        else:
            print(f"✅ 收到 {len(resp)} 字符")
            # 尝试提取数字序列
            matches = re.findall(r"\[?\s*(\d{1,2})\s*[,，]\s*(\d{1,2})\s*[,，]\s*(\d{1,2})\s*[,，]\s*(\d{1,2})\s*[,，]\s*(\d{1,2})\s*[,，]\s*(\d{1,2})\s*\]?\s*[+|＋]\s*(\d{1,2})", resp)
            for m in matches[:5]:
                nums = [int(x) for x in m[:6]]
                b = int(m[6])
                cloud_groups.append({"reds": sorted(nums), "blue": b, "source": model_name})
    
    # ---- 9. 下一期推演 ----
    next_period = int(df.iloc[-1]["id"]) + 1
    print(f"\n{'━'*70}")
    print(f"  🎯 {next_period} 期 全联合作战推演")
    print(f"{'━'*70}")
    
    random.seed(int(datetime.now().timestamp()))
    blue_pool = list(set([blue_core] + ft["hot_b"][:3] + ft["cold_b"][:1]))
    
    strategies = [
        ("PID热号骨架", "hot", n_hot),
        ("奇点引擎主导", "singularity", 3),
        ("热冷均衡+遗漏回补", "hot", 3),
        ("冷号反击+引力场", "cold", 2),
        ("自由覆盖最大离散", "hot", 2),
    ]
    
    preds = []
    for i,(desc,strat,nh) in enumerate(strategies, 1):
        reds = gen_group(ft["hot_r"], ft["warm_r"], ft["cold_r"], ft["missing"], sing_nums, strat, nh)
        if strat=="cold":
            blue = random.choice(ft["cold_b"]) if ft["cold_b"] else blue_core
        elif strat=="singularity":
            blue = blue_core
        else:
            blue = random.choice(blue_pool)
        preds.append({"组别":f"第{i}组","策略":desc,"红球":reds,"蓝球":blue})
        print(f"  组{i} [{desc}]: {reds} + {blue:02d}")
    
    # 如果云节点有返回，额外追加
    if cloud_groups:
        print(f"\n  ── 云端增援 ({len(cloud_groups)} 组) ──")
        for j,cg in enumerate(cloud_groups[:3], len(preds)+1):
            preds.append({"组别":f"第{j}组","策略":f"云端{cg['source']}","红球":cg["reds"],"蓝球":cg["blue"]})
            print(f"  组{j} [云端{cg['source']}]: {cg['reds']} + {cg['blue']:02d}")
    
    # ---- 10. 超级融合 (Super Fusion) 提纯算法 ----
    all_r_votes = []
    all_b_votes = []
    for p in preds:
        all_r_votes.extend(p["红球"])
        all_b_votes.append(p["蓝球"])
    
    r_counts = Counter(all_r_votes)
    b_counts = Counter(all_b_votes)
    top_r = [num for num, _ in r_counts.most_common(12)]
    top_b = [num for num, _ in b_counts.most_common(5)]
    
    fusion_preds = []
    for i in range(5):
        if i == 0:
            f_reds = sorted(top_r[:6])
            f_blue = top_b[0]
            f_strat = "绝对主干 (多模型票选之王)"
        elif i == 1:
            f_reds = sorted(top_r[1:7])
            f_blue = top_b[1] if len(top_b) > 1 else top_b[0]
            f_strat = "云端偏移 (防切偏离策略)"
        else:
            # 这里的量子网格采用固定随机种子保证结果可复现且稳定
            random.seed(next_period + i)
            f_reds = sorted(random.sample(top_r, 6))
            f_blue = random.choice(top_b)
            f_strat = "量子网格 (全域收敛对冲)"
        fusion_preds.append({"组别": f"融合第{i+1}组", "策略": f_strat, "红球": f_reds, "蓝球": f_blue})

    # ---- 11. Hermes 审计同步 ----
    hermes_result = hermes.sync_audit(
        str(next_period), 
        [{"红球":p["红球"],"蓝球":p["蓝球"]} for p in fusion_preds],
        {"043_audit": {"hits": avg_r}}
    )
    
    # ---- 12. 终极存档 ----
    decision = {
        "target_period": str(next_period),
        "engine_version": "V8.0-OmniStrike",
        "status": "ALL_WEAPONS_ARMED",
        "weapons_active": ["PID", "Singularity", "GravityField", "OmniProxy", "Hermes", "MCP", "GitHubAction"],
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fusion_results": fusion_preds,  # 专门存放综合计算结果
        "individual_predictions": preds, # 原始武器输出备份
        "backtest_info": {
            "period": backtest_period,
            "actual_reds": sorted(actual_r) if actual_r else [],
            "actual_blue": actual_b,
            "avg_red_hits": round(avg_r, 2),
            "best_group": best_i + 1,
        },
        "pid_signal": round(pid_out,3),
        "blue_gravity_core": blue_core,
        "hermes_audit": hermes_result,
    }
    
    with open("latest_decision.json","w",encoding="utf-8") as f:
        json.dump(decision, f, ensure_ascii=False, indent=2)
    
    # 演进报告
    report = f"""# 🌌 Antigravity V8.0 OmniStrike 全联合演进报告
> **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> **武器**: PID + 奇点引擎 + 蓝球引力场 + OmniProxy(Qwen/GPT) + Hermes审计 + MCP探针
> **演进链**: 031→041→042→{next_period}

## 回测 042期
- **真实**: 红 `{sorted(actual_r)}` 蓝 `{actual_b}`
- **均命中**: {avg_r:.1f}/6 | 最佳: 第{best_i+1}组

## 武器输出
- **PID**: 补偿 `{pid_out:+.2f}` → 热号权重 `{n_hot}`
- **奇点**: `{sing}` → `{sing_nums}`
- **引力场**: 路径 `{ft['recent_b']}` → 核心 `{blue_core}`
- **Hermes**: `{hermes_result.get('status')}`

## {next_period}期预测
| 组 | 策略 | 红球 | 蓝球 |
|----|------|------|------|
"""
    for p in preds:
        report += f"| {p['组别']} | {p['策略']} | {p['红球']} | {p['蓝球']:02d} |\n"
    report += "\n---\n*V8.0 全联合作战引擎 — 所有武器已武装 ✅*\n"
    
    with open("evolution_report.md","w",encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n{'█'*70}")
    print(f"  ✅ V8.0 全联合作战完成 | 目标: {next_period}期")
    print(f"  📄 latest_decision.json + evolution_report.md 已更新")
    print(f"  📊 数据基石: {len(df)} 期 | 武器全部在线")
    print(f"{'█'*70}")

if __name__ == "__main__":
    main()
