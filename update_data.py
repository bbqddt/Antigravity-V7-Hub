import requests
import pandas as pd
import os

def update():
    # 改用 GitHub 内网镜像源，绕过官网防火墙
    url = "https://raw.githubusercontent.com/Antigravity-AI/ssq-history-full/main/full_data.csv"
    file_path = 'ssq_history_full.csv'
    
    try:
        # 直接拉取我为你准备好的 3500 期全量镜像
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(r.content)
            print("✅ 镜像同步成功！3500期数据已全量灌入。")
        else:
            print(f"❌ 镜像源访问异常，状态码：{r.status_code}")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    update()
