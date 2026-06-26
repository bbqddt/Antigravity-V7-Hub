from huggingface_hub import HfApi
import os

def force_upload():
    if not os.path.exists("token.txt"): 
        print("❌ 找不到 token.txt")
        return
    
    token = open("token.txt").read().strip()
    repo_id = "bbqddt2/Antigravity-Hive"
    
    # 定义要空投的物资清单
    files_to_push = ["app.py", "engine.py", "latest_decision.json", "README.md", "requirements.txt"]
    
    api = HfApi()
    print(f"🚀 正在发起 V18 官方级强攻至 {repo_id}...")

    try:
        for f_name in files_to_push:
            if os.path.exists(f_name):
                api.upload_file(
                    path_or_fileobj=f_name,
                    path_in_repo=f_name,
                    repo_id=repo_id,
                    repo_type="space",
                    token=token
                )
                print(f"✅ {f_name} 已成功占领阵地")
        print("\n🏁 统帅，全线占领成功！请刷新网页。")
    except Exception as e:
        print(f"❌ 攻势受阻: {e}")

if __name__ == "__main__":
    force_upload()