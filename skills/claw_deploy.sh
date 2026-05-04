#!/bin/bash
# 🔱 Antigravity Omega - Claw Cloud (ap-northeast-1) 离岸要塞部署脚本

echo "🚀 [1/4] 正在加固东京阵地 (Claw Cloud)..."
sudo apt update && sudo apt install -y python3-pip git screen curl

echo "📦 [2/4] 正在拉取 Omega 核心防御组件..."
# 针对 Claw Cloud 的独享算力优化
pip3 install streamlit requests beautifulsoup4 pandas openai pyyaml

echo "📂 [3/4] 正在同步真理抓取逻辑 (Truth Fetcher)..."
cat <<EOF > ~/truth_fetcher.py
import requests
import json
from bs4 import BeautifulSoup

def fetch_ssq_history():
    url = "http://datachart.500.com/ssq/history/newinc/history.php?limit=10"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.select('tr.t_tr1')
        history = []
        for row in rows:
            tds = row.find_all('td')
            if len(tds) > 10:
                history.append({"期号": tds[0].text.strip(), "红球": [tds[i].text.strip() for i in range(1, 7)], "蓝球": tds[7].text.strip()})
        with open("history_truth.json", "w", encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        print("✅ Claw Cloud: 真理已同步。")
    except Exception as e: print(f"❌ Error: {e}")

if __name__ == "__main__":
    fetch_ssq_history()
EOF

echo "🔥 [4/4] 正在点火：启动离岸观测塔..."
# 绑定 0.0.0.0 确保公网可达
screen -dmS claw_tower streamlit run app.py --server.port 8501 --server.address 0.0.0.0

echo "✅ 报告长官：东京阵地 (Claw Cloud) 已部署完成！"
echo "🔗 请访问: http://您的Claw服务器IP:8501"
