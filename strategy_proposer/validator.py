# -*- coding: utf-8 -*-
"""
Antigravity 策略框架 — 假设验证器 V1.0

核心理念:
- 每个假设都必须通过 walk-forward 交叉验证
- 验证结果: survived (通过) / eliminated (失败)
- 失败时记录原因: overfit / noise_chase / cliche / fragile
- 验证通过的假设可以"进化"出新假设

用法:
    from strategy_proposer.validator import HypothesisValidator

    validator = HypothesisValidator()
    results = validator.validate_all(hypotheses, draws)
"""
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from strategy_proposer.hypothesis import Hypothesis

_PROJECT_ROOT = Path(__file__).resolve().parent


class HypothesisValidator:
    """假设验证器 — walk-forward 交叉验证"""

    def __init__(self, random_baseline: float = 1.09):
        self.random_baseline = random_baseline

    def validate(self, hypothesis: Hypothesis, draws: Any,
                 n_windows: int = 8, window_size: int = 300,
                 step: int = 30) -> Dict:
        """
        验证一个假设。

        由于假设是"陈述"而非具体策略，验证器根据假设的category和params
        生成对应的测试策略，然后进行walk-forward验证。

        Args:
            hypothesis: 待验证的假设
            draws: 历史数据
            n_windows: 验证窗口数
            window_size: 训练窗口大小
            step: 窗口步进

        Returns:
            {
                "status": "survived" | "eliminated",
                "avg_hits": 平均命中数,
                "p_value": p值,
                "elimination_reason": 失败原因(如果淘汰),
                "per_round": 每轮命中数,
                "validated_at": 验证时间,
            }
        """
        # 根据假设生成测试策略
        strategy = self._build_test_strategy(hypothesis, draws)
        if strategy is None:
            return {
                "status": "eliminated",
                "avg_hits": 0, "p_value": 1.0,
                "elimination_reason": "cannot_build_strategy",
                "per_round": [],
                "validated_at": datetime.now().isoformat(),
            }

        # walk-forward 验证
        per_round_hits = []
        for w in range(n_windows):
            train_end = window_size + w * step
            test_start = train_end + 10
            test_end = test_start + 10

            if test_end > len(draws):
                break

            try:
                pred = strategy(train_draws=draws[:train_end], test_draws=draws[test_start:test_end])
                if pred:
                    actual_reds = set()
                    for d in pred["test_draws"]:
                        actual = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
                        actual_reds.update(actual)

                    hits = len(set(pred.get("reds", [])) & actual_reds) if pred.get("reds") else 0
                    per_round_hits.append(hits / 6.0)
                else:
                    per_round_hits.append(0)
            except Exception:
                per_round_hits.append(0)

        if not per_round_hits:
            return {
                "status": "eliminated",
                "avg_hits": 0, "p_value": 1.0,
                "elimination_reason": "no_valid_rounds",
                "per_round": [],
                "validated_at": datetime.now().isoformat(),
            }

        avg = sum(per_round_hits) / len(per_round_hits)
        std = math.sqrt(sum((h - avg) ** 2 for h in per_round_hits) / max(len(per_round_hits) - 1, 1))

        # t检验
        se = std / math.sqrt(len(per_round_hits)) if std > 0 else 1
        t_stat = (avg - self.random_baseline) / se if se > 0 else 0
        p_value = self._t_to_pvalue(t_stat, len(per_round_hits))

        # 判定是否存活
        elimination_reason = None
        if avg < self.random_baseline:
            elimination_reason = "below_random_baseline"
        elif p_value > 0.1:
            elimination_reason = "not_significant"
        elif std > avg * 0.5:
            elimination_reason = "too_unstable"
        elif len(per_round_hits) < 3:
            elimination_reason = "insufficient_data"

        status = "eliminated" if elimination_reason else "survived"

        # 更新假设
        hypothesis.status = status
        hypothesis.tested_at = datetime.now().isoformat()
        hypothesis.result = {
            "avg_hits": round(avg, 4),
            "std": round(std, 4),
            "p_value": round(p_value, 4),
            "rounds": len(per_round_hits),
            "beats_random": avg > self.random_baseline,
            "stable": round(avg - std, 4),
        }
        hypothesis.elimination_reason = elimination_reason

        return {
            "status": status,
            "avg_hits": round(avg, 4),
            "std": round(std, 4),
            "p_value": round(p_value, 4),
            "elimination_reason": elimination_reason,
            "per_round": [round(h, 4) for h in per_round_hits],
            "validated_at": hypothesis.tested_at,
        }

    def validate_all(self, hypotheses: List[Hypothesis], draws: Any,
                     **kwargs) -> Dict[str, Dict]:
        """批量验证假设"""
        results = {}
        for h in hypotheses:
            result = self.validate(h, draws, **kwargs)
            results[h.id] = result
        return results

    def _build_test_strategy(self, hypothesis: Hypothesis, draws: Any):
        """
        根据假设生成测试策略。

        这是一个简化实现。在实际系统中，每个假设类别应该有对应的策略生成器。
        这里我们用启发式方法根据假设的category生成简单的测试策略。
        """
        category = hypothesis.template_category

        if category in ["periodic", "spectral"]:
            return self._periodic_test_strategy
        elif category == "omission":
            return self._omission_test_strategy
        elif category == "positional":
            return self._positional_test_strategy
        elif category == "cooccurrence":
            return self._cooccurrence_test_strategy
        elif category == "structural":
            return self._structural_test_strategy
        elif category == "blue":
            return self._blue_test_strategy
        else:
            return self._generic_test_strategy

    def _periodic_test_strategy(self, train_draws, test_draws):
        """周期性测试策略"""
        from collections import Counter
        freq = Counter()
        for d in train_draws:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            freq.update(reds)
        top6 = [n for n, _ in freq.most_common(6)]
        return {"reds": top6, "test_draws": test_draws}

    def _omission_test_strategy(self, train_draws, test_draws):
        """遗漏测试策略"""
        from collections import Counter
        freq = Counter()
        for d in train_draws:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            freq.update(reds)
        # 选频率最低的6个
        sorted_nums = sorted(freq.items(), key=lambda x: x[1])
        top6 = [n for n, _ in sorted_nums[:6]]
        return {"reds": top6, "test_draws": test_draws}

    def _positional_test_strategy(self, train_draws, test_draws):
        """位置测试策略"""
        from collections import Counter
        pos_freq = [Counter() for _ in range(6)]
        for d in train_draws:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            for i, r in enumerate(reds):
                pos_freq[i][r] += 1
        top6 = []
        for i in range(6):
            if pos_freq[i]:
                top6.append(pos_freq[i].most_common(1)[0][0])
        return {"reds": top6[:6], "test_draws": test_draws}

    def _cooccurrence_test_strategy(self, train_draws, test_draws):
        """共现测试策略"""
        from collections import Counter
        cooccur = Counter()
        for d in train_draws:
            reds = sorted(d.reds if hasattr(d, 'reds') else sorted(list(d.red)))
            for i in range(len(reds)):
                for j in range(i + 1, len(reds)):
                    cooccur[(reds[i], reds[j])] += 1
        # 选共现最高的号码
        num_score = Counter()
        for (a, b), c in cooccur.items():
            num_score[a] += c
            num_score[b] += c
        top6 = [n for n, _ in num_score.most_common(6)]
        return {"reds": top6, "test_draws": test_draws}

    def _structural_test_strategy(self, train_draws, test_draws):
        """结构测试策略"""
        from collections import Counter
        freq = Counter()
        for d in train_draws:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            freq.update(reds)
        top6 = [n for n, _ in freq.most_common(6)]
        return {"reds": top6, "test_draws": test_draws}

    def _blue_test_strategy(self, train_draws, test_draws):
        """蓝球测试策略"""
        from collections import Counter
        blues = Counter()
        for d in train_draws:
            blues[d.blue if hasattr(d, 'blue') else d.blue] += 1
        top_blue = blues.most_common(1)[0][0] if blues else 8
        return {"reds": [], "blue": top_blue, "test_draws": test_draws}

    def _generic_test_strategy(self, train_draws, test_draws):
        """通用测试策略（频率最高）"""
        from collections import Counter
        freq = Counter()
        for d in train_draws:
            reds = d.reds if hasattr(d, 'reds') else sorted(list(d.red))
            freq.update(reds)
        top6 = [n for n, _ in freq.most_common(6)]
        return {"reds": top6, "test_draws": test_draws}

    @staticmethod
    def _t_to_pvalue(t: float, df: int) -> float:
        """简化t检验p值"""
        x = abs(t) / math.sqrt(2)
        try:
            sign = 1 if x >= 0 else -1
            a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
            p = 0.3275911
            t_val = 1.0 / (1.0 + p * abs(x))
            erf_x = sign * (1.0 - (((((a5 * t_val + a4) * t_val) + a3) * t_val + a2) * t_val + a1) * t_val * math.exp(-x * x))
            p_one_tail = 0.5 * (1 - erf_x)
            return min(1.0, 2 * p_one_tail)
        except:
            return 1.0
