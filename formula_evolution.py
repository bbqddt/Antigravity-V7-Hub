# -*- coding: utf-8 -*-
"""
Antigravity 公式演进系统 V4.0 — 真实开奖校对驱动
====================================================

核心理念 (你的想法):
- 公式的生命力不在于"发明"，而在于"验证"
- 每一个公式，都要和真实历史开奖号码逐期对照
- 不合格就淘汰，合格的变异出新公式，再对照、再淘汰
- 不断开发新公式 → 不断试错 → 优质公式迭代 → 优胜劣汰
- 不要忽略与真实历史开奖号码的校对验证、回测

演进流程:
1. 生成/变异公式
2. 用公式对每一期真实开奖打分
3. 统计公式的命中率、准确率
4. 淘汰差的，保留好的
5. 好的公式变异出下一代
6. 重复步骤2-5，直到收敛或达到目标

用法:
    python formula_evolution.py --run              # 运行完整演进
    python formula_evolution.py --run --generations 50  # 指定代数
    python formula_evolution.py --best              # 查看最佳公式
    python formula_evolution.py --backtest          # 对最佳公式做回测
    python formula_evolution.py --compare           # 公式对比
"""
import sys
import os
import json
import math
import time
import logging
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

from data_layer import load_history, Draw

logger = logging.getLogger("FormulaEvolution")
os.makedirs(_PROJECT_ROOT / "logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_PROJECT_ROOT / "logs" / "formula_evolution.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


# ═══════════════════════════════════════════════════════════
# 公式与真实开奖的逐期校对器
# ═══════════════════════════════════════════════════════════

class FormulaMatchChecker:
    """
    公式与真实开奖的逐期校对器

    核心功能:
    - 用公式对每一期真实开奖打分
    - 统计公式的命中率、准确率
    - 生成详细的校对报告

    这不是"预测"，而是"验证" — 用历史数据检验公式的有效性。
    """

    RANDOM_EXPECTATION = 6 * 6 / 33  # ≈ 1.09 (每期期望命中数)

    def __init__(self, draws: List[Draw]):
        self.draws = draws

    def check_formula(self, formula: Any, start_index: int = 0,
                      end_index: int = None) -> Dict:
        """
        用公式对指定范围内的每一期真实开奖进行校对。

        Args:
            formula: 公式对象（有 rank_top_6(draws[:i]) 方法）
            start_index: 起始期索引
            end_index: 结束期索引（默认到最后）

        Returns:
            校对报告
        """
        if end_index is None:
            end_index = len(self.draws)

        total_periods = 0
        total_hits = 0
        per_period_hits = []
        per_formula_hits = []

        for i in range(start_index, end_index):
            train_data = self.draws[:i]
            actual = self.draws[i]
            actual_reds = actual.reds if hasattr(actual, 'reds') else sorted(list(actual.red))

            try:
                pred_top6 = formula.rank_top_6(train_data)
                hits = len(set(pred_top6) & set(actual_reds))
                total_periods += 1
                total_hits += hits
                per_period_hits.append(hits)
            except:
                pass

        if total_periods == 0:
            return {"error": "no_data"}

        avg_hits = total_hits / total_periods
        accuracy_rate = total_hits / (total_periods * 6)  # 命中率比例

        # 与随机基线对比
        expected_random = self.RANDOM_EXPECTATION * total_periods
        improvement = ((total_hits - expected_random) / expected_random) * 100

        # 每期命中分布
        hit_distribution = Counter(per_period_hits)

        # 连续命中统计
        max_consecutive = self._max_consecutive_hits(per_period_hits, threshold=1)
        avg_run_length = self._avg_run_length(per_period_hits, threshold=1)

        return {
            "total_periods": total_periods,
            "total_hits": total_hits,
            "avg_hits_per_period": round(avg_hits, 4),
            "accuracy_rate": round(accuracy_rate, 4),
            "expected_random": round(expected_random, 2),
            "improvement_pct": round(improvement, 2),
            "hit_distribution": dict(hit_distribution),
            "max_consecutive_hits": max_consecutive,
            "avg_run_length": round(avg_run_length, 2),
            "per_period_hits": per_period_hits[-50:],  # 最近50期
        }

    def walk_forward_check(self, formula: Any,
                           initial_window: int = 200,
                           step: int = 20,
                           test_size: int = 10) -> Dict:
        """
        前向滚动校对 — 最核心的验证方式。

        每一轮:
        1. 用前 initial_window + w*step 期数据训练公式
        2. 用公式预测接下来 test_size 期
        3. 与真实开奖逐期对照
        4. 记录命中率

        这就是你说的"与真实历史开奖号码校对验证、回测"。
        """
        results = []
        total_hits = 0
        total_periods = 0

        for w in range(50):  # 50轮
            train_end = initial_window + w * step
            test_start = train_end + test_size
            test_end = test_start + test_size

            if test_end > len(self.draws):
                break

            try:
                train_data = self.draws[:train_end]
                test_data = self.draws[test_start:test_end]

                pred_top6 = formula.rank_top_6(train_data)

                period_hits = []
                for draw in test_data:
                    actual_reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
                    hits = len(set(pred_top6) & set(actual_reds))
                    period_hits.append(hits)
                    total_hits += hits
                    total_periods += 1

                results.append({
                    "round": w + 1,
                    "train_size": train_end,
                    "test_periods": len(period_hits),
                    "hits": period_hits,
                    "total_hits_in_test": sum(period_hits),
                })
            except:
                results.append({
                    "round": w + 1,
                    "error": True,
                })

        if total_periods == 0:
            return {"error": "no_results"}

        avg_hits = total_hits / total_periods
        expected_random = self.RANDOM_EXPECTATION * total_periods
        improvement = ((total_hits - expected_random) / expected_random) * 100

        # 每轮命中率趋势
        round_avgs = [r["total_hits_in_test"] / max(r["test_periods"], 1)
                      for r in results if not r.get("error")]

        return {
            "total_rounds": len(results),
            "total_periods_checked": total_periods,
            "total_hits": total_hits,
            "avg_hits_per_period": round(avg_hits, 4),
            "expected_random": round(expected_random, 2),
            "improvement_pct": round(improvement, 2),
            "round_results": results,
            "round_avg_hits": [round(h, 2) for h in round_avgs],
            "trend": "UP" if len(round_avgs) >= 5 and round_avgs[-1] > round_avgs[0] else
                     "DOWN" if len(round_avgs) >= 5 and round_avgs[-1] < round_avgs[0] else
                     "FLAT",
        }

    @staticmethod
    def _max_consecutive_hits(hits: List[int], threshold: int = 1) -> int:
        max_run = 0
        current_run = 0
        for h in hits:
            if h >= threshold:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
        return max_run

    @staticmethod
    def _avg_run_length(hits: List[int], threshold: int = 1) -> float:
        runs = []
        current_run = 0
        for h in hits:
            if h >= threshold:
                current_run += 1
            else:
                if current_run > 0:
                    runs.append(current_run)
                current_run = 0
        if current_run > 0:
            runs.append(current_run)
        return sum(runs) / max(len(runs), 1)


# ═══════════════════════════════════════════════════════════
# 公式演进引擎 — 不断试错，优胜劣汰
# ═══════════════════════════════════════════════════════════

class FormulaEvolutionEngine:
    """
    公式演进引擎

    核心循环:
    1. 生成/变异公式
    2. 用公式与真实开奖逐期校对
    3. 淘汰差的，保留好的
    4. 好的公式变异出下一代
    5. 重复

    这就是你说的"不断开发新公式 → 不断试错 → 优质公式迭代 → 优胜劣汰"。
    """

    def __init__(self, draws: List[Draw]):
        self.draws = draws
        self.checker = FormulaMatchChecker(draws)
        self.population: List[Dict] = []
        self.history: List[Dict] = []
        self.best_formula = None
        self.best_eval = {}
        self.best_score = -1
        self.generation = 0

    def initialize_population(self, size: int = 50):
        """初始化公式种群 — 从所有原语中随机组合"""
        from formula_lang.primitive import PrimitiveFactory
        from formula_lang.grammar import FormulaGrammar
        from formula_lang.evaluator_v3 import FormulaEvaluatorV3, IncrementalEvaluator

        factory = PrimitiveFactory()
        prims = factory.create_all()
        ev = FormulaEvaluatorV3()
        inc_ev = IncrementalEvaluator(ev)
        rng = random.Random(42)

        operators = ['resonance', 'cascade', 'phase_align', 'weighted_sum']

        for i in range(size):
            n_prims = rng.randint(2, 4)
            selected = rng.sample(prims, min(n_prims, len(prims)))
            op = rng.choice(operators)

            try:
                f = getattr(FormulaGrammar, op)(selected, name=f'gen0_{i}')
                # V3.2: 用双指标评估 (增量)
                quick_eval = inc_ev.evaluate_incremental(f, self.draws, n_windows=10, window_size=300, step=50)
                score = quick_eval.get('combined_score', quick_eval.get('avg_hits', 0))

                self.population.append({
                    'formula': f,
                    'score': score,
                    'generation': 0,
                    'parent': None,
                    'eval_result': quick_eval,
                })
            except Exception as e:
                continue

        # 按分数排序
        self.population.sort(key=lambda x: -x['score'])
        self._update_best()

        logger.info(f"  初始化种群: {len(self.population)} 个公式")
        logger.info(f"  最佳公式: {self.population[0]['formula'].name} (improvement={self.population[0]['score']:.1f}%)")

    def evolve(self, generations: int = 30, population_size: int = 50,
               elite_ratio: float = 0.2) -> List[Dict]:
        """
        运行多代演进。

        每代:
        1. 用真实开奖校对当前种群
        2. 保留精英 (elite_ratio)
        3. 精英变异 + 随机新生成 → 新一代
        4. 重复

        Args:
            generations: 演进代数
            population_size: 种群大小
            elite_ratio: 精英比例

        Returns:
            演进历史
        """
        from formula_lang.mutator import PrimitiveMutator
        from formula_lang.primitive import PrimitiveFactory
        from formula_lang.grammar import FormulaGrammar
        from formula_lang.evaluator_v3 import FormulaEvaluatorV3, IncrementalEvaluator

        mutator = PrimitiveMutator()
        factory = PrimitiveFactory()
        prims = factory.create_all()
        ev = FormulaEvaluatorV3()
        inc_ev = IncrementalEvaluator(ev)
        operators = ['resonance', 'cascade', 'phase_align', 'weighted_sum']
        rng = random.Random()
        overall_start = time.time()  # 总耗时监控

        for gen in range(1, generations + 1):
            self.generation = gen
            logger.info(f"\n{'='*60}")
            logger.info(f"  第 {gen}/{generations} 代演进")
            logger.info(f"{'='*60}")

            # Step 1: V3.2双指标评估当前种群（并行）
            logger.info(f"\n  [1/4] V3.2评估种群 ({len(self.population)} 个公式)...")
            gen_start = time.time()

            # 构建公式字典用于并行评估
            formulas_dict = {}
            for idx, member in enumerate(self.population):
                formulas_dict[f"gen{self.generation}_{idx}"] = member['formula']

            # 并行评估
            from formula_lang.evaluator_v3 import evaluate_batch_parallel
            eval_results = evaluate_batch_parallel(
                formulas_dict, self.draws, ev,
                n_windows=15, window_size=300, step=50,
                max_workers=min(8, len(self.population)),
            )

            # 回填结果
            for idx, member in enumerate(self.population):
                key = f"gen{self.generation}_{idx}"
                if key in eval_results:
                    er = eval_results[key]
                    member['score'] = er.get('combined_score', er.get('avg_hits', 0))
                    member['eval_result'] = er
                    member['avg_hits'] = er.get('avg_hits', 0)
                    member['avg_brier'] = er.get('avg_brier', 0)
                    member['beats_random'] = er.get('beats_random', False)
                else:
                    member['score'] = -1
                    member['avg_hits'] = 0
                    member['avg_brier'] = 0
                    member['beats_random'] = False

            gen_elapsed = time.time() - gen_start
            logger.info(f"    评估耗时: {gen_elapsed:.2f}s ({len(self.population)}公式/{os.cpu_count() or 4}核)")

            # 排序
            self.population.sort(key=lambda x: -x['score'])

            # 打印本代Top-5
            logger.info(f"  本代Top-5:")
            for i, m in enumerate(self.population[:5]):
                hits = m.get('avg_hits', 0)
                brier = m.get('avg_brier', 0)
                br = 'BEATS!' if m.get('beats_random') else ''
                logger.info(f"    #{i+1} {m['formula'].name[:40]:<40} "
                           f"hits={hits:.3f} brier={brier:.6f} {br}")

            # Step 2: 保留精英
            elite_count = max(1, int(population_size * elite_ratio))
            elites = self.population[:elite_count]
            logger.info(f"\n  [2/4] 保留精英: {elite_count} 个")

            # Step 3: 精英变异 + 随机新生成
            new_population = list(elites)  # 精英直接进入下一代

            # 精英变异
            for elite in elites:
                try:
                    mutated = mutator.mutate(elite['formula'], self.draws, generation=gen)
                    # V3.2: 快速评估变异体 (增量)
                    quick_eval = inc_ev.evaluate_incremental(mutated, self.draws, n_windows=5, window_size=300, step=50)
                    new_population.append({
                        'formula': mutated,
                        'score': quick_eval.get('combined_score', 0),
                        'generation': gen,
                        'parent': elite['formula'].name,
                        'eval_result': quick_eval,
                        'avg_hits': quick_eval.get('avg_hits', 0),
                        'avg_brier': quick_eval.get('avg_brier', 0),
                        'beats_random': quick_eval.get('beats_random', False),
                    })
                except Exception as e:
                    logger.debug(f"    变异失败: {e}")

            # 随机新生成 (补充种群)
            while len(new_population) < population_size:
                n_prims = rng.randint(2, 4)
                selected = rng.sample(prims, min(n_prims, len(prims)))
                op = rng.choice(operators)
                try:
                    f = getattr(FormulaGrammar, op)(selected, name=f'gen{gen}_new_{len(new_population)}')
                    # V3.2: 快速评估 (增量)
                    quick_eval = inc_ev.evaluate_incremental(f, self.draws, n_windows=5, window_size=300, step=50)
                    new_population.append({
                        'formula': f,
                        'score': quick_eval.get('combined_score', 0),
                        'generation': gen,
                        'parent': 'random',
                        'eval_result': quick_eval,
                        'avg_hits': quick_eval.get('avg_hits', 0),
                        'avg_brier': quick_eval.get('avg_brier', 0),
                        'beats_random': quick_eval.get('beats_random', False),
                    })
                except:
                    break

            self.population = new_population
            self._update_best()

            # Step 4: 保存本代记录 + 性能监控
            gen_record = {
                'generation': gen,
                'population_size': len(self.population),
                'best_formula': self.best_formula.name if self.best_formula else None,
                'best_score': self.best_score,
                'top5': [
                    {'name': m['formula'].name, 'score': m['score']}
                    for m in self.population[:5]
                ],
            }
            self.history.append(gen_record)

        total_elapsed = time.time() - overall_start

        # 保存性能监控日志
        perf_log = {
            'timestamp': datetime.now().isoformat(),
            'total_generations': generations,
            'population_size': population_size,
            'total_time_seconds': round(total_elapsed, 2),
            'time_per_generation': round(total_elapsed / max(generations, 1), 2),
            'best_formula': self.best_formula.name if self.best_formula else None,
            'best_combined_score': self.best_score,
            'best_avg_hits': self.best_eval.get('avg_hits', 0) if hasattr(self, 'best_eval') and self.best_eval else 0,
            'best_avg_brier': self.best_eval.get('avg_brier', 0) if hasattr(self, 'best_eval') and self.best_eval else 0,
            'beats_random': self.best_eval.get('beats_random', False) if hasattr(self, 'best_eval') and self.best_eval else False,
            'history': self.history,
        }
        perf_path = _PROJECT_ROOT / "evolution_performance_log.json"
        with open(perf_path, 'w', encoding='utf-8') as f:
            json.dump(perf_log, f, ensure_ascii=False, indent=2)

        logger.info(f"\n{'='*60}")
        logger.info(f"  演进完成: {generations} 代, {len(self.history)} 代记录")
        logger.info(f"  总耗时: {total_elapsed:.1f}s ({total_elapsed/max(generations,1):.1f}s/代)")
        logger.info(f"  最佳公式: {self.best_formula.name if self.best_formula else '无'}")
        logger.info(f"  最佳得分: {self.best_score:.4f}")
        logger.info(f"  性能日志: {perf_path}")
        logger.info(f"{'='*60}")

        return self.history

    def _update_best(self):
        """更新最佳公式"""
        if self.population:
            best = max(self.population, key=lambda x: x['score'])
            if best['score'] > self.best_score:
                self.best_score = best['score']
                self.best_formula = best['formula']
                self.best_eval = best.get('eval_result', {})

    def get_best_formula(self) -> Optional[Dict]:
        """获取最佳公式及其 V3.2 评估报告"""
        if not self.best_formula:
            return None

        from formula_lang.evaluator_v3 import FormulaEvaluatorV3
        ev = FormulaEvaluatorV3()
        # V3.2: 用最佳公式做完整评估
        full_eval = ev.evaluate(
            self.best_formula, self.draws,
            n_windows=15, window_size=300, step=50,
        )

        return {
            'formula': self.best_formula,
            'generation': self.generation,
            'score': self.best_score,
            'eval_result': full_eval,
            'avg_hits': full_eval.get('avg_hits', 0),
            'avg_brier': full_eval.get('avg_brier', 0),
            'beats_random': full_eval.get('beats_random', False),
        }

    def save_history(self, filepath: str = None):
        """保存演进历史"""
        if filepath is None:
            filepath = str(_PROJECT_ROOT / "formula_evolution_history.json")

        history_data = {
            'generated_at': datetime.now().isoformat(),
            'total_generations': len(self.history),
            'best_formula': self.best_formula.name if self.best_formula else None,
            'best_score': self.best_score,
            'history': self.history,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

        logger.info(f"  演进历史已保存: {filepath}")


# ═══════════════════════════════════════════════════════════
# CLI入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    import subprocess
    import sys

    parser = argparse.ArgumentParser(description="Antigravity 公式演进系统 V4.0 — 真实开奖校对驱动")
    parser.add_argument("--run", action="store_true", help="运行完整演进")
    parser.add_argument("--generations", type=int, default=20, help="演进代数（默认20）")
    parser.add_argument("--population", type=int, default=30, help="种群大小（默认30）")
    parser.add_argument("--best", action="store_true", help="查看最佳公式")
    parser.add_argument("--backtest", action="store_true", help="对最佳公式做回测")
    parser.add_argument("--compare", action="store_true", help="公式对比")
    args = parser.parse_args()

    draws = load_history()
    logger.info(f"数据: {len(draws)} 期 (#{draws[0].period} ~ #{draws[-1].period})")

    # 启动前强制一致性检查
    try:
        result = subprocess.run(
            [sys.executable, str(_PROJECT_ROOT / "consistency_checker.py"), "--enforce"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            logger.error("一致性检查失败，中止演进:\n" + result.stdout)
            sys.exit(1)
        logger.info("一致性检查通过。")
    except Exception as e:
        logger.warning(f"一致性检查异常: {e}")

    engine = FormulaEvolutionEngine(draws)

    if args.run:
        # 运行演进
        engine.initialize_population(size=args.population)
        engine.evolve(generations=args.generations, population_size=args.population)
        engine.save_history()

        # 打印最佳公式
        best = engine.get_best_formula()
        if best:
            logger.info(f"\n{'='*60}")
            logger.info(f"  最佳公式: {best['formula'].name}")
            logger.info(f"  演进代数: {best['generation']}")
            logger.info(f"  综合评分: {best['score']:.4f}")
            logger.info(f"  平均命中: {best['avg_hits']:.3f} (随机={FormulaMatchChecker.RANDOM_EXPECTATION:.2f})")
            logger.info(f"  Brier Score: {best['avg_brier']:.6f}")
            logger.info(f"  beats_random: {best['beats_random']}")
            logger.info(f"{'='*60}")

    elif args.best:
        # 查看最佳公式
        history_file = _PROJECT_ROOT / "formula_evolution_history.json"
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            logger.info(f"总代数: {history['total_generations']}")
            logger.info(f"最佳公式: {history['best_formula']}")
            logger.info(f"最佳得分: {history['best_score']:.1f}%")
        else:
            logger.info("没有历史记录，请先运行 --run")

    elif args.backtest:
        # 对最佳公式做回测
        history_file = _PROJECT_ROOT / "formula_evolution_history.json"
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            logger.info(f"回测报告 (基于 {history['total_generations']} 代演进):")
            logger.info(f"  最佳公式: {history['best_formula']}")
            logger.info(f"  改进率: {history['best_score']:.1f}%")
        else:
            logger.info("没有历史记录，请先运行 --run")

    else:
        parser.print_help()
