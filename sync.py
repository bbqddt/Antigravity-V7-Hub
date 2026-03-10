import os
import subprocess

def quick_sync():
    print("\n" + "="*30)
    print("🚀 启动中枢同步协议 V12.8")
    print("="*30)
    
    try:
        # 执行同步
        os.system('git add .')
        msg = "2026026演化更新" # 移除 input() 以防止无交互终端挂死
        os.system(f'git commit -m "{msg}"')
        os.system('git push origin main')
        
        print("\n✅ 指挥官，云端‘肉身’已完成逻辑对齐！")
        print("🔗 请刷新 Hugging Face 页面查看最终战况。")
    except Exception as e:
        print(f"❌ 同步失败: {e}")

if __name__ == "__main__":
    quick_sync()