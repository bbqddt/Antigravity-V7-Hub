import os

def quick_sync():
    """在 IDE 中一键同步四位一体"""
    print("正在执行代码同步...")
    os.system("git add .")
    # 如果还没有初始化仓库，这里需要注意。先假设已有仓库
    os.system('git commit -m "V9.5: 指挥官在 IDE 注入最新因果逻辑"')
    os.system("git push origin main")
    print("🚀 灵魂已推向 GitHub，Hugging Face 正在重塑肉身...")

if __name__ == "__main__":
    quick_sync()
