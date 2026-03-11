import os
import pandas as pd
import time

class CoreAgent:
    def __init__(self):
        self.csv_path = 'data/ssq_history_full.csv'
        self.check_environment()

    def check_environment(self):
        """确保物理基石存在"""
        if not os.path.exists('data'):
            os.makedirs('data')
            print("📁 [SYSTEM] 已创建 data 目录")
        
        if not os.path.exists(self.csv_path):
            print(f"❌ [ERROR] 找不到基石文件: {self.csv_path}")
            # 这里可以放一个初始化 CSV 的逻辑，但我们假设你已有 3510 期数据
        else:
            print(f"✅ [READY] 物理链路通畅。基石期数: {len(pd.read_csv(self.csv_path))} 期")

    def sync_to_cloud(self, message="V45 自动化演进同步"):
        """一键推送至 Hugging Face"""
        print("\n" + "="*30)
        print("🚀 启动云端对齐协议...")
        print("="*30)
        try:
            os.system('git add .')
            # 自动提交，不再需要你手动敲说明
            os.system(f'git commit -m "{message}"')
            os.system('git push origin main')
            print("\n✅ [SUCCESS] 云端看板已更新。")
        except Exception as e:
            print(f"❌ [SYNC ERROR] 同步失败: {e}")

    def get_last_id(self):
        df = pd.read_csv(self.csv_path)
        return int(df.iloc[-1]['id'])

# 实例化
agent = CoreAgent()

if __name__ == "__main__":
    # 测试运行
    print(f"🛰️  当前系统最后期数: {agent.get_last_id()}")
    print("💡 提示: 总控已就绪，等待 auditor.py 进行逻辑审计。")