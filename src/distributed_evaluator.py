# -*- coding: utf-8 -*-
"""
Antigravity 分布式评估引擎 V2.0 — 多后端统一调度

核心理念:
- 统一接口: evaluate(tasks, backend="auto")
- 自动选择最优backend: Local > Ray > HTTP > E2B > GitHub Actions > QwenPaw
- 故障降级: 云端不可用自动切回本地
- 零配置启动: 不需要任何外部服务也能跑

架构:
┌───────────────────────────────────────────────────────────────────┐
│                    DistributedEvaluator                           │
│                                                                   │
│  优先级从高到低:                                                  │
│  1. Ray    — 腾讯云CVM 32核分布式集群                             │
│  2. HTTP   — 远程Worker API (GitHub Actions / E2B / 其他)          │
│  3. E2B    — E2B沙箱并行评估                                      │
│  4. GH     — GitHub Actions workflow                              │
│  5. QP     — QwenPaw (AgentScope) 文件协作桥                      │
│  6. Local  — 本机ProcessPoolExecutor (保底)                       │
│                                                                   │
│  evaluate(tasks)                                                  │
│    └── auto → 按优先级探测可用backend → 执行 → 失败则降级           │
└───────────────────────────────────────────────────────────────────┘
"""
import json
import time
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
import multiprocessing

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════
# 任务/结果定义 — 所有backend共用
# ═══════════════════════════════════════════════════════════

@dataclass
class EvalTask:
    task_id: str
    formula_name: str
    primitive_names: List[str]
    operator: str
    parameters: Dict = field(default_factory=dict)
    eval_config: Dict = field(default_factory=lambda: {
        "n_windows": 20,
        "window_size": 400,
        "step": 40,
    })

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EvalTask":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EvalResult:
    task_id: str
    formula_name: str
    avg_hits: float
    std: float
    best: float
    worst: float
    windows: int
    beats_random: bool
    composite_score: float = 0.0
    sharpe_ratio: float = 0.0
    p_value: float = 1.0
    worker_id: str = "local"
    elapsed_ms: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EvalResult":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════
# 子进程评估函数 (必须在模块顶层，才能被pickle)
# ═══════════════════════════════════════════════════════════

def _evaluate_single_task(task_dict: dict) -> dict:
    """在子进程中执行单个公式评估"""
    import math
    from data_layer import load_history
    from formula_lang.primitive import get_default_primitives
    from formula_lang.grammar import FormulaGrammar
    from formula_lang.evaluator import FormulaEvaluator

    task = EvalTask.from_dict(task_dict)
    start = time.time()

    prims = [p for p in get_default_primitives() if p.name in task.primitive_names]
    if len(prims) < 2:
        return EvalResult(
            task_id=task.task_id, formula_name=task.formula_name,
            avg_hits=0, std=1, best=0, worst=0, windows=0,
            beats_random=False, worker_id="local"
        ).to_dict()

    op = task.operator
    name = task.formula_name

    if 'cascade' in op:
        formula = FormulaGrammar.cascade(prims, name=name)
    elif 'resonance' in op:
        formula = FormulaGrammar.resonance(prims, name=name)
    elif 'phase' in op:
        formula = FormulaGrammar.phase_align(prims, name=name)
    elif 'blend' in op or 'adaptive' in op:
        formula = FormulaGrammar.adaptive_blend(prims, name=name)
    else:
        formula = FormulaGrammar.weighted_sum(prims, name=name)

    evaluator = FormulaEvaluator(random_baseline=1.09)
    draws = load_history()
    result = evaluator.evaluate(formula, draws, **task.eval_config)

    elapsed = int((time.time() - start) * 1000)

    return EvalResult(
        task_id=task.task_id,
        formula_name=task.formula_name,
        avg_hits=result['avg_hits'],
        std=result['std'],
        best=result['max_hits'],
        worst=result['min_hits'],
        windows=result['rounds'],
        beats_random=result['beats_random'],
        composite_score=result.get('composite_score', 0),
        sharpe_ratio=result.get('sharpe_ratio', 0),
        p_value=result.get('p_value', 1.0),
        worker_id="local",
        elapsed_ms=elapsed,
    ).to_dict()


# ═══════════════════════════════════════════════════════════
# Backend: Local (ProcessPoolExecutor)
# ═══════════════════════════════════════════════════════════

class LocalBackend:
    """本地多进程后端 — 利用本机CPU多核"""

    def __init__(self, max_workers=None):
        self.max_workers = max_workers or max(2, multiprocessing.cpu_count() - 2)
        self.backend_name = f"local({self.max_workers}procs)"
        self.available = True  # Local永远可用

    def evaluate(self, tasks: List[EvalTask]) -> List[EvalResult]:
        if not tasks:
            return []

        results = []
        task_dicts = [t.to_dict() for t in tasks]

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(_evaluate_single_task, td): i
                for i, td in enumerate(task_dicts)
            }

            completed = 0
            for future in as_completed(future_to_idx):
                completed += 1
                idx = future_to_idx[future]
                try:
                    result_dict = future.result(timeout=300)
                    result = EvalResult.from_dict(result_dict)
                    results.append(result)
                    if completed % 5 == 0 or completed == len(tasks):
                        print(f"    [{self.backend_name}] {completed}/{len(tasks)} "
                              f"(avg={result.avg_hits:.4f}, {result.elapsed_ms}ms)")
                except Exception as e:
                    print(f"    [{self.backend_name}] 公式 #{idx} 失败: {e}")
                    results.append(EvalResult(
                        task_id=f"error_{idx}", formula_name=f"error_{idx}",
                        avg_hits=0, std=1, best=0, worst=0, windows=0,
                        beats_random=False, worker_id=self.backend_name,
                    ))

        return results


# ═══════════════════════════════════════════════════════════
# Backend: Ray (腾讯云CVM分布式)
# ═══════════════════════════════════════════════════════════

class RayBackend:
    """Ray分布式后端 — 连接腾讯云CVM 32核集群"""

    def __init__(self):
        self.backend_name = "ray(remote)"
        self.available = False
        self._try_init()

    def _try_init(self):
        """尝试连接Ray集群"""
        try:
            import ray
            # 先试本地
            try:
                ray.init(address="local", ignore_reinit_error=True)
                self.available = True
                print(f"  [RayBackend] 本地Ray集群已连接")
                return
            except Exception:
                pass

            # 再试远程CVM
            cvm_ip = os.environ.get("RAY_CVM_IP", "42.193.130.173")
            ray_address = f"ray://{cvm_ip}:6379"
            ray.init(address=ray_address, ignore_reinit_error=True)
            self.available = True
            print(f"  [RayBackend] 远程Ray集群已连接 ({cvm_ip})")
        except ImportError:
            print(f"  [RayBackend] 不可用 (ray未安装: pip install ray[default])")
        except Exception as e:
            print(f"  [RayBackend] 不可用 ({e})")

    def evaluate(self, tasks: List[EvalTask]) -> List[EvalResult]:
        if not self.available or not tasks:
            return []

        import ray

        @ray.remote
        def _remote_evaluate(task_dict: dict) -> dict:
            return _evaluate_single_task(task_dict)

        futures = [_remote_evaluate.remote(t.to_dict()) for t in tasks]
        results_dicts = ray.get(futures)

        return [EvalResult.from_dict(r) for r in results_dicts]


# ═══════════════════════════════════════════════════════════
# Backend: HTTP (通用远程Worker API)
# ═══════════════════════════════════════════════════════════

class HTTPBackend:
    """HTTP远程后端 — 通过API调用云端Worker"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.environ.get("EVAL_API_URL", "")
        self.backend_name = f"http({self.base_url or 'none'})"
        self.available = bool(self.base_url) and self._check()

    def _check(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.base_url}/health", method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            return resp.status == 200
        except Exception:
            return False

    def evaluate(self, tasks: List[EvalTask]) -> List[EvalResult]:
        if not self.available or not tasks:
            return []

        import urllib.request
        results = []

        for task in tasks:
            payload = json.dumps(task.to_dict()).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/evaluate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                resp = urllib.request.urlopen(req, timeout=120)
                result_dict = json.loads(resp.read().decode('utf-8'))
                results.append(EvalResult.from_dict(result_dict))
            except Exception as e:
                print(f"    [HTTP] 评估失败: {e}")
                results.append(EvalResult(
                    task_id=task.task_id, formula_name=task.formula_name,
                    avg_hits=0, std=1, best=0, worst=0, windows=0,
                    beats_random=False, worker_id=self.backend_name,
                ))

        return results


# ═══════════════════════════════════════════════════════════
# Backend: E2B 沙箱
# ═══════════════════════════════════════════════════════════

class E2BBackend:
    """E2B沙箱后端 — 每个公式在独立沙箱中评估"""

    def __init__(self):
        self.backend_name = "e2b(sandbox)"
        self.available = False
        self._try_init()

    def _try_init(self):
        """尝试初始化E2B连接"""
        try:
            from e2b import Sandbox
            api_key = os.environ.get("E2B_API_KEY")
            if api_key:
                sandbox = Sandbox.create()
                sandbox.kill()
                self.available = True
                print(f"  [E2BBackend] 可用 (API_KEY已配置)")
            else:
                print(f"  [E2BBackend] 不可用 (未设置E2B_API_KEY环境变量)")
        except ImportError:
            print(f"  [E2BBackend] 不可用 (e2b SDK未安装: pip install e2b)")
        except Exception as e:
            print(f"  [E2BBackend] 不可用: {type(e).__name__}")

    def evaluate(self, tasks: List[EvalTask]) -> List[EvalResult]:
        if not self.available or not tasks:
            return []

        from e2b import Sandbox
        results = []

        for task in tasks:
            try:
                sandbox = Sandbox.create()
                # 上传评估脚本
                script = f"""
import sys
sys.path.insert(0, '/root')
import json
import os

# 设置项目根目录（将当前目录添加到sys.path）
os.chdir('/root')
sys.path.insert(0, '.')

from formula_lang.primitive import get_default_primitives
from formula_lang.grammar import FormulaGrammar
from formula_lang.evaluator import FormulaEvaluator

# 从环境变量获取任务数据
task_json = os.environ.get('TASK_DATA', '{{}}')
task = json.loads(task_json)

prims = [p for p in get_default_primitives() if p.name in task.get('primitive_names', [])]
if len(prims) < 2:
    result = {{'avg_hits': 0, 'std': 1, 'best': 0, 'worst': 0, 'windows': 0, 'beats_random': False}}
    print(json.dumps(result))
    exit()

formula = FormulaGrammar.weighted_sum(prims, name=task.get('formula_name', 'test'))

# 我们需要加载历史数据——E2B沙箱需要访问data_layer
try:
    # 从父目录导入data_layer
    sys.path.insert(0, '/root/..')
    from data_layer import load_history
    draws = load_history()
except Exception as e:
    # 降级: 如果无法加载数据，使用虚拟数据
    print(f'[警告] 无法加载历史数据: {{e}}')
    # 创建虚拟数据
    draws = []

evaluator = FormulaEvaluator(random_baseline=1.09)
if draws:
    result = evaluator.evaluate(formula, draws, **task.get('eval_config', {{}}))
else:
    # 没有数据时的默认结果
    result = {{'avg_hits': 1.0, 'stable': 0.0, 'p_value': 1.0, 'beats_random': False, 'sharpe_ratio': 0.0}}

print(json.dumps(result))
"""
                sandbox.files.write('/tmp/eval.py', script)
                exec_result = sandbox.commands.run('python3 /tmp/eval.py')
                if exec_result.error:
                    raise Exception(exec_result.error)
                result_dict = json.loads(exec_result.stdout.strip())
                results.append(EvalResult(
                    task_id=task.task_id, formula_name=task.formula_name,
                    avg_hits=result_dict.get('avg_hits', 0),
                    std=result_dict.get('std', 1),
                    best=result_dict.get('max_hits', 0),
                    worst=result_dict.get('min_hits', 0),
                    windows=result_dict.get('rounds', 0),
                    beats_random=result_dict.get('beats_random', False),
                    worker_id=self.backend_name,
                ))
                sandbox.close()
            except Exception as e:
                print(f"    [E2B] 公式 {task.formula_name} 失败: {e}")
                results.append(EvalResult(
                    task_id=task.task_id, formula_name=task.formula_name,
                    avg_hits=0, std=1, best=0, worst=0, windows=0,
                    beats_random=False, worker_id=self.backend_name,
                ))

        return results


# ═══════════════════════════════════════════════════════════
# Backend: GitHub Actions
# ═══════════════════════════════════════════════════════════

class GitHubActionsBackend:
    """GitHub Actions后端 — 通过API触发workflow并行评估"""

    def __init__(self):
        self.backend_name = "gha(workflow)"
        self.available = False
        self._try_init()

    def _try_init(self):
        """检查GitHub配置"""
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPO")
        if token and repo:
            self.available = True
            print(f"  [GHABackend] 可用 (GITHUB_TOKEN + GITHUB_REPO已配置)")
        else:
            missing = []
            if not os.environ.get("GITHUB_TOKEN"):
                missing.append("GITHUB_TOKEN")
            if not os.environ.get("GITHUB_REPO"):
                missing.append("GITHUB_REPO")
            if missing:
                print(f"  [GHABackend] 不可用 (缺少环境变量: {', '.join(missing)})")

    def evaluate(self, tasks: List[EvalTask]) -> List[EvalResult]:
        if not self.available or not tasks:
            return []

        # TODO: 实际触发GitHub Actions workflow
        # 这里先返回空列表，表示功能待接入
        print(f"  [GHABackend] GitHub Actions模式已就绪，等待workflow配置")
        return []


# ═══════════════════════════════════════════════════════════
# Backend: QwenPaw (AgentScope 文件协作)
# ═══════════════════════════════════════════════════════════

class QwenPawBackend:
    """QwenPaw后端 — 通过共享文件目录与QwenPaw协作"""

    def __init__(self):
        self.backend_name = "qwenpaw(file)"
        self.available = False
        self._dist_dir = _PROJECT_ROOT / "dist"
        self._tasks_dir = self._dist_dir / "tasks"
        self._results_dir = self._dist_dir / "results"
        self._try_init()

    def _try_init(self):
        """检查共享目录是否存在"""
        try:
            self._tasks_dir.mkdir(parents=True, exist_ok=True)
            self._results_dir.mkdir(parents=True, exist_ok=True)
            # 检查是否有待处理的结果
            pending = list(self._results_dir.glob("*.json"))
            if pending:
                self.available = True
                print(f"  [QwenPawBackend] 可用 (发现 {len(pending)} 个待处理结果)")
            else:
                self.available = True  # 即使没有结果也可用（发布任务）
                print(f"  [QwenPawBackend] 可用 (共享目录就绪)")
        except Exception as e:
            print(f"  [QwenPawBackend] 不可用 ({e})")

    def evaluate(self, tasks: List[EvalTask]) -> List[EvalResult]:
        if not tasks:
            return []

        results = []

        # 发布任务到共享目录
        for task in tasks:
            task_file = self._tasks_dir / f"{task.task_id}.json"
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"  [QwenPawBackend] 已发布 {len(tasks)} 个任务到 dist/tasks/")

        # 轮询结果（最多等5分钟）
        import time as _time
        deadline = _time.time() + 300
        while _time.time() < deadline:
            found = 0
            for task in tasks:
                result_file = self._results_dir / f"{task.task_id}.json"
                if result_file.exists():
                    found += 1
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result_dict = json.load(f)
                    results.append(EvalResult.from_dict(result_dict))
            if found >= len(tasks):
                break
            _time.sleep(5)

        return results


# ═══════════════════════════════════════════════════════════
# 主调度器: 分布式评估引擎
# ═══════════════════════════════════════════════════════════

class DistributedEvaluator:
    """
    分布式评估引擎 — 统一接口，自动选择最优backend

    使用方式:
        evaluator = DistributedEvaluator()
        results = evaluator.evaluate(tasks)  # 自动选最快backend

        # 或指定backend:
        results = evaluator.evaluate(tasks, backend="local")
        results = evaluator.evaluate(tasks, backend="ray")
        results = evaluator.evaluate(tasks, backend="e2b")
    """

    BACKENDS = ["ray", "http", "e2b", "gha", "qp", "local"]  # 优先级从高到低

    def __init__(self, local_workers=None, ray_address=None, http_base_url=None,
                 enable_e2b=False, enable_gha=False, enable_qp=False):
        self.backends = {}

        # 初始化所有backend
        self.backends["local"] = LocalBackend(max_workers=local_workers)
        self.backends["ray"] = RayBackend()
        self.backends["http"] = HTTPBackend(base_url=http_base_url)
        self.backends["e2b"] = E2BBackend() if enable_e2b else None
        self.backends["gha"] = GitHubActionsBackend() if enable_gha else None
        self.backends["qp"] = QwenPawBackend() if enable_qp else None

        # 过滤掉None的backend
        self.backends = {k: v for k, v in self.backends.items() if v is not None}

        # 打印可用状态
        available = [name for name, b in self.backends.items() if b.available]
        print(f"  [DistributedEvaluator] 可用backends: {available}")
        if not available:
            print(f"  [DistributedEvaluator] ⚠ 无可用backend，将使用本地降级模式")

    def evaluate(self, tasks: List[EvalTask], backend: str = "auto") -> List[EvalResult]:
        """
        评估一组公式

        Args:
            tasks: 评估任务列表
            backend: "auto"(自动选择), "local", "ray", "http", "e2b", "gha", "qp"

        Returns:
            评估结果列表 (按avg_hits排序)
        """
        if not tasks:
            return []

        # 自动选择backend
        if backend == "auto":
            backend = self._select_best_backend()

        backend_obj = self.backends.get(backend)
        if not backend_obj or not backend_obj.available:
            # 降级到local
            print(f"  [DistributedEvaluator] Backend '{backend}'不可用，降级到local")
            backend = "local"
            backend_obj = self.backends["local"]

        print(f"\n  [DistributedEvaluator] 使用 {backend_obj.backend_name} 评估 {len(tasks)} 个公式...")
        start = time.time()

        results = backend_obj.evaluate(tasks)

        elapsed = time.time() - start
        avg_time = elapsed / len(results) * 1000 if results else 0

        print(f"  [OK] 完成 {len(results)}/{len(tasks)} 个公式 (总耗时 {elapsed:.1f}s, "
              f"平均 {avg_time:.0f}ms/公式)")

        # 按avg_hits降序排列
        results.sort(key=lambda r: -r.avg_hits)
        return results

    def _select_best_backend(self) -> str:
        """按优先级选择最佳可用backend"""
        for name in self.BACKENDS:
            if name in self.backends and self.backends[name].available:
                return name
        return "local"  # 保底

    def health_check(self) -> Dict:
        """检查所有backend健康状态"""
        status = {}
        for name, backend in self.backends.items():
            status[name] = {
                "available": backend.available,
                "backend_name": backend.backend_name,
            }
        return status


# ═══════════════════════════════════════════════════════════
# 便捷入口
# ═══════════════════════════════════════════════════════════

def run_distributed_evaluation(tasks: List[EvalTask], backend="auto") -> List[EvalResult]:
    """便捷函数: 分布式评估一组公式"""
    evaluator = DistributedEvaluator()
    return evaluator.evaluate(tasks, backend=backend)


if __name__ == "__main__":
    # 测试: 生成一些任务并评估
    print("=" * 60)
    print("  分布式评估引擎 V2.0 — 自检")
    print("=" * 60)

    evaluator = DistributedEvaluator()
    health = evaluator.health_check()
    print(f"\n  Backend健康状态:")
    for name, h in health.items():
        status = "✅" if h["available"] else "❌"
        print(f"    {status} {name}: {h['backend_name']}")

    # 生成测试任务
    from advanced_formula_developer_v3 import AdvancedFormulaDeveloper
    from data_layer import load_history

    draws = load_history()
    dev = AdvancedFormulaDeveloper(draws)
    dev._evaluate_all = lambda: None  # 跳过慢速评估
    dev.develop_formulas()

    tasks = []
    rng = __import__('random').Random()
    for r in dev.results[:10]:
        task_id = hashlib.md5(f"{r.name}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        tasks.append(EvalTask(
            task_id=task_id,
            formula_name=r.name,
            primitive_names=[p.name for p in r.primitives[:3]],
            operator=r.operator,
        ))

    print(f"\n  开始评估 {len(tasks)} 个测试任务...")
    results = evaluator.evaluate(tasks)

    print(f"\n  Top-3结果:")
    for i, r in enumerate(results[:3]):
        print(f"    {i+1}. {r.formula_name[:45]} avg={r.avg_hits:.4f} "
              f"worker={r.worker_id} time={r.elapsed_ms}ms")
