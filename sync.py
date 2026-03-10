import os

def quick_sync():
    print("🚀 启动中枢同步协议 V12.7...")
    os.system('git add .')
    msg = input("请输入本次逻辑变更说明 (直接回车则默认为‘自动进化’): ") or "自动进化同步"
    os.system(f'git commit -m "{msg}"')
    os.system('git push origin main')
    print("✅ 云端‘肉身’已完成逻辑对齐！")

if __name__ == "__main__":
    quick_sync()