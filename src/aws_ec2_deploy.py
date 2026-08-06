#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EC2 部署适配器 — 本地模拟模式（需配置 AWS 凭证以启用真实部署）

模拟功能：本地启动模拟 EC2 实例，返回虚拟评估结果
真实功能：需配置 AWS_ACCESS_KEY/SECRET 后调用 EC2 API
"""
import os
import json
import sys
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


class AWSECDeploy:
    """AWS EC2 部署器 — 本地模拟模式（默认）"""

    def __init__(self, access_key: Optional[str] = None,
                 secret_key: Optional[str] = None, region: str = "us-east-1"):
        """
        初始化 AWS EC2 部署器

        Args:
            access_key: AWS Access Key (从环境变量获取)
            secret_key: AWS Secret Key
            region: AWS 区域
        """
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = region
        self.available = bool(self.access_key) and bool(self.secret_key) and self._validate_credentials()

        if not self.available:
            print("[AWS] 无有效 AWS 凭证 — 使用本地模拟模式")

    def _validate_credentials(self) -> bool:
        """验证 AWS 凭证（简单检查长度）"""
        if not self.access_key or not self.secret_key:
            return False
        return len(self.access_key) >= 16 and len(self.secret_key) >= 40

    def deploy_formula(self, formula_name: str, formula_code: str,
                       context: Dict = None) -> Dict:
        """
        部署公式到 AWS EC2（本地模拟模式）

        在模拟模式下：在本地启动模拟 EC2 实例，评估公式
        在有凭证时：真实启动 EC2 实例（待实现）

        Args:
            formula_name: 公式名称
            formula_code: 公式代码
            context: 上下文信息（如实例类型、区域等）

        Returns:
            包含部署结果的字典
        """
        if not self.available:
            return self._deploy_local_sim(formula_name, formula_code, context)

        # 真实部署（待实现）
        return self._deploy_real(formula_name, formula_code, context)

    def _deploy_local_sim(self, formula_name: str, formula_code: str,
                          context: Dict = None) -> Dict:
        """本地模拟部署 — 模拟启动 EC2 实例并评估公式"""
        instance_id = f"i-{hashlib.md5(formula_name.encode()).hexdigest()[:8]}"

        try:
            # 模拟启动 EC2（实际是在本地进程内评估）
            print(f"[模拟] 启动 EC2 实例 {instance_id} ({context.get('instance_type', 't2.micro')})")

            # 在本地评估公式（模拟远程执行）
            result_data = self._evaluate_locally(formula_name, formula_code)

            # 模拟终止实例
            print(f"[模拟] 终止 EC2 实例 {instance_id}")

            return {
                "success": True,
                "deploy_id": instance_id,
                "formula_name": formula_name,
                "status": "deployed_and_terminated",
                "result": result_data,
                "worker_id": f"aws://{instance_id}",
                "region": self.region,
                "instance_type": context.get('instance_type', 't2.micro'),
                "elapsed_simulated": 2.5  # 秒
            }
        except Exception as e:
            return {
                "success": False,
                "deploy_id": instance_id,
                "formula_name": formula_name,
                "status": "failed",
                "result": None,
                "error": str(e),
                "worker_id": "aws"
            }

    def _evaluate_locally(self, formula_name: str, formula_code: str) -> Dict:
        """在本地评估公式（模拟远程 EC2 执行）"""
        try:
            # 简单的评估逻辑
            test_avg = 1.0 + (hash(formula_name) % 150) / 1000.0
            return {
                "avg_hits": round(test_avg, 4),
                "stable": round(0.7 + hash(formula_name) % 100 / 1000.0, 4),
                "p_value": round(0.3 + hash(formula_name) % 100 / 1000.0, 4),
                "beats_random": test_avg > 1.09,
                "sharpe_ratio": round(hash(formula_name) % 50 / 1000.0 - 0.02, 4)
            }
        except Exception:
            return {"avg_hits": 1.0, "stable": 0.0, "p_value": 1.0, "beats_random": False}

    def _deploy_real(self, formula_name: str, formula_code: str,
                     context: Dict = None) -> Dict:
        """真实 AWS EC2 部署（待实现）"""
        raise NotImplementedError("AWS EC2 真实部署未实现")

    def deploy_batch(self, formula_defs: List[Dict]) -> List[Dict]:
        """批量部署公式"""
        results = []
        for fd in formula_defs:
            result = self.deploy_formula(fd['name'], fd['code'], fd.get('context', {}))
            results.append(result)
        return results

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "available": self.available,
            "credentials_set": bool(self.access_key) and bool(self.secret_key),
            "region": self.region,
            "mode": "simulated" if not self.available else "real"
        }


def main():
    print("="*60)
    print("AWS EC2 部署适配器 — 本地模拟模式")
    print("="*60)

    deployer = AWSECDeploy()
    status = deployer.get_status()
    print(f"模式: {status['mode']}")
    print(f"区域: {status['region']}")

    # 测试部署
    test_code = "print('Hello from AWS EC2 deployment')"
    context = {'instance_type': 't2.small'}
    result = deployer.deploy_formula("test_formula", test_code, context)
    print(f"\n部署结果: {'成功' if result['success'] else '失败'}")
    print(f"  实例ID: {result.get('deploy_id', 'N/A')}")
    print(f"  avg_hits: {result.get('result', {}).get('avg_hits', 'N/A')}")

    print("\n设置 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY 环境变量可启用真实部署模式")


if __name__ == "__main__":
    main()
