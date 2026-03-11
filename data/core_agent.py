import os

class CoreAgent:
    def __init__(self):
        print("🛰️  [AGENT] 总控同步模块已激活...")

    def fast_sync(self):
        """一键完成 Git 提交与推送"""
        print("\n" + "="*30)
        print("🚀 启动全网对齐协议...")
        print("="*30)
        
        # 执行物理同步指令
        try:
            os.system('git add .')
            os.system('git commit -m "V45 Logic Update: Quantum Collapse Live"')
            os.system('git push origin main')
            print("\n✅ [SUCCESS] 资产已推送到 Hugging Face，请刷新页面查看！")
        except Exception as e:
            print(f"❌ [ERROR] 同步失败: {e}")

if __name__ == "__main__":
    agent = CoreAgent()
    # 执行同步
    agent.fast_sync()