import requests
import pandas as pd
import io
import os

def auto_update():
    # 1. 抓取官网最新开奖 (cwl 移动端接口，稳定且无反爬)
    url = "https://m.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&issueCount=5"
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)'}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        new_data = r.json()['result']
        
        # 2. 加载仓库现有的 CSV
        file_path = 'ssq_history_full.csv'
        df = pd.read_csv(file_path)
        
        # 3. 检查并缝补缺失期号
        updated = False
        for item in new_data:
            issue_id = int(item['code'])
            if issue_id not in df['id'].values:
                reds = item['red'].split(',')
                new_row = {
                    'id': issue_id,
                    'r1': int(reds[0]), 'r2': int(reds[1]), 'r3': int(reds[2]),
                    'r4': int(reds[3]), 'r5': int(reds[4]), 'r6': int(reds[5]),
                    'b': int(item['blue']), 
                    'date': item['date'].split('(')[0]
                }
                df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)
                updated = True
                print(f"✅ 成功补齐期号: {issue_id}")

        if updated:
            # 4. 保持严谨排序并存回
            df.sort_values('id', ascending=False).to_csv(file_path, index=False)
            print("💾 CSV 数据库已更新。")
        else:
            print("💡 数据已是最新，无需更新。")

    except Exception as e:
        print(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    auto_update()
