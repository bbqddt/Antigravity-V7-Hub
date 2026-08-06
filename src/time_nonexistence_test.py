# -*- coding: utf-8 -*-
"""
Antigravity 时间不存在检验协议 V0.2 — 证伪"时间存在"假设

核心哲学:
- 不假设"双色球有规律"
- 不假设"双色球是随机的"
- 而是设计实验，让数据自己告诉我们答案

如果时间存在:
1. 序列应该有方向性（过去→未来，不是反过来）
2. 序列应该是马尔可夫的（未来只依赖现在）
3. 统计特性应该随时间演化（均值、方差在漂移）
4. 更多数据应该降低不确定性（复杂度下降）
5. 因果关系应该有方向性

如果时间不存在:
1. 正向序列 = 反向序列（前后对称）
2. 长记忆（ACF 不快速衰减）
3. 统计特性恒定（无漂移）
4. 复杂度恒定（信息不随数据量变化）
5. 因果关系双向

我们不是要"证明时间不存在"。
我们是要**证伪"时间存在"这个假设**。
如果假设通过所有检验 → 数据是随机的，公式无用。
如果假设被证伪 → 数据有结构，公式可能有用。

这就是科学方法。
"""
import numpy as np
import pandas as pd
import json
import math
from pathlib import Path
from collections import Counter
from datetime import datetime
from data_layer import load_history

_PROJECT_ROOT = Path(__file__).resolve().parent


class TimeExistenceTest:
    """时间存在性检验"""

    def __init__(self, draws):
        self.draws = draws
        self.n = len(draws)
        self.results = {}

    def run_all(self):
        print("=" * 70)
        print("  ⚖️ 时间不存在检验协议 V0.2")
        print("  假设: 如果时间存在，数据应表现出方向性、漂移、马尔可夫性")
        print("  目标: 证伪这个假设")
        print("=" * 70)
        print()

        tests = [
            ("1. 前后对称性检验", self.test_time_reversal),
            ("2. 马尔可夫性检验", self.test_markov),
            ("3. 统计漂移检验", self.test_drift),
            ("4. 信息复杂度检验", self.test_complexity),
            ("5. 因果方向检验", self.test_causal_direction),
            ("6. 预测增益检验", self.test_prediction_gain),
            ("7. 结构稳定性检验", self.test_structural_stability),
            ("8. Hurst 指数检验", self.test_hurst),
        ]

        passed = 0
        failed = 0

        for name, test_fn in tests:
            print(f"\n{'━'*60}")
            print(f"  {name}")
            print(f"{'━'*60}")
            result = test_fn()
            self.results[name] = result

            if result["verdict"] == "REJECT":
                print(f"  ❌ 证伪: {result['summary']}")
                failed += 1
            else:
                print(f"  ✅ 通过: {result['summary']}")
                passed += 1

        print(f"\n{'='*70}")
        print(f"  总结")
        print(f"{'='*70}")
        print(f"  通过: {passed}/{len(tests)} (支持'时间存在')")
        print(f"  证伪: {failed}/{len(tests)} (支持'时间不存在')")
        print()

        if failed == 0:
            print(f"  ⚠️  所有检验都通过了'时间存在'假设。")
            print(f"  结论: 数据与随机序列一致。公式可能无用。")
        elif failed >= 6:
            print(f"  ⚠️  大多数检验证伪了'时间存在'假设。")
            print(f"  结论: 数据有强烈的非随机结构。公式可能有效。")
        elif failed >= 4:
            print(f"  ⚠️  部分检验证伪了'时间存在'假设。")
            print(f"  结论: 数据有微弱的非随机结构。需要更多数据。")
        else:
            print(f"  ⚠️  少数检验证伪了'时间存在'假设。")
            print(f"  结论: 数据接近随机。公式效果可能有限。")

        output = {
            "timestamp": datetime.now().isoformat(),
            "n_draws": self.n,
            "tests": {k: {kk: vv for kk, vv in v.items() if kk != "details"} for k, v in self.results.items()},
            "summary": {
                "passed": passed,
                "failed": failed,
                "total": len(tests),
                "interpretation": self._interpret(failed, passed),
            }
        }
        with open(str(_PROJECT_ROOT / "time_existence_test.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n📄 结果已保存: time_existence_test.json")

    def _interpret(self, failed, passed):
        if failed == 0:
            return "数据与完全随机一致。无法用公式预测。"
        elif failed >= 6:
            return "数据强烈非随机。存在静态场结构。公式有效。"
        elif failed >= 4:
            return "数据部分非随机。可能存在弱结构。需要更多检验。"
        else:
            return "数据接近随机。公式效果有限。"

    def _get_position_sequences(self):
        reds_by_pos = [[] for _ in range(6)]
        for draw in self.draws:
            reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
            for i in range(6):
                if i < len(reds):
                    reds_by_pos[i].append(reds[i])
        return reds_by_pos

    def test_time_reversal(self):
        """如果时间不存在，正向=反向"""
        reds_by_pos = self._get_position_sequences()
        results = {}
        for pos in range(6):
            s = np.array(reds_by_pos[pos])
            s_rev = s[::-1]
            # KS 检验
            cdf1 = np.cumsum(np.bincount(s, minlength=34)) / len(s)
            cdf2 = np.cumsum(np.bincount(s_rev, minlength=34)) / len(s_rev)
            ks = np.max(np.abs(cdf1 - cdf2))
            results[f"pos{pos+1}"] = round(ks, 4)

        avg_ks = np.mean(list(results.values()))
        verdict = "REJECT" if avg_ks < 0.02 else "PASS"
        return {"details": results, "avg_ks": round(avg_ks, 4), "verdict": verdict,
                "summary": f"正向/反向KS均值={avg_ks:.4f} {'(相同→时间不存在)' if avg_ks < 0.02 else '(不同→时间存在)'}"}

    def test_markov(self):
        """如果时间不存在，ACF 不快速衰减"""
        reds_by_pos = self._get_position_sequences()
        results = {}
        for pos in range(6):
            s = np.array(reds_by_pos[pos])
            n = len(s)
            mean = np.mean(s)
            var = np.var(s)
            if var < 1e-10:
                results[f"pos{pos+1}"] = 0
                continue
            acfs = []
            for lag in range(1, 21):
                acf = np.mean((s[:-lag] - mean) * (s[lag:] - mean)) / var
                acfs.append(abs(acf))
            # 慢衰减 = 长尾ACF
            slow = sum(1 for lag, acf in enumerate(acfs, 1) if acf > 0.01 and lag > 5)
            results[f"pos{pos+1}"] = slow

        avg_slow = np.mean(list(results.values()))
        verdict = "REJECT" if avg_slow > 3 else "PASS"
        return {"details": results, "avg_slow": round(avg_slow, 2), "verdict": verdict,
                "summary": f"长尾ACF位置数={avg_slow:.1f} (越多→时间不存在)"}

    def test_drift(self):
        """如果时间不存在，统计特性不漂移"""
        reds_by_pos = self._get_position_sequences()
        results = {}
        for pos in range(6):
            s = np.array(reds_by_pos[pos])
            window = 100
            rolling = [np.mean(s[i:i+window]) for i in range(0, len(s)-window, window)]
            if len(rolling) > 1:
                slope = np.polyfit(range(len(rolling)), rolling, 1)[0]
                drift = abs(slope) / max(abs(np.mean(rolling)), 1)
            else:
                drift = 0
            results[f"pos{pos+1}"] = round(drift, 6)

        avg_drift = np.mean(list(results.values()))
        verdict = "PASS" if avg_drift > 0.001 else "REJECT"
        return {"details": results, "avg_drift": round(avg_drift, 6), "verdict": verdict,
                "summary": f"平均漂移率={avg_drift:.6f} {'(漂移→时间存在)' if avg_drift > 0.001 else '(无漂移→时间不存在)'}"}

    def test_complexity(self):
        """如果时间不存在，信息复杂度不随数据量变化"""
        results = {}
        for ws in [100, 500, 1000, 2000]:
            if ws >= self.n:
                continue
            subset = self.draws[:ws]
            freq = Counter()
            for d in subset:
                reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
                for n in reds:
                    freq[n] += 1
            total = len(subset) * 6
            entropy = -sum((c/total)*math.log2(c/total) for c in freq.values() if c > 0)
            results[f"w{ws}"] = round(entropy, 4)

        entropies = list(results.values())
        slope = (entropies[-1] - entropies[0]) / len(entropies) if len(entropies) >= 2 else 0
        verdict = "PASS" if abs(slope) > 0.01 else "REJECT"
        return {"details": results, "slope": round(slope, 6), "verdict": verdict,
                "summary": f"熵变化率={slope:.6f} {'(下降→时间存在)' if abs(slope) > 0.01 else '(恒定→时间不存在)'}"}

    def test_causal_direction(self):
        """如果时间不存在，因果不对称性低"""
        reds_by_pos = self._get_position_sequences()
        results = {}
        for pos in range(6):
            s = np.array(reds_by_pos[pos])
            if len(s) < 20:
                results[f"pos{pos+1}"] = 0
                continue
            bins = np.percentile(s, [33, 66])
            disc = np.digitize(s, bins)
            joint_fwd = Counter()
            joint_rev = Counter()
            for i in range(1, len(disc)):
                joint_fwd[(disc[i], disc[i-1])] += 1
                joint_rev[(disc[i-1], disc[i])] += 1
            total = sum(joint_fwd.values())
            h_fwd = -sum((c/total)*math.log2(c/total) for c in joint_fwd.values() if c > 0)
            h_rev = -sum((c/total)*math.log2(c/total) for c in joint_rev.values() if c > 0)
            asym = abs(h_fwd - h_rev) / max(h_fwd + h_rev, 1e-10)
            results[f"pos{pos+1}"] = round(asym, 4)

        avg_asym = np.mean(list(results.values()))
        verdict = "PASS" if avg_asym > 0.01 else "REJECT"
        return {"details": results, "avg_asym": round(avg_asym, 4), "verdict": verdict,
                "summary": f"平均非对称性={avg_asym:.4f} {'(有方向→时间存在)' if avg_asym > 0.01 else '(无方向→时间不存在)'}"}

    def test_prediction_gain(self):
        """如果时间不存在，预测精度不随数据量提升"""
        results = {}
        for ts in [100, 500, 1000, 2000]:
            if ts >= self.n - 100:
                continue
            train = self.draws[:ts]
            test = self.draws[ts+50:min(ts+100, self.n)]
            if not test:
                continue
            freq = Counter()
            for d in train:
                reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
                for n in reds:
                    freq[n] += 1
            top6 = [n for n, _ in freq.most_common(6)]
            hits = sum(len(set(top6) & (set(d.reds) if hasattr(d, 'reds') else set(sorted(list(d.red))))) for d in test)
            acc = hits / (len(test) * 6)
            results[f"train{ts}"] = round(acc, 4)

        accs = list(results.values())
        gain = accs[-1] - accs[0] if len(accs) >= 2 else 0
        verdict = "PASS" if gain > 0.005 else "REJECT"
        return {"details": results, "gain": round(gain, 4), "verdict": verdict,
                "summary": f"预测增益={gain:.4f} {'(增益→时间存在)' if gain > 0.005 else '(无增益→时间不存在)'}"}

    def test_structural_stability(self):
        """如果时间不存在，KL散度不随数据量变化"""
        results = {}
        for ws in [100, 500, 1000, 2000]:
            if ws >= self.n:
                continue
            subset = self.draws[:ws]
            freq = Counter()
            for d in subset:
                reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
                for n in reds:
                    freq[n] += 1
            expected = 6/33
            kl = sum((freq.get(n,0)/len(subset))*math.log(max((freq.get(n,0)/len(subset))/expected, 1e-10)) for n in range(1,34))
            results[f"w{ws}"] = round(kl, 6)

        kls = list(results.values())
        var = np.var(kls) if len(kls) > 1 else 0
        verdict = "PASS" if var > 1e-8 else "REJECT"
        return {"details": results, "kl_var": round(var, 8), "verdict": verdict,
                "summary": f"KL方差={var:.8f} {'(变化→时间存在)' if var > 1e-8 else '(稳定→时间不存在)'}"}

    def test_hurst(self):
        """如果时间不存在，Hurst ≠ 0.5"""
        reds_by_pos = self._get_position_sequences()
        results = {}
        for pos in range(6):
            s = np.array(reds_by_pos[pos])
            n = len(s)
            if n < 20:
                results[f"pos{pos+1}"] = 0.5
                continue
            ret = np.diff(s)
            lags = range(2, min(80, n//4))
            taus = []
            for lag in lags:
                rs = []
                for i in range(0, n-lag, lag):
                    seg = ret[i:i+lag]
                    if len(seg) < 2:
                        continue
                    m = np.mean(seg)
                    std = np.std(seg)
                    if std < 1e-12:
                        continue
                    r = np.max(np.cumsum(seg-m)) - np.min(np.cumsum(seg-m))
                    rs.append(r/std)
                if rs:
                    taus.append(np.log(np.mean(rs)))
            if len(taus) >= 3:
                h = np.polyfit(np.log(list(lags)[:len(taus)]), taus, 1)[0]
            else:
                h = 0.5
            results[f"pos{pos+1}"] = round(h, 4)

        avg_h = np.mean(list(results.values()))
        dev = abs(avg_h - 0.5)
        verdict = "REJECT" if dev > 0.05 else "PASS"
        return {"details": results, "avg_hurst": round(avg_h, 4), "verdict": verdict,
                "summary": f"平均Hurst={avg_h:.4f} {'(≠0.5→时间不存在)' if dev > 0.05 else '(≈0.5→时间存在)'}"}


if __name__ == "__main__":
    draws = load_history()
    print(f"数据: {len(draws)} 期\n")
    tester = TimeExistenceTest(draws)
    tester.run_all()
