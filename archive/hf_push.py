import os
import sys

def force_upload():
    """上传文件到 HuggingFace Hub"""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("❌ 请先安装 huggingface_hub: pip install huggingface_hub")
        return

    if not os.path.exists("token.txt"):
        # 尝试从环境变量获取
        token = os.environ.get("HF_TOKEN")
        if not token:
            print("❌ 找不到 token.txt，请设置 HF_TOKEN 环境变量")
            return
    else:
        token = open("token.txt", "r").read().strip()
        repo_id = "bbqddt2/Antigravity-Hive"

    api = HfApi()
    print(f"🚀 正在发起强攻至 {repo_id}...")

    files_to_push = [
        "app.py", "engine.py", "data_layer.py",
        "Antigravity_V8_Core.py", "latest_decision.json",
        "README.md", "requirements.txt"
    ]

    try:
        uploaded = False
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
                uploaded = True
            else:
                print(f"⚠️ 跳过: {f_name}（不存在）")

        if uploaded:
            print("\n🏁 全线占领成功！请刷新网页。")
        else:
            print("⚠️ 没有文件被上传")
    except Exception as e:
        print(f"❌ 攻势受阻: {e}")

if __name__ == "__main__":
    force_upload()
