import pandas as pd
import os
from sync import execute_push  # 这一行是关键：跨文件调用

def harvest_and_sync():
    print("\n" + "🛰️ " * 10)
    print("ANTIGRAVITY 自动化收割机启动...")
    
    csv_path = 'data/ssq_history_full.csv'
    df = pd.read_csv(csv_path)
    last_id = int(df.iloc[-1]['id'])
    
    print(f"📡 当前基石期数: {last_id}")
    user_input = input(f"检测到 {last_id + 1} 期数据了吗？(Y/N): ")
    
    if user_input.upper() == 'Y':
        data_str = input("输入号码 (r1 r2 r3 r4 r5 r6 b): ")
        nums = data_str.split()
        if len(nums) == 7:
            # 注入数据逻辑
            new_row = {'id': last_id+1, 'r1':nums[0], 'r2':nums[1], 'r3':nums[2], 
                        'r4':nums[3], 'r5':nums[4], 'r6':nums[5], 'blue':nums[6]}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(csv_path, index=False)
            
            # 这里的魔法：调用 sync.py 里的函数
            execute_push() 
        else:
            print("❌ 号码数量不对！")

if __name__ == "__main__":
    harvest_and_sync()