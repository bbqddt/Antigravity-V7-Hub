# --- 统帅专用：极简抗压版推演脚本 ---
import openai
import pandas as pd
import time

API_KEY = "AIzaSyC--Fs9TA5Ypdo62bPZfIXuZwL1OGRLG4Q" #
client = openai.OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def run_low_pressure_audit():
    print(">>> 正在启动反重力冷却协议...")
    # 强制增加冷却，避开 Google 敏感期
    time.sleep(70) 

    try:
        # 仅读取最近 10 期数据，大幅降低 Token 负载
        df = pd.read_csv(r"D:\Antigravity_V7\data\lottery_history.csv").tail(10)
        data_info = df.to_string()

        response = client.chat.completions.create(
            model="gemini-3.1-pro-preview", 
            messages=[
                {"role": "system", "content": "You are a data auditor."},
                {"role": "user", "content": f"Data:\n{data_info}\nPredict for period 2026033."}
            ],
            temperature=0.1 #
        )
        
        result = response.choices[0].message.content
        with open("latest_predictions.csv", "w", encoding="utf-8") as f:
            f.write(f"period,numbers\n2026033,\"{result.strip()}\"")
        
        print("✅ SUCCESS: 033 期数据已成功穿透锁定！")

    except Exception as e:
        print(f"❌ 链路反馈: {e}")

if __name__ == "__main__":
    run_low_pressure_audit()
