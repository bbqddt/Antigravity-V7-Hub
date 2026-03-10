# sync.py 修改如下
import os

def execute_push(): # 函数名改掉，不再叫 sync
    print("🚀 启动中枢同步协议...")
    os.system('git add .')
    msg = input("说明: ") or "Update"
    os.system(f'git commit -m "{msg}"')
    os.system('git push origin main')