import requests
import pandas as pd
import time
import os

def force_rebuild_causality():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    file_path = 'ssq_history_full.csv'
    
    print("🚀 启动全量暴力收割模式 (2003-2026)...")
    all_records = []
    
    # 暴力抓取 45 页，确保 3500+ 期一条不漏
    for page in range(1, 46):
        url = f"https://m.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&pageNo={page}&pageSize=100"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            data = r.json().get('result', [])
            if not data: break
            
            for item in data:
                reds = item['red'].split(',')
                all_records.append({
                    'id': int(item['code']), # 强制建立 id 列
                    'r1': int(reds[0]), 'r2': int(reds[1]), 'r3': int(reds[2]),
                    'r4': int(reds[3]), 'r5': int(reds[4]), 'r6': int(reds[5]),
                    'b': int(item['blue']), 
                    'date': item['date'].split('(')[0]
                })
            print(f"📥 劫持中：已获取 {len(all_records)} 条记录...")
            time.sleep(0.4) # 稍微加速
        except Exception as e:
            print(f"⚠️ 跳过异常页: {e}")
            continue

    if all_records:
        # 彻底不看旧文件，直接用新抓到的数据覆盖
        df = pd.DataFrame(all_records)
        df = df.sort_values('id', ascending=False)
        df.to_csv(file_path, index=False)
        print(f"🏁 暴力收割成功！全量因果链已归位：共 {len(df)} 期。")
    else:
        print("❌ 抓取失败，请检查网络或接口。")

if __name__ == "__main__":
    force_rebuild_causality()
