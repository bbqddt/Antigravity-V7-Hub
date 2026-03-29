import os
import kagglehub
import pandas as pd
import streamlit as st

def sync_latest_data():
    """
    使用 Kaggle API 自动同步最新的双色球历史数据
    """
    print(">>> 正在启动 Kaggle 远程补给协议...")
    
    try:
        # 1. 从 Streamlit Secrets 获取身份钥匙
        os.environ["KAGGLE_USERNAME"] = st.secrets["KAGGLE_USERNAME"]
        os.environ["KAGGLE_API_TOKEN"] = st.secrets["KAGGLE_API_TOKEN"]

        # 2. 定位 Kaggle 上的优质双色球数据集 (ssq-history-data)
        dataset_handle = "fanyunqi/ssq-history-data"
        
        # 3. 下载/更新最新数据
        # 这个函数很智能：如果本地已是最新的，它就不会重复下载
        local_path = kagglehub.dataset_download(dataset_handle)
        
        # 4. 定位下载后的 CSV 文件 (通常数据集里会有个 csv)
        # 我们寻找目录下后缀为 .csv 的文件
        files = [f for f in os.listdir(local_path) if f.endswith('.csv')]
        if not files:
            raise Exception("Kaggle 目录中未找到数据文件")
        
        full_csv_path = os.path.join(local_path, files[0])
        print(f"✅ 数据补给成功: {full_csv_path}")
        return full_csv_path

    except Exception as e:
        print(f"❌ 远程同步链路故障: {e}")
        return None

if __name__ == "__main__":
    sync_latest_data()
