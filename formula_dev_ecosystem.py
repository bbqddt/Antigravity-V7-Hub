# -*- coding: utf-8 -*-
"""
Antigravity 公式开发生态系统 V1.0 — 统一编排入口

三大支柱整合:
1. Pillar 1: 公式语言 (Formula Language) — 原语注册、组合、变异
2. Pillar 2: 自研策略框架 (Self-Proposing Strategies) — 假设生成、验证、生命周期
3. Pillar 3: LLM驱动创新 (LLM Innovation) — Gemini原语提议、失败分析、语法演进

用法:
    from formula_dev_ecosystem import FormulaDevelopmentEcosystem

    ecosystem = FormulaDevelopmentEcosystem()

    # 运行一个开发周期
    results = ecosystem.run_cycle(n_hypotheses=100, n_generations=5)

    # 让Gemini提出新原语
    novel_prims = ecosystem.analyzer.propose_new_primitives()

    # 导出存活策略到预测引擎
    ecosystem.export_to_predictors()
"""
import sys
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import Counter, defaultdict

# Fix Windows GBK encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# ─── 项目路径 ──────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

from data_layer import load_history, Draw

# Pillar 1: Formula Language
from formula_lang.primitive import (
    Primitive, get_default_primitives, PrimitiveFactory,
    CooccurrenceAffinity, RecencyGradient, PeriodicEcho,
    SumRangeTracker, AdjacentNumberBias, TrendReversalDetector,
    PeriodicGap, RegimeSwitch, PhysicalBiasDetector,
)
from formula_lang.grammar import FormulaGrammar, Formula
from formula_lang.evaluator import FormulaEvaluator
from formula_lang.evaluator_v3 import FormulaEvaluatorV3
from formula_lang.validator import FormulaValidator
from formula_lang.mutator import PrimitiveMutator
from formula_lang.registry import PrimitiveRegistry

# Pillar 2: Strategy Proposer
from strategy_proposer.hypothesis import Hypothesis, HypothesisTemplate
from strategy_proposer.generator import HypothesisGenerator
from strategy_proposer.validator import HypothesisValidator
from strategy_proposer.registry import StrategyRegistry


# ═══════════════════════════════════════════════════════════
# 公式开发生态系统 — 主编排类
# ═══════════════════════════════════════════════════════════

class FormulaDevelopmentEcosystem:
    """
    公式开发生态系统 — 整合三大支柱的统一编排器。

    生命周期:
    1. 初始化: 加载数据、原语库、策略注册表
    2. 运行周期: 生成假设 → 验证 → 存活/淘汰 → 进化
    3. LLM创新: 让Gemini提议新原语规格
    4. 导出: 将存活策略导出到预测引擎

    属性:
        draws: 历史开奖数据
        library: 原语库 (PrimitiveLibrary)
        registry: 策略注册表 (StrategyRegistry)
        analyzer: LLM分析器 (GeminiAnalyzer)
        validator: 公式验证器 (FormulaValidator)
    """

    def __init__(self, data_path: Optional[str] = None):
        """
        初始化作生态系统的核心组件。

        Args:
            data_path: 数据文件路径 (可选，默认从data_layer加载)
        """
        self.data_path = data_path
        self.draws = load_history(data_path)
        print(f"[Ecosystem] 加载 {len(self.draws)} 期数据 ({self.draws[0].period} ~ {self.draws[-1].period})")

        # Pillar 1: 原语库 + 注册表
        self.library = self._init_library()
        self.primitive_registry = PrimitiveRegistry()
        self.mutator = PrimitiveMutator()
        self.formula_evaluator = FormulaEvaluator()
        self.formula_validator = FormulaValidator()

        # Pillar 2: 策略框架
        self.strategy_registry = StrategyRegistry()
        self.hypothesis_generator = HypothesisGenerator()
        self.hypothesis_validator = HypothesisValidator()

        # Pillar 3: LLM创新 (如果可用)
        self.analyzer = self._init_analyzer()

        # 统计
        self.cycle_count = 0
        self.total_hypotheses_generated = 0
        self.total_survived = 0
        self.total_eliminated = 0

        print(f"[Ecosystem] 初始化完成: {len(self.library)} 原语, "
              f"{len(self.strategy_registry.hypotheses)} 已有假设")

    def _init_library(self) -> List[Primitive]:
        """初始化原语库 — 使用33个默认原语"""
        return get_default_primitives()

    def _init_analyzer(self) -> Any:
        """初始化LLM分析器 — 如果Gemini不可用则返回None"""
        try:
            from llm_innovation.gemini_analyzer import GeminiAnalyzer
            analyzer = GeminiAnalyzer()
            if analyzer.client.available:
                print("[Ecosystem] Gemini分析器已激活")
                return analyzer
            else:
                print("[Ecosystem] [WARN] Gemini不可用，跳过LLM创新")
                return None
        except ImportError:
            print("[Ecosystem] [WARN] llm_innovation模块未安装，跳过LLM创新")
            return None

    # ─── 核心方法: 运行一个开发周期 ──────────────────────────

    def run_cycle(self, n_hypotheses: int = 100, n_generations: int = 5,
                  top_k: int = 5, initial_window: int = 500) -> Dict:
        """
        运行一个完整的公式开发周期。

        流程:
        1. 从数据信号生成假设
        2. 用walk-forward验证假设
        3. 存活/淘汰决策
        4. 对存活假设进行进化
        5. 记录统计

        Args:
            n_hypotheses: 生成的假设数量
            n_generations: 进化代数
            top_k: 每组预测的组数
            initial_window: 初始训练窗口大小

        Returns:
            周期结果摘要
        """
        self.cycle_count += 1
        print(f"\n{'='*60}")
        print(f"  开发周期 #{self.cycle_count}")
        print(f"{'='*60}")

        # Step 1: 生成假设
        print(f"\n[Step 1/5] 生成假设...")
        hypotheses = self._generate_hypotheses(n_hypotheses)
        print(f"  生成 {len(hypotheses)} 个新假设")
        self.total_hypotheses_generated += len(hypotheses)

        # Step 2: 注册假设
        for h in hypotheses:
            self.strategy_registry.add(h)

        # Step 3: 验证假设
        print(f"\n[Step 2/5] Walk-forward 验证...")
        validation_results = self._validate_hypotheses(hypotheses, initial_window)
        survived = [h for h in hypotheses if h.status == "survived"]
        eliminated = [h for h in hypotheses if h.status == "eliminated"]
        print(f"  存活: {len(survived)}, 淘汰: {len(eliminated)}")
        self.total_survived += len(survived)
        self.total_eliminated += len(eliminated)

        # Step 4: 进化存活假设
        print(f"\n[Step 3/5] 进化存活假设...")
        evolved = self._evolve_hypotheses(survived, n_generations, top_k, initial_window)
        print(f"  进化出 {len(evolved)} 个新假设")

        # Step 5: 评估公式性能
        print(f"\n[Step 4/5] 评估公式性能...")
        formula_results = self._evaluate_formulas(hypotheses, initial_window, top_k)

        # Step 6: 保存状态
        print(f"\n[Step 5/5] 保存状态...")
        self._save_state()

        summary = {
            "cycle": self.cycle_count,
            "hypotheses_generated": len(hypotheses),
            "survived": len(survived),
            "eliminated": len(eliminated),
            "evolved": len(evolved),
            "formula_results": formula_results,
            "timestamp": datetime.now().isoformat(),
        }

        print(f"\n[周期摘要] 生成{len(hypotheses)}假设 | "
              f"存活{len(survived)} | 淘汰{len(eliminated)} | "
              f"进化{len(evolved)}")

        return summary

    def _generate_hypotheses(self, n: int) -> List[Hypothesis]:
        """从数据信号生成假设"""
        hypotheses = self.hypothesis_generator.generate_from_signals()

        # 如果生成的不够，用模板补充
        if len(hypotheses) < n:
            templates = HypothesisTemplate.get_all_templates()
            rng = random.Random()
            for _ in range(n - len(hypotheses)):
                template = rng.choice(templates)
                params = self._random_params(template)
                h = template.fill(params)
                hypotheses.append(h)

        return hypotheses[:n]

    def _random_params(self, template: HypothesisTemplate) -> Dict:
        """为模板生成随机参数"""
        rng = random.Random()
        params = {}

        if "num" in template.template_str or "n" in template.template_str:
            params["n"] = rng.randint(1, 33)
            params["num"] = rng.randint(1, 33)
            params["num_set"] = rng.choice(["all", "hot", "cold", "structured"])

        if "pos" in template.template_str:
            params["pos"] = rng.randint(1, 6)
            params["pos_a"] = rng.randint(1, 6)
            params["pos_b"] = rng.randint(1, 6)

        if "hurst" in template.template_str:
            params["hurst"] = round(rng.uniform(0.1, 0.9), 2)
            params["hurst_range"] = "[0.1, 0.4]"

        if "window" in template.template_str:
            params["window"] = rng.choice([10, 30, 50, 100])

        if "omit" in template.template_str or "omit_days" in template.template_str:
            params["omit_threshold"] = rng.randint(5, 30)
            params["omit_days"] = rng.randint(5, 30)

        if "cooccur" in template.template_str or "cooccur_freq" in template.template_str:
            params["n_a"] = rng.randint(1, 33)
            params["n_b"] = rng.randint(1, 33)
            params["cooccur_freq"] = round(rng.uniform(0.05, 0.25), 3)
            params["expected"] = "0.09"

        if "blue" in template.template_str:
            params["blue_prev"] = rng.randint(1, 16)
            params["blue_next"] = rng.randint(1, 16)
            params["transition_prob"] = round(rng.uniform(0.05, 0.15), 3)

        if "sum_range" in template.template_str:
            params["sum_range"] = f"[{rng.randint(80, 100)}, {rng.randint(110, 130)}]"
            params["freq"] = round(rng.uniform(0.15, 0.25), 3)
            params["expected"] = "0.18"

        if "binary" in template.template_str:
            params["n"] = rng.randint(1, 33)
            params["binary_feature"] = rng.choice(["popcount", "palindrome", "leading_zeros"])

        if "corr" in template.template_str:
            params["pos_a"] = rng.randint(1, 6)
            params["pos_b"] = rng.randint(1, 6)
            params["corr_type"] = rng.choice(["positive", "negative"])
            params["corr_value"] = round(rng.uniform(0.1, 0.5), 3)

        if "range" in template.template_str:
            params["range_label"] = rng.choice(["low", "mid", "high"])
            params["range_min"] = rng.randint(1, 15)
            params["range_max"] = rng.randint(20, 33)

        if not params:
            params["n"] = rng.randint(1, 33)

        return params

    def _validate_hypotheses(self, hypotheses: List[Hypothesis],
                             initial_window: int = 500) -> Dict:
        """批量验证假设"""
        results = {}
        for h in hypotheses:
            result = self.hypothesis_validator.validate(
                h, self.draws,
                n_windows=8,
                window_size=initial_window,
                step=30,
            )
            results[h.id] = result
        return results

    def _evolve_hypotheses(self, survivors: List[Hypothesis],
                           n_generations: int = 5,
                           top_k: int = 5,
                           initial_window: int = 500) -> List[Hypothesis]:
        """进化存活假设 — 通过变异原语和重新组合"""
        evolved = []

        for survivor in survivors[:5]:  # 最多进化Top-5
            for gen in range(n_generations):
                # 变异原语
                prim = random.choice(self.library)
                mutated = self.mutator.mutate(prim, self.draws, generation=gen)

                # 创建新公式
                primitives = [mutated]
                if len(self.library) > 1:
                    other = random.choice([p for p in self.library if p.uuid != mutated.uuid])
                    primitives.append(other)

                op = random.choice(["resonance", "cascade", "phase_align", "weighted_sum"])
                try:
                    formula = getattr(FormulaGrammar, op)(primitives, name=f"evolved_{survivor.id}_gen{gen}")

                    # 评估新公式
                    eval_result = self.formula_evaluator.evaluate(
                        formula, self.draws,
                        n_windows=8,
                        window_size=initial_window,
                        step=30,
                    )

                    # 如果表现好，注册为新假设
                    if eval_result.get("avg_hits", 0) > 1.5:
                        new_h = Hypothesis(
                            template_name="evolved",
                            template_category=survivor.template_category,
                            filled_statement=f"进化自 {survivor.statement[:50]}...",
                            params={"original_id": survivor.id, "generation": gen, "avg_hits": eval_result["avg_hits"]},
                            signals={},
                            validation_method="walk_forward",
                        )
                        new_h.status = "survived"
                        new_h.result = eval_result
                        new_h.parent_ids = [survivor.id]
                        evolved.append(new_h)
                        survivor.children.append(new_h.id)
                except Exception:
                    continue

        return evolved

    def _evaluate_formulas(self, hypotheses: List[Hypothesis],
                           initial_window: int = 500,
                           top_k: int = 5) -> Dict:
        """评估假设对应的公式性能"""
        results = {}

        # 对每个存活的假设，构建并评估对应公式
        for h in hypotheses:
            if h.status != "survived":
                continue

            # 根据假设类别选择原语构建公式
            primitives = self._select_primitives_for_category(h.template_category)
            if not primitives:
                continue

            op = random.choice(["resonance", "cascade", "weighted_sum"])
            try:
                formula = getattr(FormulaGrammar, op)(primitives, name=f"formula_{h.id}")
                eval_result = self.formula_evaluator.evaluate(
                    formula, self.draws,
                    n_windows=8,
                    window_size=initial_window,
                    step=30,
                )
                results[h.id] = eval_result
            except Exception:
                continue

        return results

    def _select_primitives_for_category(self, category: str) -> List[Primitive]:
        """根据类别选择原语"""
        matching = [p for p in self.library if p.category == category]
        if not matching:
            # 回退到随机选择
            rng = random.Random()
            return rng.sample(self.library, min(3, len(self.library)))
        return matching[:3]

    def _save_state(self):
        """保存生态系统状态"""
        state = {
            "cycle_count": self.cycle_count,
            "total_hypotheses_generated": self.total_hypotheses_generated,
            "total_survived": self.total_survived,
            "total_eliminated": self.total_eliminated,
            "n_primitives": len(self.library),
            "n_hypotheses": len(self.strategy_registry.hypotheses),
            "survived_count": len(self.strategy_registry.get_survived()),
            "eliminated_count": len(self.strategy_registry.get_eliminated()),
            "last_updated": datetime.now().isoformat(),
        }

        state_path = _PROJECT_ROOT / "ecosystem_state.json"
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        # 保存策略注册表
        self.strategy_registry.save()

        # 保存原语注册表
        self.primitive_registry.save()

        print(f"  状态已保存到 {state_path}")

    # ─── LLM创新接口 ─────────────────────────────────────────

    def propose_novel_primitives(self, n_specs: int = 5) -> List[Dict]:
        """
        让Gemini提出新原语规格。

        Args:
            n_specs: 希望提出的规格数量

        Returns:
            原语规格列表
        """
        if not self.analyzer:
            print("[WARN] Gemini分析器不可用")
            return []

        specs = self.analyzer.propose_new_primitives(self.draws, n_specs=n_specs)
        print(f"[LLM] Gemini提出了 {len(specs)} 个新原语规格")
        return specs

    def review_failure_patterns(self) -> Dict:
        """
        让Gemini分析失败假设的模式。

        Returns:
            失败模式分析
        """
        if not self.analyzer:
            return {"patterns": [], "recommendations": []}

        eliminated = self.strategy_registry.get_eliminated()
        if not eliminated:
            return {"patterns": [], "recommendations": ["没有失败的假设需要分析"]}

        eliminated_dicts = [h.to_dict() for h in eliminated[:20]]  # 最多分析20个
        return self.analyzer.analyze_failure_patterns(eliminated_dicts)

    # ─── 导出接口 ────────────────────────────────────────────

    def export_to_predictors(self, output_dir: Optional[str] = None) -> Dict:
        """
        将存活策略导出到预测引擎。

        Args:
            output_dir: 输出目录

        Returns:
            导出摘要
        """
        if output_dir is None:
            output_dir = str(_PROJECT_ROOT)

        survivors = self.strategy_registry.get_survived()
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "n_survivors": len(survivors),
            "surviving_hypotheses": [h.to_dict() for h in survivors],
        }

        output_path = Path(output_dir) / "exported_strategies.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"[Export] 导出 {len(survivors)} 个存活策略到 {output_path}")

        return {
            "output_path": str(output_path),
            "n_exported": len(survivors),
        }

    # ─── 统计接口 ────────────────────────────────────────────

    def get_summary(self) -> Dict:
        """获取生态系统摘要"""
        return {
            "cycles_run": self.cycle_count,
            "data_points": len(self.draws),
            "primitives_registered": len(self.library),
            "hypotheses_total": self.total_hypotheses_generated,
            "hypotheses_survived": self.total_survived,
            "hypotheses_eliminated": self.total_eliminated,
            "strategy_registry": self.strategy_registry.summary(),
            "primitive_registry": self.primitive_registry.summary(),
            "llm_available": self.analyzer is not None,
        }


# ═══════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════

def create_ecosystem(data_path: Optional[str] = None) -> FormulaDevelopmentEcosystem:
    """工厂函数: 创建公式开发生态系统实例"""
    return FormulaDevelopmentEcosystem(data_path)


def quick_test(n_cycles: int = 3) -> Dict:
    """
    快速测试: 运行几个周期查看效果。

    Args:
        n_cycles: 运行周期数

    Returns:
        汇总结果
    """
    ecosystem = FormulaDevelopmentEcosystem()

    all_results = []
    for i in range(n_cycles):
        print(f"\n{'#'*60}")
        print(f"  Quick Test Cycle {i+1}/{n_cycles}")
        print(f"{'#'*60}")

        result = ecosystem.run_cycle(n_hypotheses=50, n_generations=3)
        all_results.append(result)

    summary = ecosystem.get_summary()
    summary["quick_test_results"] = all_results
    return summary


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="公式开发生态系统 V1.0")
    parser.add_argument("--data-file", help="CSV数据文件路径")
    parser.add_argument("--cycles", type=int, default=3, help="运行周期数")
    parser.add_argument("--n-hypotheses", type=int, default=100, help="每周期生成假设数")
    parser.add_argument("--n-generations", type=int, default=5, help="进化代数")
    parser.add_argument("--export", action="store_true", help="导出存活策略")
    parser.add_argument("--review", action="store_true", help="分析失败模式")
    parser.add_argument("--propose", type=int, default=0, help="让Gemini提出新原语规格数")
    parser.add_argument("--summary", action="store_true", help="只显示摘要")
    args = parser.parse_args()

    if args.summary:
        # 只加载并显示摘要
        eco = FormulaDevelopmentEcosystem(args.data_file)
        print(json.dumps(eco.get_summary(), indent=2, ensure_ascii=False))
    elif args.propose > 0:
        # LLM创新模式
        eco = FormulaDevelopmentEcosystem(args.data_file)
        specs = eco.propose_novel_primitives(args.propose)
        print(json.dumps(specs, indent=2, ensure_ascii=False))
    elif args.review:
        # 失败分析模式
        eco = FormulaDevelopmentEcosystem(args.data_file)
        analysis = eco.review_failure_patterns()
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    elif args.export:
        # 导出模式
        eco = FormulaDevelopmentEcosystem(args.data_file)
        eco.export_to_predictors()
    else:
        # 标准运行模式
        eco = FormulaDevelopmentEcosystem(args.data_file)
        for i in range(args.cycles):
            print(f"\n{'='*60}")
            print(f"  Cycle {i+1}/{args.cycles}")
            print(f"{'='*60}")
            eco.run_cycle(
                n_hypotheses=args.n_hypotheses,
                n_generations=args.n_generations,
            )
        print(f"\n{'='*60}")
        print("  最终摘要")
        print(f"{'='*60}")
        print(json.dumps(eco.get_summary(), indent=2, ensure_ascii=False))
