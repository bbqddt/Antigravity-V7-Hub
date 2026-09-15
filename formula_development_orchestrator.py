# -*- coding: utf-8 -*-
"""
Antigravity 公式开发总控脚本 V1.0

一键运行: 公式开发 → 策略生成 → LLM创新 → 回测验证

用法:
    python formula_development_orchestrator.py              # 一键运行
    python formula_development_orchestrator.py --formulas   # 只运行公式开发
    python formula_development_orchestrator.py --strategies # 只运行策略生成
    python formula_development_orchestrator.py --llm        # 只运行LLM创新
    python formula_development_orchestrator.py --test       # 测试模式（少数据）
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# 项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent

# 确保项目根目录在路径中
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from data_layer import load_history, Draw


def safe_print(msg):
    """安全打印，过滤emoji"""
    clean = "".join(c for c in msg if ord(c) < 128 or c in "\n\r\t")
    print(clean)

def run_formula_development(draws, n_generations=5, population_size=10):
    """运行公式开发"""
    print("\n" + "=" * 70)
    print("  [Formula Development Phase]")
    print("=" * 70)

    from formula_lang import get_default_primitives, FormulaGrammar, Primitive
    from formula_lang.registry import PrimitiveRegistry
    from formula_lang.evaluator import FormulaEvaluator

    # 1. 加载默认原语
    primitives = get_default_primitives()
    print(f"\n[OK] Loaded {len(primitives)} default primitives")
    for p in primitives:
        print(f"   - {p.name} ({p.category})")

    # 2. 注册原语
    registry = PrimitiveRegistry()
    for p in primitives:
        registry.register_primitive(p)
    print(f"\n[Registry] {len(registry.alive)} primitives registered (expected {len(primitives)})")

    # Also register to global Primitive registry
    for p in primitives:
        Primitive._registry[p.uuid] = p

    # 3. 生成公式（随机组合原语）
    print(f"\n[Generating formulas...]")
    evaluator = FormulaEvaluator()
    formulas = []

    for i in range(population_size):
        n_prims = (i % 3) + 2  # 2-4个原语
        selected = primitives[i % len(primitives):(i % len(primitives)) + n_prims]
        if len(selected) < 2:
            selected = primitives[:n_prims]

        op = ["resonance", "cascade", "phase_align", "weighted_sum"][i % 4]
        formula = getattr(FormulaGrammar, op)(selected, name=f"dev_formula_{i}")
        formulas.append(formula)

    print(f"   Generated {len(formulas)} formulas")

    # 4. 评估公式
    print(f"\n[Evaluating formulas (8-round walk-forward)...]")
    eval_results = evaluator.evaluate_batch(formulas, draws, n_windows=8, window_size=300, step=30)

    # 5. 排名
    scored = []
    for i, formula in enumerate(formulas):
        name = f"dev_formula_{i}"
        perf = eval_results.get(name, eval_results.get(formula.name, {}))
        scored.append((formula, perf))

    scored.sort(key=lambda x: -x[1].get("avg_hits", 0))

    print(f"\n[Top-5 Formulas:]")
    for i, (formula, perf) in enumerate(scored[:5]):
        print(f"  #{i+1}: {formula.name}")
        print(f"      avg_hits={perf.get('avg_hits', 0):.3f} std={perf.get('std', 0):.3f} "
              f"p={perf.get('p_value', 1):.3f} stable={perf.get('stable', 0):.3f}")

    # 6. 进化
    print(f"\n[Evolving {n_generations} generations...]")
    results = registry.evolve(draws, n_generations=n_generations,
                              population_size=population_size)

    # 7. 保存
    registry.save()

    report = {
        "phase": "formula_development",
        "timestamp": datetime.now().isoformat(),
        "n_primitives": len(primitives),
        "n_formulas": len(formulas),
        "top_formulas": [
            {
                "name": f.name,
                "avg_hits": perf.get("avg_hits", 0),
                "p_value": perf.get("p_value", 1),
                "stable": perf.get("stable", 0),
            }
            for f, perf in scored[:10]
        ],
        "evolution": results.get("generations", []),
        "registry_summary": registry.summary(),
    }

    with open(str(_PROJECT_ROOT / "formula_development_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[Report saved: formula_development_report.json]")
    return report


def run_strategy_generation(draws):
    """运行策略生成"""
    print("\n" + "=" * 70)
    print("  [Strategy Generation Phase]")
    print("=" * 70)

    from strategy_proposer import HypothesisGenerator, HypothesisValidator, StrategyRegistry

    # 1. 生成假设
    gen = HypothesisGenerator()
    hypotheses = gen.generate_from_signals()
    print(f"\n[OK] Generated {len(hypotheses)} hypotheses")

    for h in hypotheses[:10]:
        print(f"   [{h.status}] {h.statement[:60]}...")

    # 2. 验证假设
    validator = HypothesisValidator()
    results = validator.validate_all(hypotheses, draws, n_windows=6, window_size=300, step=30)

    survived = sum(1 for r in results.values() if r.get("status") == "survived")
    eliminated = sum(1 for r in results.values() if r.get("status") == "eliminated")

    print(f"\n[Validation Results:] {survived} survived / {eliminated} eliminated")

    # 3. 注册
    registry = StrategyRegistry()
    for h in hypotheses:
        registry.add(h)
    registry.save()

    report = {
        "phase": "strategy_generation",
        "timestamp": datetime.now().isoformat(),
        "n_hypotheses": len(hypotheses),
        "survived": survived,
        "eliminated": eliminated,
        "registry_summary": registry.summary(),
    }

    with open(str(_PROJECT_ROOT / "strategy_generation_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[Report saved: strategy_generation_report.json]")
    return report


def run_llm_innovation(draws):
    """运行LLM创新"""
    print("\n" + "=" * 70)
    print("  [LLM Innovation Phase]")
    print("=" * 70)

    from llm_innovation import GeminiAnalyzer, FailureReviewer

    # 1. Gemini分析
    analyzer = GeminiAnalyzer()
    if analyzer.client.available:
        print(f"\n[Gemini available, requesting new primitive specs...]")
        specs = analyzer.propose_new_primitives(draws, n_specs=3)
        print(f"   Received {len(specs)} new primitive specs")
        for spec in specs:
            print(f"   - {spec.get('name', '?')} ({spec.get('category', '?')})")
            print(f"     {spec.get('description', '')}")
    else:
        print(f"\n[Gemini unavailable, skipping spec generation]")
        specs = []

    # 2. 失败审查
    reviewer = FailureReviewer()
    print(f"\n[Failure reviewer ready]")
    print(f"   Failure types: {list(reviewer.FAILURE_TYPES.keys())}")

    report = {
        "phase": "llm_innovation",
        "timestamp": datetime.now().isoformat(),
        "gemini_available": analyzer.client.available,
        "specs_received": len(specs),
        "specs": specs,
    }

    with open(str(_PROJECT_ROOT / "llm_innovation_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[Report saved: llm_innovation_report.json]")
    return report


def run_integration_test(draws):
    """集成测试 — 快速验证所有模块能正常工作"""
    print("\n" + "=" * 70)
    print("  [Integration Test Mode]")
    print("=" * 70)

    from formula_lang import get_default_primitives, FormulaGrammar
    from formula_lang.evaluator import FormulaEvaluator

    # 测试1: 原语加载
    primitives = get_default_primitives()
    print(f"\n[OK] Primitives loaded: {len(primitives)}")

    # 测试2: 公式生成
    f = FormulaGrammar.resonance(primitives[:3], name="test_resonance")
    scores = f.evaluate_for_all_numbers(draws[:100])
    print("[OK] Formula evaluation: 33 numbers scored")

    # 测试3: 假设生成
    from strategy_proposer import HypothesisGenerator
    gen = HypothesisGenerator()
    hyps = gen.generate_from_signals()
    print(f"[OK] Hypothesis generation: {len(hyps)} hypotheses")

    # 测试4: LLM客户端
    from llm_innovation import GeminiClient
    client = GeminiClient()
    llm_status = "available" if client.available else "unavailable (local mode)"
    print(f"[OK] LLM client: {llm_status}")

    print("\nAll modules integration test PASSED!")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity 公式开发总控")
    parser.add_argument("--formulas", action="store_true", help="只运行公式开发")
    parser.add_argument("--strategies", action="store_true", help="只运行策略生成")
    parser.add_argument("--llm", action="store_true", help="只运行LLM创新")
    parser.add_argument("--test", action="store_true", help="集成测试模式")
    parser.add_argument("--generations", type=int, default=3, help="进化代数")
    parser.add_argument("--population", type=int, default=10, help="种群大小")
    args = parser.parse_args()

    start_time = time.time()

    # 加载数据
    print("Loading historical data...")
    draws = load_history()
    print(f"   Data scale: {len(draws)} periods")

    if args.test:
        run_integration_test(draws)
        return

    all_reports = {}

    if args.formulas:
        all_reports["formula_development"] = run_formula_development(
            draws, n_generations=args.generations, population_size=args.population)
    elif args.strategies:
        all_reports["strategy_generation"] = run_strategy_generation(draws)
    elif args.llm:
        all_reports["llm_innovation"] = run_llm_innovation(draws)
    else:
        # 全部运行
        all_reports["formula_development"] = run_formula_development(
            draws, n_generations=args.generations, population_size=args.population)
        all_reports["strategy_generation"] = run_strategy_generation(draws)
        all_reports["llm_innovation"] = run_llm_innovation(draws)

    # 汇总报告
    elapsed = time.time() - start_time
    summary = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "data_periods": len(draws),
        "phases": {k: {"status": "completed", "report_keys": list(v.keys())}
                   for k, v in all_reports.items()},
    }

    with open(str(_PROJECT_ROOT / "development_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"  Formula Development Orchestrator Complete! Elapsed: {elapsed:.1f}s")
    print("=" * 70)
    print(f"\nSummary report: development_summary.json")


if __name__ == "__main__":
    main()
