# -*- coding: utf-8 -*-
"""直接验证：预测系统 vs 随机基线"""
import sys, json, random, numpy as np
from pathlib import Path
from collections import Counter
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, "/e/享中")
from data_layer import load_history, Draw
from scipy import stats

DATA_FILE = Path("/e/享中/data/lottery_history.csv")
RANDOM_BASELINE = 1.09

def main():
    draws = load_history(str(DATA_FILE))
    print(f"数据: {len(draws)} 期 (#{draws[0].period} ~ #{draws[-1].period})\n")

    n = 500
    hot_hits, cold_hits, rand_hits = [], [], []
    formula_hits = []

    for i in range(len(draws) - n, len(draws)):
        actual = draws[i]
        train = draws[:i]
        recent = train[-50:]

        # 热号
        freq = Counter()
        for d in recent:
            freq.update(d.reds)
        hot_reds = [x for x, _ in freq.most_common(6)]
        hot_hits.append(len(set(hot_reds) & set(actual.reds)))

        # 冷号
        cold_reds = [x for x, _ in freq.most_common()[:6]]
        cold_hits.append(len(set(cold_reds) & set(actual.reds)))

        # 随机
        rand_reds = sorted(random.sample(range(1, 34), 6))
        rand_hits.append(len(set(rand_reds) & set(actual.reds)))

        # 公式: cooccurrence_affinity
        try:
            from formula_lang import get_default_primitives, FormulaGrammar
            ps = get_default_primitives()
            cooc = [p for p in ps if p.name == "cooccurrence_affinity"]
            if cooc and not formula_hits:
                f = FormulaGrammar.resonance(cooc[0])
                scores = f.evaluate_for_all_numbers(train)
                top6 = f.rank_top_6(train)
                if top6:
                    formula_hits.append(len(set(top6[:6]) & set(actual.reds)))
        except:
            pass

    print("=" * 60)
    print(f"  {'方法':<20} {'平均命中':<10} {'vs基线':<10} {'样本':<6} {'显著':<6}")
    print("  " + "-" * 52)
    print(f"  {'随机基线':<20} {RANDOM_BASELINE:<10.3f} {'-':<10} {'-':<6} {'-':<6}")
    print(f"  {'热号策略':<20} {np.mean(hot_hits):<10.3f} {np.mean(hot_hits)-RANDOM_BASELINE:+.3f}   {n:<6} ", end="")
    _, p1 = stats.ttest_rel(hot_hits, rand_hits)
    print("✓" if p1 < 0.05 else "✗")
    print(f"  {'冷号策略':<20} {np.mean(cold_hits):<10.3f} {np.mean(cold_hits)-RANDOM_BASELINE:+.3f}   {n:<6} ", end="")
    _, p2 = stats.ttest_rel(cold_hits, rand_hits)
    print("✓" if p2 < 0.05 else "✗")
    print(f"  {'随机对照':<20} {np.mean(rand_hits):<10.3f} {np.mean(rand_hits)-RANDOM_BASELINE:+.3f}   {n:<6} {'-':<6}")
    if formula_hits:
        print(f"  {'公式(cooccur)':<20} {np.mean(formula_hits):<10.3f} {np.mean(formula_hits)-RANDOM_BASELINE:+.3f}   {len(formula_hits):<6} ", end="")
        _, p3 = stats.ttest_rel(formula_hits, rand_hits[:len(formula_hits)])
        print("✓" if p3 < 0.05 else "✗")

    print("\n" + "=" * 60)
    print("  结论")
    print("=" * 60)
    print(f"""
  1. 热号策略平均命中 {np.mean(hot_hits):.3f}，与随机基线 1.09 差异仅 +{np.mean(hot_hits)-RANDOM_BASELINE:+.3f}
  2. 配对t检验 p={p1:.4f}，{'统计显著' if p1 < 0.05 else '不显著'}
  3. 冷号策略 p={p2:.4f}，{'统计显著' if p2 < 0.05 else '不显著'}

  简言之：基于历史的简单策略无法稳定超越随机。
  任何声称"显著优于随机"的结果，都需要严格的统计检验支持。
""")

if __name__ == "__main__":
    main()
