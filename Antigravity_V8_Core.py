import os
import sys
import json
import csv
import random
import requests
from bs4 import BeautifulSoup
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "ssq_history_full.csv")
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")
REPORT_FILE = os.path.join(BASE_DIR, "Latest_Prediction_V8.md")
JSON_OUTPUT = os.path.join(BASE_DIR, "latest_decision_v8.json")

def sync_latest_data():
    print(">>> 启动绝对真理数据流...")
    url = "https://datachart.500.com/ssq/history/newinc/history.php?start=03001&end=26150"
    headers = {"User-Agent": "Mozilla/5.0"}
    local_data = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            local_data = list(reader)
    
    local_periods = {row['period'] for row in local_data if 'period' in row}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        tbody = soup.find('tbody', id='tdata')
        
        new_records = []
        if tbody:
            for tr in tbody.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 7:
                    period = tds[0].text.strip()
                    reds = ",".join([td.text.strip() for td in tds[1:7]])
                    blue = tds[7].text.strip()
                    date_str = tds[15].text.strip() if len(tds) >= 16 else ""
                    if period and period not in local_periods:
                        new_records.append({'period': period, 'red': reds, 'blue': blue, 'date': date_str})
        
        if new_records:
            with open(CSV_FILE, 'a', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['period', 'red', 'blue', 'date'])
                if not local_data: writer.writeheader()
                for rec in sorted(new_records, key=lambda x: x['period']):
                    writer.writerow(rec)
            local_data.extend(sorted(new_records, key=lambda x: x['period']))
    except Exception as e:
        print(f"⚠️ 网络拉取异常，使用历史数据: {e}")
    return local_data

def calculate_zero_t_tension(data, top_n=3):
    if not data: return []
    all_reds = []
    for row in data[-100:]:
        try:
            all_reds.extend([int(x) for x in row['red'].split(',')])
        except: pass
    
    red_counts = Counter(all_reds)
    candidates = []
    for _ in range(3000):
        sample_reds = sorted(random.sample(range(1, 34), 6))
        sample_blue = random.randint(1, 16)
        consecutive = sum(1 for a, b in zip(sample_reds, sample_reds[1:]) if b - a == 1)
        if consecutive >= 3: continue
        score = sum(red_counts.get(r, 0) for r in sample_reds)
        if consecutive == 1: score += 5
        if consecutive == 2: score -= 2
        odds = sum(1 for r in sample_reds if r % 2 != 0)
        if odds in (2, 3, 4): score += 3
        candidates.append({'red': sample_reds, 'blue': sample_blue, 'score': score})
        
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    unique_candidates = []
    seen = set()
    for c in candidates:
        sig = tuple(c['red'])
        if sig not in seen:
            seen.add(sig)
            unique_candidates.append(c)
        if len(unique_candidates) >= top_n:
            break
    return unique_candidates

def main():
    top_n = 3
    if len(sys.argv) > 1:
        try: top_n = int(sys.argv[1])
        except: pass

    data = sync_latest_data()
    preds = calculate_zero_t_tension(data, top_n)
    
    # 获取下一期期号
    latest_period = int(data[-1]['period']) if data else 26057
    target_period = latest_period + 1

    # 输出 JSON 供 TG Bot 读取
    json_output = {
        "target_period": str(target_period),
        "engine": "V8 Zero-T (Physical Tension)",
        "groups": []
    }
    for p in preds:
        red_str = ", ".join([f"{x:02d}" for x in p['red']])
        json_output["groups"].append({
            "red": red_str,
            "blue": p['blue'],
            "score": p['score']
        })

    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4)
    print(f"V8 核心演算完成！生成了 {top_n} 组数据，期号推演为: {target_period}")

if __name__ == "__main__":
    main()
