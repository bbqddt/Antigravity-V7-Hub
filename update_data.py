import requests
import pandas as pd
import io
import os
import time

def auto_update():
    file_path = 'ssq_history_full.csv'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # 1. 加载现有数据
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
    else:
        df = pd.DataFrame(columns=['id','r1','r2','r3','r4','r5','r6','b','date'])

    # 2. 判断是否需要启动“全量收割” (少于 3000 期则视为数据残缺)
    if len(df) < 3000:
        print("🚨 侦测到因果链严重残缺，启动全量收割模式 (2003-2026)...")
        all_records = []
        for page in range(1, 40):  # 抓取前 40 页，覆盖 23 年
            url = f"https://m.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&pageNo={page}&pageSize=100"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                data = r.json().get('result', [])
                if not data: break
                for item in data:
                    reds = item['red'].split(',')
                    all_records.append({
                        'id': int(item['code']),
                        'r1': int(reds[0]), 'r2': int(reds[1]), 'r3': int(reds[2]),
                        'r4': int(reds[3]), 'r5': int(reds[4]), 'r6': int(reds[5]),
                        'b': int(item['blue']), 'date': item['date'].split('(')[0]
                    })
                print(f"📥 已劫持第 {page} 页数据...")
                time.sleep(0.5)
            except: break
        df = pd.DataFrame(all_records)
    else:
        # 正常增量更新逻辑
        print("✅ 基础数据充沛，执行日常增量缝补...")
        url = "https://m.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&issueCount=5"
        r = requests.get(url, headers=headers, timeout=10)
        new_data = r.json().get('result', [])
        for item in new_data:
            issue_id = int(item['code'])
            if issue_id not in df['id'].values:
                reds = item['red'].split(',')
                new_row = {'id': issue_id, 'r1': int(reds[0]), 'r2': int(reds[1]), 'r3': int(reds[2]), 
                           'r4': int(reds[3]), 'r5': int(reds[4]), 'r6': int(reds[5]), 
                           'b': int(item['blue']), 'date': item['date'].split('(')[0]}
                df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)

    # 3. 排序并保存
    df.sort_values('id', ascending=False).to_csv(file_path, index=False)
    print(f"🏁 同步完成。当前因果链总深度: {len(df)} 期")

if __name__ == "__main__":
    auto_update()
