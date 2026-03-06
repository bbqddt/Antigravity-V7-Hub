import requests
import pandas as pd
import time

def force_rebuild():
    url_template = "https://m.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&pageNo={}&pageSize=100"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    all_data = []

    print("开始穿越回 2003 年...")
    for page in range(1, 41): # 抓 40 页 = 4000 条
        try:
            r = requests.get(url_template.format(page), headers=headers, timeout=15)
            res = r.json().get('result', [])
            if not res: break
            
            for item in res:
                reds = item['red'].split(',')
                all_data.append({
                    'id': int(item['code']),
                    'r1': int(reds[0]), 'r2': int(reds[1]), 'r3': int(reds[2]),
                    'r4': int(reds[3]), 'r5': int(reds[4]), 'r6': int(reds[5]),
                    'b': int(item['blue']),
                    'date': item['date'].split('(')[0]
                })
            print(f"进度：已抓取 {len(all_data)} 条...")
            time.sleep(0.3)
        except: break

    if len(all_data) > 3000:
        df = pd.DataFrame(all_data).sort_values('id', ascending=False)
        # 暴力覆盖，不讲道理
        df.to_csv('ssq_history_full.csv', index=False)
        print(f"✅ 成功！最终写入文件总数：{len(df)}")
    else:
        print(f"❌ 抓取数量异常 ({len(all_data)})，取消写入以保护原始数据。")

if __name__ == "__main__":
    force_rebuild()
