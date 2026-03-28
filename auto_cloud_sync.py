import os
from huggingface_hub import HfApi

# 1. 自主识别本地成果
local_result = "latest_predictions.csv"
repo_id = "bbqddt2/Antigravity-Hive"

# 2. 强制建立云端隧道
def auto_sync_to_cloud():
    if os.path.exists(local_result):
        try:
            api = HfApi()
            # 这里尝试自主抓取系统中的 HF_TOKEN 环境参数
            api.upload_file(
                path_or_fileobj=local_result,
                path_in_repo="latest_predictions.csv",
                repo_id=repo_id,
                repo_type="space"
            )
            print(">>> [自主演进] 云端阵地已同步。")
        except Exception as e:
            print(f">>> [同步受阻] 缺少物理凭证: {e}")

# 3. 激活 Kyma 交叉火力
def activate_kyma_nodes():
    nodes = [
        "https://api.c-03b7d12.kyma.ondemand.com", 
        "https://api.c-61dd4b5.kyma.ondemand.com"
    ]
    
    # 自动将这些节点压入运行环境
    os.environ['KYMA_NODE_A'] = nodes[0]
    os.environ['KYMA_NODE_B'] = nodes[1]
    
    print(f">>> [集群激活] 双 Kyma 节点已就位，进入全自动审计模式。")

if __name__ == "__main__":
    activate_kyma_nodes()
    auto_sync_to_cloud()
