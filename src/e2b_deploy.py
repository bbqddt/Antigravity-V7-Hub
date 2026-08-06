#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2B 部署适配器 — 将公式演进结果部署到 E2B 沙箱评估环境
支持真实云端沙箱评估，提供分布式评估的后端支持
"""
import os
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根到路径
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from e2b import Sandbox
    E2B_AVAILABLE = True
except ImportError:
    E2B_AVAILABLE = False


class E2BDeploy:
    """E2B 部署器 — 公式在独立沙箱中并行评估"""

    def __init__(self, api_key: Optional[str] = None, template: str = "ubuntu"):
        """
        初始化 E2B 部署器

        Args:
            api_key: E2B API Key (从环境变量 E2B_API_KEY 获取)
            template: 沙箱模板 (python/nodejs/等)
        """
        self.api_key = api_key or os.getenv("E2B_API_KEY")
        self.template = template
        self.available = False
        self._check_availability()

    def _check_availability(self) -> None:
        """检查 E2B 是否可用"""
        if not E2B_AVAILABLE:
            print("[E2B] e2b SDK 未安装，pip install e2b-code-interpreter")
            return

        if not self.api_key:
            print("[E2B] 未设置 E2B_API_KEY 环境变量")
            return

        try:
            # 测试连接（创建临时沙箱后立即销毁）
            sandbox = Sandbox.create(api_key=self.api_key, template=self.template, timeout=30)
            sandbox.kill()
            self.available = True
            print(f"[E2B] 可用 (template={self.template})")
        except Exception as e:
            self.available = False
            print(f"[E2B] 不可用: {e}")

    def deploy_formula(self, formula_name: str, formula_code: str,
                       task_id: str = None) -> Dict:
        """
        部署单个公式到 E2B 沙箱进行评估

        Args:
            formula_name: 公式名称
            formula_code: 公式评估代码
            task_id: 任务ID（可选）

        Returns:
            包含沙箱ID、评估结果和错误信息的字典
        """
        if not self.available:
            return {
                "success": False,
                "error": "E2B 不可用",
                "sandbox_id": None,
                "result": None,
                "worker_id": "e2b"
            }

        task_id = task_id or f"e2b_{formula_name}_{int(time.time())}"
        sandbox = None

        try:
            # 创建沙箱
            sandbox = Sandbox.create(
                api_key=self.api_key,
                template=self.template,
                timeout=120  # 延长超时以适应公式评估
            )

            # 写入评估脚本
            script_path = f"/tmp/eval_{task_id}.py"
            sandbox.files.write(script_path, formula_code)

            # 运行评估
            env_vars = {
                "TASK_ID": task_id,
                "FORMULA_NAME": formula_name
            }
            result = sandbox.commands.run(
                f"python3 {script_path}",
                env_vars=env_vars,
                timeout=110
            )

            # 解析结果
            if result.error:
                raise Exception(f"沙箱执行错误: {result.error}")

            result_data = json.loads(result.stdout.strip())

            return {
                "success": True,
                "sandbox_id": sandbox.sandbox_id,
                "task_id": task_id,
                "result": result_data,
                "worker_id": f"e2b://{sandbox.sandbox_id}",
                "elapsed": result.duration
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sandbox_id": sandbox.sandbox_id if sandbox else None,
                "task_id": task_id,
                "result": None,
                "worker_id": "e2b"
            }
        finally:
            if sandbox and sandbox.is_running():
                sandbox.kill()

    def deploy_batch(self, formula_defs: List[Dict], max_concurrent: int = 3) -> List[Dict]:
        """
        批量部署公式到 E2B 沙箱（并行）

        Args:
            formula_defs: 列表，每个元素包含 {'name': str, 'code': str, 'task_id': str}
            max_concurrent: 最大并发沙箱数

        Returns:
            所有评估结果的列表
        """
        if not self.available:
            return [{"success": False, "error": "E2B 不可用"}] * len(formula_defs)

        # 使用简单的串行调用（E2B 沙箱有配额限制，串行更稳定）
        results = []
        for fd in formula_defs:
            result = self.deploy_formula(fd['name'], fd['code'], fd.get('task_id'))
            results.append(result)
            time.sleep(0.5)  # 避免配额限制

        return results

    def get_status(self) -> Dict:
        """获取 E2B 部署器状态"""
        return {
            "available": self.available,
            "api_key_set": bool(self.api_key),
            "template": self.template,
            "sdk_available": E2B_AVAILABLE
        }


def main():
    """测试 E2B 部署器"""
    print("="*60)
    print("E2B 部署适配器 — 测试")
    print("="*60)

    # 创建测试部署器
    deployer = E2BDeploy()

    # 显示状态
    status = deployer.get_status()
    print(f"\n状态: {'可用' if status['available'] else '不可用'}")
    print(f"  SDK 可用: {status['sdk_available']}")
    print(f"  API Key 设置: {status['api_key_set']}")

    if not status['available']:
        print("\n请设置 E2B_API_KEY 环境变量或构造函数参数")
        return

    # 创建简单的测试公式评估代码
    test_formula = """
import sys
sys.path.insert(0, '/root')
from formula_lang.primitive import get_default_primitives
from formula_lang.grammar import FormulaGrammar
from formula_lang.evaluator import FormulaEvaluator
import json

# 获取原语
prims = get_default_primitives()[:2]  # 使用前2个原语
formula = FormulaGrammar.resonance(prims, name='test_formula')

# 加载数据（从环境变量读取路径）
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from data_layer import load_history

draws = load_history()
evaluator = FormulaEvaluator(random_baseline=1.09)
result = evaluator.evaluate(formula, draws, n_windows=3, window_size=500, step=100)

print(json.dumps(result))
"""

    # 部署测试公式
    print("\n测试部署单个公式...")
    result = deployer.deploy_formula("test_formula", test_formula)
    print(f"  成功: {result['success']}")
    if result['success']:
        print(f"  沙箱ID: {result['sandbox_id']}")
        print(f"  结果: avg_hits={result['result'].get('avg_hits', 'N/A')}, beats_random={result['result'].get('beats_random', 'N/A')}")
    else:
        print(f"  错误: {result['error']}")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
