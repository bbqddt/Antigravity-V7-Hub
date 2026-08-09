import google.generativeai as genai
import os


def run_gemini_evolution(prompt_path="v7_evolved_prompt.json", api_key=None):
    """
    Gemini 高维推演引擎
    Args:
        prompt_path: 进化Prompt文件路径
        api_key: Google API密钥（通过环境变量 GOOGLE_API_KEY 配置）
    """
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("❌ 未设置 GOOGLE_API_KEY 环境变量")
        return

    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    with open(prompt_path, 'r', encoding='utf-8') as f:
        context = f.read()

    print("[Gemini] 正在载入进化权重...")
    response = model.generate_content(f"作为反重力物理引擎，基于以下逻辑内核推演决策：\n{context}")

    print("\n[高维推演结果]:")
    print(response.text)


if __name__ == "__main__":
    run_gemini_evolution()
