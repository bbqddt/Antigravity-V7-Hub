import requests
import json
import time
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# [Antigravity Omega] 算力矿山收割机 V1.0
# 目标：从 TinyFish 公开节点和共享池中实时嗅探可用的 API Token，实现无限弹药供应。

ARSENAL_FILE = str(_PROJECT_ROOT / 'arsenal.json')
MCP_POOL_URLS = [
    "https://agent.tinyfish.ai/mcp/get_key", # TinyFish 主节点
    "https://api.github.com/repos/search/tokens" # 示例：甚至可以去 GitHub 嗅探泄漏的 Key
]

def harvest():
    print("💎 [MINING] 正在深入算力矿区嗅探弹药...")
    new_keys = []
    
    # 逻辑 1: 从 TinyFish MCP 节点获取
    try:
        resp = requests.get(MCP_POOL_URLS[0], timeout=10).json()
        if resp.get("key"):
            new_keys.append(resp["key"])
            print(f"✅ 发现 TinyFish 共享弹药: {resp['key'][:10]}...")
    except: pass

    # 逻辑 2: 更多收割逻辑可以持续添加...

    if new_keys:
        # 更新弹药库
        arsenal = []
        if os.path.exists(ARSENAL_FILE):
            with open(ARSENAL_FILE, "r") as f:
                arsenal = json.load(f)
        
        # 去重并合并
        for k in new_keys:
            if k not in arsenal:
                arsenal.append(k)
        
        with open(ARSENAL_FILE, "w") as f:
            json.dump(arsenal, f, indent=4)
        print(f"🔥 [SUCCESS] 弹药库已扩充。当前库存: {len(arsenal)} 枚。")
    else:
        print("📭 [EMPTY] 本次嗅探未发现新弹药。")

if __name__ == "__main__":
    while True:
        harvest()
        time.sleep(300) # 每 5 分钟收割一轮
