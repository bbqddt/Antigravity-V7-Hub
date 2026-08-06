# -*- coding: utf-8 -*-
"""
Antigravity 云端并行演进框架 V3.0 — 多后端分布式集成版

核心理念:
1. 公式生成 → 分布式并行评估 → 优胜劣汰 → 再循环
2. 统一调度: Local > Ray > HTTP > E2B > GitHub Actions > QwenPaw
3. 守护进程接管，7x24不间断运行
4. 零配置启动 + 故障自动降级

架构:
┌───────────────────────────────────────────────────────────────────┐
│              ParallelOrchestrator (Master)                        │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │           DistributedEvaluator (统一调度层)                  │  │
│  │                                                             │  │
│  │  ray(32核CVM) → http(API) → e2b(沙箱) → gha(actions)       │  │
│  │  qp(file) → local(本机多核)                                 │  │
│  │                                                             │  │
│  │  auto → 按优先级探测可用backend → 失败则降级                 │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                      │                                            │
│              自动故障降级 ↕                                        │
└───────────────────────────────────────────────────────────────────┘

每轮演进:
1. AdvancedFormulaDeveloper生成新公式 (本地)
2. DistributedEvaluator分发任务到最优backend并行评估
3. 结果汇总排序 → 决定去留
4. 更新金库 → 保存cycle记录
5. 等待下一轮
"""
import json
import time
import sys
import os
import hashlib
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 导入分布式评估引擎 — 唯一任务/结果定义来源
from distributed_evaluator import (
    DistributedEvaluator,
    EvalTask,
    EvalResult,
    _evaluate_single_task,
)

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════
# 并行调度器 — Master端
# ═══════════════════════════════════════════════════════════

class ParallelOrchestrator:
    """并行演进调度器 — 本地Master，分布式Worker池"""

    def __init__(self, max_workers=None, use_ray=False, use_http=False,
                 use_e2b=False, use_gha=False, use_qp=False):
        self.project_root = _PROJECT_ROOT
        self.vault_path = self.project_root / "formula_vault.json"

        # 分布式评估引擎 — 统一调度所有backend
        ray_addr = os.environ.get("RAY_CVM_IP", None) if use_ray else None
        http_url = os.environ.get("EVAL_API_URL", None) if use_http else None
        self.evaluator = DistributedEvaluator(
            local_workers=max_workers,
            ray_address=ray_addr,
            http_base_url=http_url,
            enable_e2b=use_e2b,
            enable_gha=use_gha,
            enable_qp=use_qp,
        )

        # 状态
        self.cycle_count = self._get_cycle_count()

    def run_evolution_cycle(self, n_formulas=20) -> Dict:
        """运行一轮完整演进"""
        self.cycle_count += 1
        print(f"\n{'='*70}")
        print(f"  并行演进 — 第 {self.cycle_count} 轮")
        print(f"  生成 {n_formulas} 个新公式 → 分布式并行评估")
        print(f"  时间: {datetime.now().isoformat()}")
        print(f"{'='*70}")

        start_time = time.time()

        # 1. 生成新公式
        print(f"\n  [1/3] 生成新公式...")
        tasks = self._generate_tasks(n_formulas)
        print(f"    生成了 {len(tasks)} 个公式任务")

        if not tasks:
            print(f"    ⚠ 未生成任何有效任务，跳过本轮")
            return {'cycle': self.cycle_count, 'error': 'no_tasks'}

        # 2. 分布式并行评估
        print(f"\n  [2/3] 并行评估 {len(tasks)} 个公式...")
        results = self.evaluator.evaluate(tasks, backend="auto")
        print(f"    评估完成 (耗时 {time.time()-start_time:.1f}s)")

        # 3. 排序和筛选
        print(f"\n  [3/3] 排序和筛选...")
        results.sort(key=lambda r: -r.avg_hits)

        top = results[:5]
        beats_random = sum(1 for r in results if r.beats_random)

        print(f"    Top-5:")
        for i, r in enumerate(top):
            print(f"      {i+1}. {r.formula_name[:45]} avg={r.avg_hits:.4f} "
                  f"sharpe={r.sharpe_ratio:.4f} ({r.elapsed_ms}ms, {r.worker_id})")

        print(f"    超越随机基线: {beats_random}/{len(results)}")

        # 4. 更新金库
        elapsed = time.time() - start_time
        self._update_vault(results)

        cycle_result = {
            'cycle': self.cycle_count,
            'timestamp': datetime.now().isoformat(),
            'elapsed_seconds': round(elapsed, 2),
            'tasks_generated': len(tasks),
            'tasks_completed': len(results),
            'beats_random': beats_random,
            'top_formula': results[0].formula_name if results else None,
            'top_avg_hits': results[0].avg_hits if results else 0,
            'backend_used': self.evaluator._select_best_backend(),
        }

        # 保存本轮结果
        cycle_path = self.project_root / f"parallel_evolution_cycle_{self.cycle_count:04d}.json"
        with open(cycle_path, 'w', encoding='utf-8') as f:
            json.dump(cycle_result, f, ensure_ascii=False, indent=2)

        print(f"\n  [OK] 本轮完成 — 耗时 {elapsed:.1f}s")
        print(f"  [OK] 结果已保存到 {cycle_path.name}")

        return cycle_result

    def _generate_tasks(self, n: int) -> List[EvalTask]:
        """从金库active公式出发，变异生成新任务"""
        from advanced_formula_developer_v3 import AdvancedFormulaDeveloper
        from data_layer import load_history

        draws = load_history()
        dev = AdvancedFormulaDeveloper(draws)

        # No monkey-patch: evaluation is fast (0.01s/formula), no need to skip
        new_results = dev.develop_formulas()

        # 转换为EvalTask — 从各策略均匀采样，避免只选resonance公式
        tasks = []
        rng = __import__('random').Random()

        # 按operator分组
        by_op = {}
        for r in new_results:
            op = r.operator if r.operator else 'unknown'
            if op not in by_op:
                by_op[op] = []
            by_op[op].append(r)

        # 从每组取n/组数+余数分配
        ops_list = list(by_op.keys())
        per_op = max(1, n // len(ops_list))
        extra = n - per_op * len(ops_list)

        for i, op in enumerate(ops_list):
            count = per_op + (1 if i < extra else 0)
            pool = by_op[op][:min(len(by_op[op]), count * 2)]
            selected = rng.sample(pool, min(count, len(pool)))
            for result in selected:
                prims = result.primitives if len(result.primitives) >= 2 else \
                        result.primitives[:1] + [p for p in dev.all_primitives
                                                  if p.name not in [pp.name for pp in result.primitives]][:1]

                if len(prims) < 2:
                    continue

                task_id = hashlib.md5(
                    f"{result.name}_{datetime.now().isoformat()}_{rng.random()}".encode()
                ).hexdigest()[:12]

                tasks.append(EvalTask(
                    task_id=task_id,
                    formula_name=result.name,
                    primitive_names=[p.name for p in prims],
                    operator=result.operator,
                    parameters={},
                ))

        # 如果还不够，从剩余补充
        if len(tasks) < n:
            remaining = [r for r in new_results if r not in tasks]
            for r in remaining[:n - len(tasks)]:
                prims = r.primitives if len(r.primitives) >= 2 else []
                if len(prims) >= 2:
                    task_id = hashlib.md5(
                        f"{r.name}_{datetime.now().isoformat()}_{rng.random()}".encode()
                    ).hexdigest()[:12]
                    tasks.append(EvalTask(
                        task_id=task_id,
                        formula_name=r.name,
                        primitive_names=[p.name for p in prims],
                        operator=r.operator,
                        parameters={},
                    ))

        return tasks[:n]

    def _update_vault(self, results: List[EvalResult]):
        """用评估结果更新金库"""
        vault = json.load(open(self.vault_path, 'r', encoding='utf-8'))
        formulas = vault.get('formulas', {})

        for result in results[:10]:  # Top-10考虑入库
            if result.avg_hits > 1.05:  # 至少高于随机基线
                if result.formula_name not in formulas:
                    entry = {
                        'name': result.formula_name,
                        'primitives': [],
                        'operator': 'unknown',
                        'avg_hits': result.avg_hits,
                        'test_avg': result.avg_hits,
                        'stable': round(result.avg_hits - result.std, 4),
                        'beats_random': result.beats_random,
                        'composite_score': result.composite_score,
                        'sharpe_ratio': result.sharpe_ratio,
                        'generation': self.cycle_count,
                        'born_at': datetime.now().isoformat(),
                        'status': 'active',
                        'win_rate': 0.0,
                    }
                    formulas[result.formula_name] = entry

        vault['formulas'] = formulas
        vault['updated_at'] = datetime.now().isoformat()
        vault['version'] = '4.0'
        vault['total_formulas'] = len(formulas)
        vault['active'] = sum(1 for f in formulas.values() if f.get('status') == 'active')
        vault['bench'] = sum(1 for f in formulas.values() if f.get('status') == 'bench')
        vault['eliminated'] = sum(1 for f in formulas.values() if f.get('status') == 'eliminated')

        with open(self.vault_path, 'w', encoding='utf-8') as f:
            json.dump(vault, f, ensure_ascii=False, indent=2)

    def _get_cycle_count(self) -> int:
        count = 0
        for f in self.project_root.glob('parallel_evolution_cycle_*.json'):
            try:
                n = int(f.stem.split('_')[-1])
                count = max(count, n)
            except:
                pass
        return count

    def run_forever(self, interval_minutes=10, max_cycles=None):
        """持续运行 — 守护模式"""
        print("=" * 70)
        print(f"  并行演进守护进程启动")
        available = [n for n, b in self.evaluator.backends.items() if b.available]
        print(f"  可用Backend: {available}")
        print(f"  运行间隔: {interval_minutes} 分钟")
        print(f"  按 Ctrl+C 停止")
        print("=" * 70)

        running = True

        def handle_signal(signum, frame):
            nonlocal running
            print(f"\n[守护进程] 收到信号 {signum}，准备退出...")
            running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        cycle = 0
        while running:
            cycle += 1
            try:
                result = self.run_evolution_cycle()
                if max_cycles and cycle >= max_cycles:
                    print(f"\n  [守护进程] 已达到最大轮次 {max_cycles}，退出")
                    break
            except Exception as e:
                print(f"\n  [守护进程] 错误: {e}")
                import traceback
                traceback.print_exc()

            if running:
                wait_seconds = interval_minutes * 60
                print(f"\n  [守护进程] 下次演进将在 {interval_minutes} 分钟后启动...")

                for remaining in range(wait_seconds, 0, -60):
                    if not running:
                        break
                    if remaining % 3600 == 0:
                        mins = remaining // 60
                        print(f"    剩余: {mins} 分钟")
                    time.sleep(60)

        print(f"\n  [守护进程] 已停止。共运行 {cycle} 次循环。")


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity 分布式并行演进调度器 V3.0")
    parser.add_argument("--cycles", type=int, default=1, help="运行N轮")
    parser.add_argument("--workers", type=int, default=None,
                        help="本地Worker数量(自动=CPU-2)")
    parser.add_argument("--ray", action="store_true",
                        help="启用Ray远程Worker(需配置RAY_CVM_IP)")
    parser.add_argument("--http", action="store_true",
                        help="启用HTTP远程Worker(需配置EVAL_API_URL)")
    parser.add_argument("--e2b", action="store_true",
                        help="启用E2B沙箱Worker(需配置E2B_API_KEY)")
    parser.add_argument("--gha", action="store_true",
                        help="启用GitHub Actions Worker(需配置GITHUB_TOKEN/GITHUB_REPO)")
    parser.add_argument("--qp", action="store_true",
                        help="启用QwenPaw文件协作Worker(需配置共享目录)")
    parser.add_argument("--daemon", action="store_true",
                        help="守护模式(持续运行)")
    parser.add_argument("--interval", type=int, default=10,
                        help="守护模式间隔(分钟)")
    parser.add_argument("--max-cycles", type=int, default=None,
                        help="守护模式下最大轮次")
    parser.add_argument("--tasks", type=int, default=20,
                        help="每轮生成N个公式")
    args = parser.parse_args()

    orchestrator = ParallelOrchestrator(
        max_workers=args.workers,
        use_ray=args.ray,
        use_http=args.http,
        use_e2b=args.e2b,
        use_gha=args.gha,
        use_qp=args.qp,
    )

    if args.daemon:
        orchestrator.run_forever(
            interval_minutes=args.interval,
            max_cycles=args.max_cycles,
        )
    else:
        for _ in range(args.cycles):
            result = orchestrator.run_evolution_cycle(n_formulas=args.tasks)
            print(f"\n  本轮摘要: {json.dumps(result, ensure_ascii=False)}")

        print(f"\n{'='*70}")
        print(f"  全部 {args.cycles} 轮完成")
        print(f"{'='*70}")
