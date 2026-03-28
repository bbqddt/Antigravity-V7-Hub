import os
from huggingface_hub import HfApi

def sync_predictions_to_hf():
    print("🚀 启动 Hugging Face 云端同步隧道...")
    # 获取本地最新的预测结果文件
    local_file_path = 'latest_predictions.csv'
    
    if not os.path.exists(local_file_path):
        print(f"❌ [警告] 找不到 {local_file_path}，无法执行上行同步")
        return
        
    try:
        # 需在环境变量中配置 HF_TOKEN，或已经通过 huggingface-cli login
        # 为了与自动化兼容，我们尽量读取环境变量
        token = os.environ.get('HF_TOKEN')
        api = HfApi(token=token)
        
        # 将文件推送到指定的 Dataset
        repo_id = "bbqddt2/Antigravity-Hive"
        print(f"📡 目标空间锁定: {repo_id}")
        
        api.upload_file(
            path_or_fileobj=local_file_path,
            path_in_repo="latest_predictions.csv",
            repo_id=repo_id,
            repo_type="dataset", # 也可以是 model/space，根据您的 Hive 定义决定
        )
        print("✅ [SUCCESS] 云端阵地推演结果『重生』完毕，24/7 监控就位")
    except Exception as e:
        print(f"❌ [ERROR] Hugging Face 隧道传输失败: {e}")

if __name__ == "__main__":
    sync_predictions_to_hf()
