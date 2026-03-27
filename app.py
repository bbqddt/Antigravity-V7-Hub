import openai
import pandas as pd
import time
import os

# 鉴权配置
API_KEY = "AIzaSyC--Fs9TA5Ypdo62bPZfIXuZwL1OGRLG4Q"
client = openai.OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def run_prediction():
    print(">>> 正在启动 3.1 Pro 算力推演...")
    
    # 增加 60 秒强制冷却，确保 Google 配额计数器重置
    print(">>> 正在进行链路冷却（预计 60 秒），请勿中断...")
    time.sleep(60) 

    try:
        # 路径适配
        data_path = r"D:\Antigravity_V7\data\lottery_history.csv"
        output_path = r"D:\Antigravity_V7\latest_predictions.csv"
        
        df = pd.read_csv(data_path).tail(20) # 略微减少期数以降低 Token 消耗
        data_info = df.to_string()

        response = client.chat.completions.create(
            model="gemini-3.1-pro-preview", # 匹配 Playground 算力
            messages=[
                {"role": "system", "content": "You are a data auditor. Predict 10 sets based on collision trends."},
                {"role": "user", "content": f"Data:\n{data_info}\nPredict for period 2026033. Format: R,R,R,R,R,R|B"}
            ],
            temperature=0.1
        )

        result = response.choices[0].message.content
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"period,numbers\n2026033,\"{result.strip()}\"")
        
        print("✅ SUCCESS: 033 期战报已生成！")

    except Exception as e:
        if "429" in str(e):
            print("❌ 依然过载。建议：请在 AI Studio 手动点击左侧 'Settings' 查看 Quota 限制。")
        else:
            print(f"❌ 链路异常: {e}")

if __name__ == "__main__":
    run_prediction()
