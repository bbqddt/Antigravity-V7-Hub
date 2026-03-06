import requests
import pandas as pd
import time
import os

def update_causality():
    file_path = 'ssq_history_full.csv'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # 1. 尝试抓取最新数据 (单页即可，因为你已经有地基了)
    url = "https://m.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&pageNo=1&pageSize=30"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json().get('result', [])
        if not data:
            raise ValueError("官网接口返回为空，可能被拦截了")
            
        new_records = []
        for item in data:
            reds = item['red'].split(',')
            new_records.append({
                'id': int(item['code']),
                'r1': int(reds[0]), 'r2': int(reds[1]), 'r3': int(reds[2]),
                'r4': int(reds[3]), 'r5': int(reds[4]), 'r6': int(reds[5]),
                'b': int(item['blue']),
                'date': item['date'].split('(')[0]
            })
        
        new_df = pd.DataFrame(new_records)

        # 2. 读取现有地基
        if os.path.exists(file_path):
            old_df = pd.read_csv(file_path)
            # 合并并去重
            final_df = pd.concat([new_df, old_df]).drop_duplicates(subset=['id']).sort_values('id', ascending=False)
        else:
            final_df = new_df

        # 3. 写入文件
        final_df.to_csv(file_path, index=False)
        print(f"✅ 成功！当前因果链总深度：{len(final_df)}")

    except Exception as e:
        print(f"❌ 更新失败: {e}。保持原数据不变。")

if __name__ == "__main__":
    update_causality()
