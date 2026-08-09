# -*- coding: utf-8 -*-
"""
HF Spaces 部署脚本 — 上传 Antigravity 项目到 Hugging Face

用法:
    python deploy_hf.py --space username/Antigravity --token $HF_TOKEN
    python deploy_hf.py --space username/Antigravity --token $HF_TOKEN --quiet
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def check_prerequisites():
    """检查依赖"""
    try:
        from huggingface_hub import HfApi
        return True
    except ImportError:
        print("❌ huggingface_hub 未安装")
        print("   运行: pip install huggingface_hub")
        return False


def create_tarball() -> Path:
    """打包项目文件"""
    tar_path = _PROJECT_ROOT / "antigravity_hf_deploy.tar.gz"
    print(f"📦 打包项目到 {tar_path}...")

    # 排除不必要的文件
    exclude_patterns = [
        ".venv", "__pycache__", "*.pyc", "node_modules", ".git",
        "archive", "models", "dist", "*.exe", "*.vbs", "*.bat",
        "*.ps1", ".env", "keys.json", "logs", "*.tar.gz",
        "ChromeProfile", "Start_Antigravity.bat",
    ]

    cmd = (
        f'tar czf "{tar_path}" --exclude="*/{p}" ' +
        f'{"--exclude=*/*/" + p for p in exclude_patterns[:3]} ' +
        f'-C "{_PROJECT_ROOT.parent}" "{_PROJECT_ROOT.name}"'
    )
    # 简化：直接用 shutil 打包 hf_space/ 目录
    import tarfile
    with tarfile.open(tar_path, "w:gz") as tar:
        hf_dir = _PROJECT_ROOT
        for item in hf_dir.iterdir():
            if item.name != "deploy_hf.py":
                tar.add(item, arcname=item.name)

    size_mb = tar_path.stat().st_size / (1024 * 1024)
    print(f"✅ 打包完成: {size_mb:.1f} MB")
    return tar_path


def deploy_to_hf(space_id: str, token: str, quiet: bool = False):
    """部署到 HF Spaces"""
    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=token)

    # 创建或获取空间
    try:
        repo_url = api.create_repo(
            repo_id=space_id,
            repo_type="space",
            exist_ok=True,
            space_sdk="gradio",
            space_hardware="cpu",
        )
        if not quiet:
            print(f"✅ Space 已创建/找到: https://huggingface.co/{space_id}")
    except Exception as e:
        print(f"⚠️ 创建Space失败: {e}")
        print(f"   请确认: {space_id} 格式正确，且你有权限")
        return False

    # 上传文件
    hf_dir = _PROJECT_ROOT
    uploaded = 0
    errors = 0

    for file_path in hf_dir.glob("*"):
        if file_path.is_file() and file_path.name != "deploy_hf.py":
            try:
                api.upload_file(
                    path_or_fileobj=str(file_path),
                    path_in_repo=file_path.name,
                    repo_id=space_id,
                    repo_type="space",
                )
                uploaded += 1
                if not quiet:
                    print(f"  📤 {file_path.name}")
            except Exception as e:
                print(f"  ❌ {file_path.name}: {e}")
                errors += 1

    print(f"\n{'='*50}")
    print(f"  部署完成! 上传 {uploaded} 个文件 ({errors} 个错误)")
    print(f"  访问: https://huggingface.co/spaces/{space_id}")
    print(f"{'='*50}")
    return True


def main():
    parser = argparse.ArgumentParser(description="部署 Antigravity 到 HF Spaces")
    parser.add_argument("--space", required=True, help="Space ID, 如: username/Antigravity")
    parser.add_argument("--token", default=None, help="HF Token (或设置 HF_TOKEN 环境变量)")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    args = parser.parse_args()

    token = args.token or os.environ.get("HF_TOKEN")
    if not token:
        print("❌ 需要提供 HF_TOKEN:")
        print("   python deploy_hf.py --space user/Antigravity --token <your-token>")
        print("   或 set HF_TOKEN=<your-token>")
        sys.exit(1)

    if not check_prerequisites():
        sys.exit(1)

    print(f"\n🚀 开始部署到 HF Spaces: {args.space}")
    deploy_to_hf(args.space, token, args.quiet)


if __name__ == "__main__":
    main()
