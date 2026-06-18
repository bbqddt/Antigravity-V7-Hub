import os
import kagglehub
import streamlit as st

def sync_latest_data():
    """
    使用 Kaggle API 自动同步最新的双色球历史数据
    """
    try:
        # 从 Streamlit Secrets 提取钥匙
        os.environ["KAGGLE_USERNAME"] = st.secrets["KAGGLE_USERNAME"]
        os.environ["KAGGLE_API_TOKEN"] = st.secrets["KAGGLE_API_TOKEN"]

        # 指定 Kaggle 上的双色球数据集
        dataset_handle = "fanyunqi/ssq-history-data"
        
        # 自动下载（如果本地已有且是最新的，则跳过下载）
        local_path = kagglehub.dataset_download(dataset_handle)
        
        # 寻找目录下的 CSV 文件
        files = [f for f in os.listdir(local_path) if f.endswith('.csv')]
        if not files:
            return None
        
        return os.path.join(local_path, files[0])

    except Exception as e:
        print(f"Kaggle Sync Error: {e}")
        return None
