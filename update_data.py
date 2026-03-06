import requests
import pandas as pd
import io
import os

def auto_update():
    # 1. 抓取官网真实数据 (cwl 接口)
    url = "https://m.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&issueCount=5"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        new_data = r.json()['result']
        
        # 2. 读取仓库里那个 241 期的 CSV
        file_path = 'ssq_history_full.csv'
        if not os.path.exists(file_path):
            print("❌ 错误：找不到 ssq_history_full.csv 文件")
            return

        df = pd.read_csv(file_path)
        
        # 3. 严谨校准：对比期号，发现缺失则补齐
        updated = False
        for item in new_data:
            issue_id = int(item['code'])
            # 如果官网的期号在你的 CSV 里找不到，就执行“自生长”
            if issue_id not in df['id'].values:
                reds = item['red'].split(',')
                new_row = {
                    'id': issue_id,
                    'r1': int(reds[0]), 'r2': int(reds[1]), 'r3': int(reds[2]),
                    'r4': int(reds[3]), 'r5': int(reds[4]), 'r6': int(reds[5]),
                    'b': int(item['blue']), 
                    'date': item['date'].split('(')[0]
                }
                # 插入到最前面
                df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)
                updated = True
                print(f"✅ 成功劫持新期号: {issue_id}")

        if updated:
            # 保持 ID 倒序排列，确保严谨
            df.sort_values('id', ascending=False).to_csv(file_path, index=False)
            print("💾 物理数据库已完成同步更新。")
        else:
            print("💡 检查完毕：当前已是最新因果链，无需补齐。")

    except Exception as e:
        print(f"❌ 运行异常: {e}")

if __name__ == "__main__":
    auto_update()
