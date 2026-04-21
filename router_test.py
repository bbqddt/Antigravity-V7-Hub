from openai import OpenAI

# 1. 物理接入：OpenRouter 超级网关
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

def start_audit():
    print("🚀 反重力审计员：正在接入 OpenRouter 多模型矩阵...")
    
    # 尝试模型列表，直到一个能跑通
    models_to_try = [
        "anthropic/claude-3.5-sonnet:beta", # 增加 beta 后缀更稳
        "deepseek/deepseek-chat",           # 万能备选，响应极快
        "google/gemini-pro-1.5"            # 最后的防线
    ]

    for model_id in models_to_try:
        try:
            print(f"⏳ 正在尝试调用 {model_id} 执行 043 期逻辑审计...")
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:8501", 
                    "X-Title": "Antigravity_V7_Audit",
                },
                model=model_id,
                messages=[
                    {"role": "system", "content": "你现在是反重力系统高阶策略合伙人，核心课题是'时间并不存在'。"},
                    {"role": "user", "content": "基于'时间不存在'假设，对 043 期双色球开奖张量进行逻辑审计。"}
                ]
            )
            print("\n" + "="*30)
            print(f"🔥 来自 {model_id} 的 043 期审计报告：")
            print("="*30)
            print(completion.choices[0].message.content)
            return # 成功后直接退出
        except Exception as e:
            print(f"⚠️ {model_id} 暂时无法访问，尝试下一个模型... (错误: {e})")

if __name__ == "__main__":
    start_audit()
