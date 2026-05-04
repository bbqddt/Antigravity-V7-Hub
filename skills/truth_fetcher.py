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
        target_csv = r"e:\享中\ssq_history_full.csv"
        
        print(f"[LOG] Captured {len(rows)} trajectories. Parsing...")

        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 8:
                period = tds[0].text.strip()
                reds = [tds[i].text.strip() for i in range(1, 7)]
                blue = tds[7].text.strip()
                date = tds[15].text.strip() if len(tds) > 15 else ""
                
                history_data.append([period, ",".join(reds), blue, date])

        # 保存为 CSV
        with open(target_csv, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["period", "red", "blue", "date"])
            writer.writerows(history_data)

        print(f"[SUCCESS] Data saved to: {target_csv}")
        return history_data

    except Exception as e:
        print(f"[ERROR] Evolution interrupted: {e}")
        return []

if __name__ == "__main__":
    fetch_ssq_history(limit=5000)
