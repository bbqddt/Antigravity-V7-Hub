import requests
import pandas as pd
import time
import random
import os
from tqdm import tqdm

class SegmentGenesisProbe:
    def __init__(self):
        self.target_url = "http://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': 'http://www.cwl.gov.cn/ygkj/wqkjgg/ssq/'
        }
        self.save_path = "e:/享中/data/ssq_history_full.csv"

    def execute_segment_hunt(self):
        print("🌌 [Antigravity 3.1 Pro] 启动分段回溯协议 (2003-2026)...")
        all_draws = []
        
        # 3.1 核心逻辑：每页 100 期，抓取 36 页，覆盖 3600 期
        for page in tqdm(range(1, 37), desc="🧬 正在缝合因果链条"):
            params = {
                'name': 'ssq',
                'dayStart': '2003-01-01',
                'pageNo': page,
                'pageSize': 100, # 降低单次负载，避免被封
                'systemType': 'PC'
            }
            try:
                res = requests.get(self.target_url, headers=self.headers, params=params, timeout=15)
                data = res.json()
                if 'result' in data:
                    for item in data['result']:
                        reds = item['red'].split(',')
                        all_draws.append({
                            'id': item['code'],
                            'r1': int(reds[0]), 'r2': int(reds[1]), 'r3': int(reds[2]),
                            'r4': int(reds[3]), 'r5': int(reds[4]), 'r6': int(reds[5]),
                            'b': int(item['blue']),
                            'date': item['date'][:10]
                        })
                # 随机冷却，欺骗反爬虫
                time.sleep(random.uniform(1.2, 2.5))
            except:
                continue
        
        if all_draws:
            df = pd.DataFrame(all_draws).sort_values(by='id').drop_duplicates(subset=['id']).reset_index(drop=True)
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            df.to_csv(self.save_path, index=False, encoding='utf-8-sig')
            print(f"\n✅ [全量注入成功] 当前本地库记录数: {len(df)} 期 (覆盖 2003-2026)")

if __name__ == "__main__":
    SegmentGenesisProbe().execute_segment_hunt()