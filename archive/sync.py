import os

def execute_push():
    print("\n" + "="*30)
    print("🚀 ANTIGRAVITY 核心同步引擎 V12.9")
    print("="*30)
    
    # 执行 Git 命令
    os.system('git add .')
    msg = input("请输入本次逻辑变更说明: ") or "自动化同步"
    os.system(f'git commit -m "{msg}"')
    os.system('git push origin main')
    
    print("\n✅ 云端对齐成功！指挥官请刷新页面。")

if __name__ == "__main__":
    execute_push()