import os
import requests
import pandas as pd
import json

# --- 阵地配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'data', 'lottery_history.csv')

# --- ToAPIs 通讯配置 ---
TO_API_KEY = os.environ.get("TO_API_KEY", "您的_sk_令牌")  # 通过环境变量配置
API_URL = "https://api.toapis.com/v1/chat/completions"

def run_cloud_audit():
    try:
        if not os.path.exists(CSV_PATH):
            print(f"❌ 路径故障：找不到 {CSV_PATH}")
            return

        df = pd.read_csv(CSV_PATH)
        df.columns = df.columns.str.strip()
        context_data = df.tail(30).to_string()

        print(f"📡 正在通过原生链路上传 {len(df)} 期数据至云端审计...")

        headers = {
            "Authorization": f"Bearer {TO_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gemini-2.0-flash",
            "messages": [
                {"role": "system", "content": "你是一位精通第一性原理的数据审计专家。"},
                {"role": "user", "content": f"基于以下历史碰撞数据，分析最新期的红蓝球概率分布：\n{context_data}"}
            ]
        }

        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            result = response.json()
            print("\n✨ --- 云端'天机'审计结果 ---")
            print(result['choices'][0]['message']['content'])
            print("-" * 30)
        else:
            print(f"❌ 链路回传错误: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ 系统级故障: {e}")

if __name__ == "__main__":
    run_cloud_audit()
