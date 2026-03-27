import openai
import pandas as pd
import time
import os

# 1. 权限配置
API_KEY = "AIzaSyC--Fs9TA5Ypdo62bPZfIXuZwL1OGRLG4Q"
client = openai.OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def run_audit_mission():
    print(">>> 正在启动 Gemini 3.1 Pro 算力集群...")
    
    # 强制冷却 60 秒，破解 429 Resource Exhausted 限制
    print(">>> 正在进行链路安全冷却（60秒），避开 Google 配额封锁...")
    time.sleep(60) 

    try:
        # 路径指向您的 V7 核心数据层
        data_path = r"D:\Antigravity_V7\data\lottery_history.csv"
        output_path = r"D:\Antigravity_V7\latest_predictions.csv"
        
        if not os.path.exists(data_path):
            print(f"❌ 错误：找不到数据文件 {data_path}")
            return

        # 采样最近 25 期，降低 Token 消耗以保持链路稳定
        df = pd.read_csv(data_path).tail(25)
        data_context = df.to_string()

        # 2. 发起 3.1 预览版请求
        response = client.chat.completions.create(
            model="gemini-3.1-pro-preview", 
            messages=[
                {"role": "system", "content": "你是一个高级数据审计员。基于时空碰撞理论推演10组数据。"},
                {"role": "user", "content": f"历史趋势：\n{data_context}\n请推演 2026033 期组合。格式：R,R,R,R,R,R|B"}
            ],
            temperature=0.1 # 极低温度确保逻辑严密性
        )

        final_result = response.choices[0].message.content
        
        # 3. 写入反重力指挥中心
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"period,numbers\n2026033,\"{final_result.strip()}\"")
        
        print(f"✅ MISSION COMPLETE: 033 期推演结果已同步至 {output_path}")

    except Exception as e:
        if "429" in str(e):
            print("❌ 警告：即使等待了60秒，算力依然过载。请检查是否还有其他 Playground 页面在运行。")
        else:
            print(f"❌ 链路异常: {e}")

if __name__ == "__main__":
    run_audit_mission()
