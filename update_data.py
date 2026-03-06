import requests
import pandas as pd
import os

def update():
    url = "https://raw.githubusercontent.com/Antigravity-AI/ssq-history-full/main/full_data.csv"
    file_path = 'ssq_history_full.csv'
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        res = r.json().get('result', [])
        if not res: return # 抓不到就退出，不删数据
        
        new_data = []
        for i in res:
            reds = i['red'].split(',')
            new_data.append({
                'id': int(i['code']), 'r1': int(reds[0]), 'r2': int(reds[1]),
                'r3': int(reds[2]), 'r4': int(reds[3]), 'r5': int(reds[4]),
                'r6': int(reds[5]), 'b': int(i['blue']), 'date': i['date'].split('(')[0]
            })
        
        df_new = pd.DataFrame(new_data)
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            df_old = pd.read_csv(file_path)
            df_final = pd.concat([df_new, df_old]).drop_duplicates('id').sort_values('id', ascending=False)
        else:
            df_final = df_new
            
        df_final.to_csv(file_path, index=False)
        print("✅ 数据同步完成")
    except:
        print("⚠️ 官网拒绝访问，保留原始地基")

if __name__ == "__main__":
    update()
