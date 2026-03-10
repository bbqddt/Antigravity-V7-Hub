# sync.py
import os

# 把原来的 def sync(): 改成 def execute_push():
def execute_push(): 
    print("\n" + "="*30)
    print("🚀 启动中枢同步协议 V12.9")
    print("="*30)
    
    os.system('git add .')
    msg = input("请输入本次逻辑变更说明 (默认: 自动化同步): ") or "自动化同步"
    os.system(f'git commit -m "{msg}"')
    os.system('git push origin main')
    print("\n✅ 指挥官，云端数据已对齐！")

if __name__ == "__main__":
    execute_push() # 这里也要对应修改