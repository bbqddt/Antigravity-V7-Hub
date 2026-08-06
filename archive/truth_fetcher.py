import requests
from bs4 import BeautifulSoup
import json
import csv
import os
import time
import sys

# 强制设置控制台输出为 UTF-8 (解决 Windows 乱码)
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def fetch_ssq_history(limit=5000):
    """
    Antigravity 进化版 V2：全量真理抓取引擎 (兼容编码版)
    """
    url = f"http://datachart.500.com/ssq/history/newinc/history.php?limit={limit}&sort=0"
    
    print(f"[LOG] Connecting to source: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.encoding = 'utf-8'
        
        if resp.status_code != 200:
            print(f"[WARN] Connection failed: {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.select('tr.t_tr1')
        
        history_data = []
        # 云端与本地自适应路径
        target_csv = "data/lottery_history.csv"
        alt_path = r"d:\Antigravity_V7\data\lottery_history.csv"
        
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 8:
                period = tds[0].text.strip()
                if not period.isdigit(): continue # 过滤非数字行
                reds = [tds[i].text.strip() for i in range(1, 7)]
                blue = tds[7].text.strip()
                date = tds[15].text.strip() if len(tds) > 15 else ""
                history_data.append([period, ",".join(reds), blue, date])

        # 核心修复：强制降序排列，确保最新期号在第一行
        history_data.sort(key=lambda x: int(x[0]), reverse=True)

        # 尝试保存至多个位置确保同步
        paths_to_save = [target_csv]
        alt_path = r"d:\Antigravity_V7\data\lottery_history.csv"
        if os.path.exists(os.path.dirname(alt_path)):
            paths_to_save.append(alt_path)

        for p in paths_to_save:
            with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["period", "red", "blue", "date"])
                writer.writerows(history_data)
            print(f"[SUCCESS] Data synced to: {p}")


        return history_data

    except Exception as e:
        print(f"[ERROR] Evolution interrupted: {e}")
        return []

if __name__ == "__main__":
    fetch_ssq_history(limit=5000)
