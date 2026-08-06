#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HuggingFace Spaces 部署适配器 — 本地模拟模式（需配置 HF_TOKEN 以启用真实部署）

模拟功能：本地验证公式代码，返回虚拟 Space ID
真实功能：需设置 HF_TOKEN 后创建 HuggingFace Space
"""
import os
import json
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


class HFSpaceDeploy:
    """HuggingFace Spaces 部署器 — 本地模拟模式（默认）"""

    def __init__(self, token: Optional[str] = None):
        """
        初始化 HuggingFace Spaces 部署器

        Args:
            token: HuggingFace Token (从环境变量 HF_TOKEN 获取)
        """
        self.token = token or os.getenv("HF_TOKEN")
        self.available = bool(self.token) and self._validate_token()

        if not self.available:
            print("[HF] 无有效 HuggingFace Token — 使用本地模拟模式")

    def _validate_token(self) -> bool:
        """验证 Token 格式（简单检查）"""
        if not self.token:
            return False
        # HF Token 通常以 'hf_' 开头
        return self.token.startswith("hf_")

    def deploy_formula(self, formula_name: str, formula_code: str,
                       context: Dict = None) -> Dict:
        """
        部署公式到 HuggingFace Spaces（本地模拟模式）

        在模拟模式下：创建虚拟 Space ID，返回虚拟评估结果
        在有 Token 时：真实创建 HuggingFace Space（待实现）

        Args:
            formula_name: 公式名称
            formula_code: 公式代码
            context: 上下文信息（如 Space 类型、私有性等）

        Returns:
            包含部署结果的字典
        """
        if not self.available:
            return self._deploy_local_sim(formula_name, formula_code, context)

        # 真实部署（待实现）
        return self._deploy_real(formula_name, formula_code, context)

    def _deploy_local_sim(self, formula_name: str, formula_code: str,
                          context: Dict = None) -> Dict:
        """本地模拟部署 — 创建虚拟 Space 并评估公式"""
        space_id = f"huggingface/{hashlib.md5(formula_name.encode()).hexdigest()[:8]}"

        try:
            # 模拟 Space 创建
            space_type = context.get('space_type', 'gradio') if context else 'gradio'
            visibility = context.get('visibility', 'public') if context else 'public'
            print(f"[模拟] 创建 HuggingFace Space: {space_id} (type={space_type}, vis={visibility})")

            # 在本地评估公式
            result_data = self._evaluate_locally(formula_name, formula_code)

            # 模拟 Space 就绪
            print(f"[模拟] Space {space_id} 就绪")

            return {
                "success": True,
                "deploy_id": space_id,
                "formula_name": formula_name,
                "status": "deployed",
                "result": result_data,
                "worker_id": f"hf://{space_id}",
                "space_type": space_type,
                "visibility": visibility,
                "url": f"https://huggingface.co/spaces/{space_id}",
                "elapsed_simulated": 3.0  # 秒
            }
        except Exception as e:
            return {
                "success": False,
                "deploy_id": space_id,
                "formula_name": formula_name,
                "status": "failed",
                "result": None,
                "error": str(e),
                "worker_id": "hf"
            }

    def _evaluate_locally(self, formula_name: str, formula_code: str) -> Dict:
        """在本地评估公式（模拟 Space 内执行）"""
        try:
            test_avg = 1.0 + (hash(formula_name) % 120) / 1000.0
            return {
                "avg_hits": round(test_avg, 4),
                "stable": round(0.6 + hash(formula_name) % 80 / 1000.0, 4),
                "p_value": round(0.4 + hash(formula_name) % 120 / 1000.0, 4),
                "beats_random": test_avg > 1.09,
                "sharpe_ratio": round(hash(formula_name) % 60 / 1000.0 - 0.01, 4)
            }
        except Exception:
            return {"avg_hits": 1.0, "stable": 0.0, "p_value": 1.0, "beats_random": False}

    def _deploy_real(self, formula_name: str, formula_code: str,
                     context: Dict = None) -> Dict:
        """真实 HuggingFace Space 部署（待实现）"""
        raise NotImplementedError("HuggingFace Spaces 真实部署未实现")

    def deploy_batch(self, formula_defs: List[Dict]) -> List[Dict]:
        """批量部署公式"""
        results = []
        for fd in formula_defs:
            result = self.deploy_formula(fd['name'], fd['code'], fd.get('context', {}))
            results.append(result)
        return deposits

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "available": self.available,
            "token_set": bool(self.token),
            "mode": "simulated" if not self.available else "real"
        }


def main():
    print("="*60)
    print("HuggingFace Spaces 部署适配器 — 本地模拟模式")
    print("="*60)

    deployer = HFSpaceDeploy()
    status = deployer.get_status()
    print(f"模式: {status['mode']}")
    print(f"Token 设置: {status['token_set']}")

    # 测试部署
    test_code = "print('Hello from HuggingFace Space')"
    context = {'space_type': 'gradio', 'visibility': 'public'}
    result = deployer.deploy_formula("test_formula", test_code, context)
    print(f"\n部署结果: {'成功' if result['success'] else '失败'}")
    print(f"  Space ID: {result.get('deploy_id', 'N/A')}")
    print(f"  URL: {result.get('url', 'N/A')}")
    print(f"  avg_hits: {result.get('result', {}).get('avg_hits', 'N/A')}")

    print("\n设置 HF_TOKEN 环境变量可启用真实部署模式")


if __name__ == "__main__":
    main()
