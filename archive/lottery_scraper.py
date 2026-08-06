import os
import requests
import pandas as pd
import json


def fetch_safe():
    """从新浪彩票获取历史开奖数据"""
    print("🚀 启动强行突围模式，跳过所有 SSL 验证和代理限制...")
    url = "http://trend.caipiao.sina.com.cn/api/method/getHistory?gameId=1&pageSize=100"

    session = requests.Session()
    session.trust_env = False

    try:
        response = session.get(url, timeout=15)
        data_list = response.json().get('data', [])

        if not data_list:
            print("❌ 目标数据为空，请检查网络物理链路。")
            return

        base_dir = os.path.dirname(os.path.abspath(__file__))
        save_path = os.path.join(base_dir, 'data', 'lottery_history.csv')
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        records = [{'期号': i['issue'], '红球': i['red'], '蓝球': i['blue']} for i in data_list]
        df = pd.DataFrame(records)
        df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"✅ 战果已存入: {save_path}")

    except Exception as e:
        print(f"💥 突围失败: {e}")


if __name__ == "__main__":
    fetch_safe()
