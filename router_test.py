from openai import OpenAI

# 1. 物理接入：OpenRouter 超级网关
# 确保使用你刚才展示的完整 sk-or-v1-... 密钥
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

def start_audit():
    print("🚀 反重力审计员：正在接入 OpenRouter 多模型矩阵...")
    print("⏳ 正在调用 Claude 3.5 Sonnet 执行 043 期逻辑对冲...")

    try:
        # 注意：模型 ID 必须是 anthropic/claude-3-5-sonnet (连字符格式)
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:8501", 
                "X-Title": "Antigravity_V7_Audit",
            },
            model="anthropic/claude-3-5-sonnet",
            messages=[
                {
                    "role": "system", 
                    "content": "你现在是反重力系统的高阶策略合伙人。你的底层逻辑是'第一性原理'，你的核心课题是'时间并不存在'。你负责对双色球开奖张量进行逻辑审计，剔除虚假概率，只留下具备物理确定性的号码。"
                },
                {
                    "role": "user", 
                    "content": "针对双色球 043 期，基于'时间不存在'的假设，请对历史中奖张量进行压力测试。给出你审计后的逻辑闭环号码，并解释为什么要剔除虚假干扰。"
                }
            ]
        )
        
        print("\n" + "="*30)
        print("🔥 043 期反重力审计报告：")
        print("="*30)
        print(completion.choices[0].message.content)
        print("="*30)
        
    except Exception as e:
        print(f"\n❌ 点火中断！错误原因：{e}")

if __name__ == "__main__":
    start_audit()
