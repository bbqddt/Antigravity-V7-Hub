import pandas as pd
import os

def execute_push():
    """内置同步逻辑"""
    print("\n" + "="*30)
    print("🚀 启动全量同步协议...")
    print("="*30)
    os.system('git add .')
    msg = input("请输入同步说明 (默认: 数据更新): ") or "数据更新"
    os.system(f'git commit -m "{msg}"')
    os.system('git push origin main')
    print("\n✅ 云端看板已同步！")

def harvest_main():
    """数据注入逻辑"""
    print("\n" + "🛰️ " * 10)
    print("ANTIGRAVITY 自动化收割机启动...")
    
    csv_path = 'data/ssq_history_full.csv'
    
    if not os.path.exists(csv_path):
        print(f"❌ 找不到文件: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    last_id = int(df.iloc[-1]['id'])
    
    print(f"📡 当前基石期数: {last_id}")
    user_input = input(f"检测到 {last_id + 1} 期数据了吗？(Y/N): ")
    
    if user_input.upper() == 'Y':
        data_str = input("输入号码 (格式: r1 r2 r3 r4 r5 r6 b): ")
        nums = data_str.split()
        
        if len(nums) == 7:
            # 1. 物理注入数据
            new_row = {
                'id': last_id + 1,
                'r1': int(nums[0]), 'r2': int(nums[1]), 'r3': int(nums[2]),
                'r4': int(nums[3]), 'r5': int(nums[4]), 'r6': int(nums[5]),
                'blue': int(nums[6])
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(csv_path, index=False)
            print(f"✅ 第 {last_id+1} 期已固化。")
            
            # 2. 直接运行文件内的同步函数
            execute_push() 
        else:
            print("❌ 号码数量不对！")
    else:
        print("☕ 守候中...")

if __name__ == "__main__":
    harvest_main()