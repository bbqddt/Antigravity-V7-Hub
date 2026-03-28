import os
from huggingface_hub import HfApi

def force_push_and_restart():
    repo_id = "bbqddt2/Antigravity-Hive"
    api = HfApi() # 自动获取系统 HF_TOKEN
    
    files_to_sync = ["app.py", "latest_predictions.csv"]
    
    print(f"🚀 开始空投 V22.1 代码矩阵与数据记录至 {repo_id}...")
    
    # 1. 上传文件
    for file in files_to_sync:
        if os.path.exists(file):
            try:
                print(f"  👉 正在推流 [{file}] ...", end="")
                api.upload_file(
                    path_or_fileobj=file,
                    path_in_repo=file,
                    repo_id=repo_id,
                    repo_type="space"
                )
                print(" ✅")
            except Exception as e:
                print(f" ❌ 同步失败: {e}")
        else:
            print(f"  ⚠️ [警告] 找不到本地文件: {file}")
            
    # 2. 触发重启
    print("🔄 正在触发云端生态重启 (Space Restart)...")
    try:
        api.restart_space(repo_id=repo_id)
        print("✅ Space 重启指令下发成功！全新推演节点已激活。")
    except Exception as e:
        print(f"❌ 重启失败，可能是由于权限或空间状态导致: {e}")

if __name__ == "__main__":
    force_push_and_restart()
