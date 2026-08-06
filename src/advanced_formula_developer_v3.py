# -*- coding: utf-8 -*-
"""
Antigravity 高级公式开发引擎 V3.0 — 精准突破版

核心策略（基于云端反馈分析）:
1. 强化 Spectral(0.55) + Relational(0.48) 两大最强家族
2. 废弃 Chaotic(0.0137) 和弱化 Temporal(0.0619)
3. 引入动态权重 — 根据最近N期表现自适应调整
4. 构建蓝球专用预测器 — 独立于红球评估
5. 开发"反共识"极端号码策略

目标: 将avg_hits从0.93提升到1.10+，超越随机基线1.09
"""
import json
import math
import random
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from dataclasses import dataclass, field

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from data_layer import load_history, Draw
from formula_lang.primitive import Primitive, get_default_primitives
from formula_lang.grammar import Formula, FormulaGrammar
from formula_lang.evaluator import FormulaEvaluator
from formula_lang.mutator import PrimitiveMutator


# ═══════════════════════════════════════════════════════════
# 数据工具
# ═══════════════════════════════════════════════════════════

def get_reds(draw: Draw) -> list:
    return draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))


def get_blue(draw: Draw) -> int:
    return draw.blue


def number_frequency(draws: list, lookback: int = 100) -> Counter:
    """计算最近N期号码频率"""
    recent = draws[-lookback:]
    freq = Counter()
    for d in recent:
        for r in get_reds(d):
            freq[r] += 1
    return freq


def number_omission(draws: list, n: int) -> int:
    """计算号码n的当前遗漏期数"""
    for i, d in enumerate(reversed(draws)):
        if n in get_reds(d):
            return i
    return len(draws)


def blue_ball_pattern(draws: list, lookback: int = 200) -> dict:
    """分析蓝球模式"""
    recent = draws[-lookback:]
    blues = [get_blue(d) for d in recent]

    # 频率
    freq = Counter(blues)

    # 遗漏
    omissions = {}
    for b in range(1, 17):
        for i, bl in enumerate(reversed(blues)):
            if bl == b:
                omissions[b] = i
                break
        else:
            omissions[b] = len(blues)

    # 周期性 — 检测蓝球是否有固定周期
    periods = {}
    for b in range(1, 17):
        positions = [i for i, bl in enumerate(blues) if bl == b]
        if len(positions) >= 3:
            gaps = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
            mean_gap = sum(gaps) / len(gaps)
            var_gap = sum((g - mean_gap)**2 for g in gaps) / len(gaps)
            cv = math.sqrt(var_gap) / mean_gap if mean_gap > 0 else 999
            periods[b] = {"mean_period": mean_gap, "cv": cv, "appearances": len(positions)}

    return {
        "freq": dict(freq.most_common()),
        "omissions": omissions,
        "periods": periods,
    }


# ═══════════════════════════════════════════════════════════
# 新原语: 动态加权共现 (Dynamic Cooccurrence)
# ═══════════════════════════════════════════════════════════

class DynamicCooccurrence(Primitive):
    """
    动态加权共现原语

    核心创新: 不是固定lookback窗口，而是根据近期表现动态调整权重。
    最近10期的共现权重是最近50期的2倍，最近50期又是最近200期的2倍。

    基于云端反馈: cooccurrence_affinity是最好的关系原语(30号:1.76)
    但这个版本引入时间衰减，让近期信号更强。
    """

    def __init__(self, decay_rates=None):
        super().__init__(
            name="dynamic_cooccurrence",
            category="relational",
            description="动态加权共现 — 近期共现模式权重更高",
            parameters={"decay_rates": decay_rates or [2.0, 1.0, 0.5]},
        )
        self.decay_rates = decay_rates or [2.0, 1.0, 0.5]

    def score_number(self, n: int, draws: list) -> float:
        # 三层窗口: 10期/50期/200期
        windows = [10, 50, 200]
        weights = self.decay_rates

        total_score = 0.0
        total_weight = 0.0

        for w_size, w_weight in zip(windows, weights):
            recent = draws[-min(w_size, len(draws)):]

            # 计算n与其他号码的共现
            cooccur = Counter()
            freq = Counter()

            for d in recent:
                reds = get_reds(d)
                for r in reds:
                    freq[r] += 1
                for i in range(len(reds)):
                    for j in range(i+1, len(reds)):
                        cooccur[(reds[i], reds[j])] += 1
                        cooccur[(reds[j], reds[i])] += 1

            total = len(recent)
            expected = (6/33) * (5/32) * total

            # n的超额共现
            affinity = 0
            for m in range(1, 34):
                if m == n:
                    continue
                obs = cooccur.get((n, m), 0) / 2  # 因为双向计数
                exc = (obs - expected/2) / max(expected/2, 1)
                if exc > 0.1:
                    affinity += exc

            total_score += affinity * w_weight
            total_weight += w_weight

        return max(0, total_score / max(total_weight, 1) / 5)  # 归一化


# ═══════════════════════════════════════════════════════════
# 新原语: 频谱-共现联合 (Spectral-Cooccurrence Fusion)
# ═══════════════════════════════════════════════════════════

class SpectralCooccurrenceFusion(Primitive):
    """
    频谱-共现联合原语

    核心创新: 结合SpectralPower的频域信号和CooccurrenceAffinity的关系信号。
    如果一个号码在频谱上有显著周期信号，并且与共现强关联号码的配对
    也符合该周期，则得分极高。

    基于云端反馈: Spectral家族得分0.55最高，Relational家族0.48次之
    两者的联合应该产生更强的信号。
    """

    def __init__(self, lookback: int = 200):
        super().__init__(
            name="spectral_cooccurrence_fusion",
            category="relational",
            description="频谱×共现联合分析 — 频域周期与关系模式共振的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def _simple_fft_power(self, seq: list) -> dict:
        """简化的频谱功率计算"""
        n = len(seq)
        if n < 10:
            return {}

        powers = {}
        for k in range(2, min(n//2, 50)):  # 只检测50期以内的周期
            re = sum(seq[i] * math.cos(2 * math.pi * k * i / n) for i in range(n))
            im = sum(seq[i] * math.sin(2 * math.pi * k * i / n) for i in range(n))
            power = (re**2 + im**2) / (n**2)
            powers[k] = power

        if not powers:
            return {}

        mean_p = sum(powers.values()) / len(powers)
        std_p = math.sqrt(sum((p - mean_p)**2 for p in powers.values()) / len(powers))

        # 返回显著峰值(>mean+2*std)
        peaks = {f: p for f, p in powers.items() if p > mean_p + 2 * std_p}
        return peaks

    def score_number(self, n: int, draws: list) -> float:
        recent = draws[-min(self.lookback, len(draws)):]

        # 1. 构建n的出现序列
        seq = [1 if n in get_reds(d) else 0 for d in recent]

        # 2. 计算频谱功率峰值
        peaks = self._simple_fft_power(seq)

        if not peaks:
            return 0.3  # 无显著周期信号

        # 3. 计算共现亲和度
        cooccur = Counter()
        for d in recent:
            reds = get_reds(d)
            for i in range(len(reds)):
                for j in range(i+1, len(reds)):
                    cooccur[(reds[i], reds[j])] += 1

        # 4. 联合评分: 如果有频谱周期信号，且该号码在周期内与共现伙伴配对
        n_partners = set()
        for (a, b), cnt in cooccur.items():
            if a == n:
                n_partners.add(b)
            elif b == n:
                n_partners.add(a)

        if not n_partners:
            return 0.2

        # 5. 检查伙伴号码是否也有频谱周期信号
        partner_peak_count = 0
        for m in n_partners:
            m_seq = [1 if m in get_reds(d) else 0 for d in recent]
            m_peaks = self._simple_fft_power(m_seq)
            if m_peaks:
                partner_peak_count += 1

        # 联合得分: 频谱峰值强度 × 伙伴周期同步率
        peak_strength = sum(peaks.values()) / max(len(peaks), 1)
        sync_ratio = partner_peak_count / max(len(n_partners), 1)

        return min(1.0, peak_strength * 10 * sync_ratio)


# ═══════════════════════════════════════════════════════════
# 新原语: 极端号码探测器 (Extreme Number Detector)
# ═══════════════════════════════════════════════════════════

class ExtremeNumberDetector(Primitive):
    """
    极端号码探测器

    核心创新: 当前共识号码集中在中号区(15-30)。
    这个原语专门探测小号区(1-10)和大号区(25-33)的极端模式。

    基于云端反馈: 需要"反共识"策略，探索极端号码的周期性。
    """

    def __init__(self, lookback: int = 200):
        super().__init__(
            name="extreme_number_detector",
            category="structural",
            description="极端号码(1-10, 25-33)模式探测 — 极端区周期性稳定的号码得分高",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: list) -> float:
        recent = draws[-min(self.lookback, len(draws)):]

        # 判断n是否属于极端区
        is_small = 1 <= n <= 10
        is_large = 25 <= n <= 33

        if not (is_small or is_large):
            return 0.2  # 中间号码不关注

        # 计算n在极端区的出现规律
        positions = [i for i, d in enumerate(reversed(recent)) if n in get_reds(d)]

        if len(positions) < 3:
            return 0.3  # 数据不足

        # 计算间隔的周期性
        gaps = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
        mean_gap = sum(gaps) / len(gaps)
        var_gap = sum((g - mean_gap)**2 for g in gaps) / len(gaps)
        cv = math.sqrt(var_gap) / mean_gap if mean_gap > 0 else 999

        # CV越小，周期越稳定，得分越高
        return max(0, 1.0 - cv * 1.5)


# ═══════════════════════════════════════════════════════════
# 新原语: 蓝球周期探测器 (Blue Ball Periodicity)
# ═══════════════════════════════════════════════════════════

class BlueBallPeriodicity(Primitive):
    """
    蓝球周期探测器

    核心创新: 独立于红球评估的蓝球专用原语。
    检测每个蓝球(1-16)的出现周期性和遗漏模式。

    基于云端反馈: 所有公式蓝球命中率都是0.0657，完全相同，
    说明蓝球没有被任何公式有效评估。
    """

    def __init__(self, lookback: int = 300):
        super().__init__(
            name="blue_ball_periodicity",
            category="temporal",
            description="蓝球周期探测 — 独立红球评估的蓝球专用原语",
            parameters={"lookback": lookback},
        )
        self.lookback = lookback

    def score_number(self, n: int, draws: list) -> float:
        """
        注意: 这里的n是蓝球(1-16)，不是红球。
        但为了接口统一，我们仍然用score_number(n, draws)。
        """
        if not 1 <= n <= 16:
            return 0.5

        recent = draws[-min(self.lookback, len(draws)):]

        # 提取蓝球序列
        blue_seq = [get_blue(d) for d in recent]

        # 计算n的出现间隔
        positions = [i for i, b in enumerate(reversed(blue_seq)) if b == n]

        if len(positions) < 2:
            return 0.3  # 出现太少

        # 当前遗漏
        current_omission = positions[0] if positions else len(blue_seq)

        # 历史平均间隔
        if len(positions) >= 2:
            gaps = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
            mean_gap = sum(gaps) / len(gaps)

            # 如果当前遗漏接近平均间隔的0.8-1.2倍，说明即将出现
            proximity = 1.0 - abs(current_omission - mean_gap) / mean_gap
            return max(0, proximity)
        else:
            # 只用当前遗漏判断
            return max(0, 1.0 - current_omission / max(len(blue_seq), 1))


# ═══════════════════════════════════════════════════════════
# 新原语: 多尺度共振 (Multi-Scale Resonance)
# ═══════════════════════════════════════════════════════════

class MultiScaleResonance(Primitive):
    """
    多尺度共振原语

    核心创新: 一个号码如果在多个时间尺度上都表现出规律性，
    那么它的预测价值远高于只在单一尺度有规律的号码。

    基于云端反馈: 当前公式在单一尺度评估，缺乏多尺度一致性检验。
    """

    def __init__(self, scales=None):
        super().__init__(
            name="multi_scale_resonance",
            category="multi_scale",
            description="多尺度共振 — 在多个时间尺度都表现一致的号码得分高",
            parameters={"scales": scales or [10, 30, 60, 120, 200]},
        )
        self.scales = scales or [10, 30, 60, 120, 200]

    def score_number(self, n: int, draws: list) -> float:
        # 计算每个尺度的规律性
        consistency_scores = []

        for scale in self.scales:
            if scale > len(draws):
                continue

            recent = draws[-scale:]
            positions = [i for i, d in enumerate(reversed(recent)) if n in get_reds(d)]

            if len(positions) < 2:
                consistency_scores.append(0.0)
                continue

            # 计算间隔的CV
            gaps = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
            mean_gap = sum(gaps) / len(gaps)
            var_gap = sum((g - mean_gap)**2 for g in gaps) / len(gaps)
            cv = math.sqrt(var_gap) / mean_gap if mean_gap > 0 else 999

            # CV越小，规律性越强
            scale_score = max(0, 1.0 - cv)
            consistency_scores.append(scale_score)

        if not consistency_scores:
            return 0.3

        # 多尺度一致性 = 最低的那个尺度的得分
        # (木桶原理: 最弱的尺度决定整体可靠性)
        return min(consistency_scores)


# ═══════════════════════════════════════════════════════════
# 新原语: 趋势动量 (Trend Momentum)
# ═══════════════════════════════════════════════════════════

class TrendMomentum(Primitive):
    """
    趋势动量原语

    核心创新: 不仅看号码是否"热"或"冷"，还看它的趋势变化方向。
    一个从冷变热的号码(动量为正)比一直热的号码更有预测价值。

    基于云端反馈: RecencyGradient只有部分号码有非零值，
    说明趋势信号确实存在但不够敏感。这个版本增强灵敏度。
    """

    def __init__(self, short_window=20, long_window=100):
        super().__init__(
            name="trend_momentum",
            category="temporal",
            description="趋势动量 — 从冷变热的号码得分高",
            parameters={"short_window": short_window, "long_window": long_window},
        )
        self.short_window = short_window
        self.long_window = long_window

    def score_number(self, n: int, draws: list) -> float:
        short = draws[-min(self.short_window, len(draws)):]
        long = draws[-min(self.long_window, len(draws)):]

        # 短期频率
        short_freq = sum(1 for d in short if n in get_reds(d)) / max(len(short) * 6, 1)

        # 长期频率
        long_freq = sum(1 for d in long if n in get_reds(d)) / max(len(long) * 6, 1)

        # 动量 = 短期频率 - 长期频率
        momentum = short_freq - long_freq

        # 动量越大(从冷变热)，得分越高
        # 动量为负(从热变冷)，得分低但不为0(可能有回补)
        return max(0, 0.5 + momentum * 5)


# ═══════════════════════════════════════════════════════════
# 高级公式开发引擎
# ═══════════════════════════════════════════════════════════

@dataclass
class FormulaResult:
    """公式评估结果"""
    name: str
    primitives: list
    operator: str
    avg_hits: float
    stable: float
    p_value: float
    beats_random: bool
    top_numbers: list = field(default_factory=list)
    details: dict = field(default_factory=dict)


class AdvancedFormulaDeveloper:
    """高级公式开发引擎 V3.0"""

    def __init__(self, draws: list):
        self.draws = draws
        self.evaluator = FormulaEvaluator(random_baseline = 1.09)
        self.results = []
        self.new_primitives = self._create_new_primitives()

    def _create_new_primitives(self) -> list:
        """创建新原语"""
        return [
            # 新原语
            DynamicCooccurrence(),
            SpectralCooccurrenceFusion(),
            ExtremeNumberDetector(),
            BlueBallPeriodicity(),
            MultiScaleResonance(),
            TrendMomentum(),
            # 精选旧原语(保留表现最好的)
            *self._select_top_primitives(),
        ]

    def _select_top_primitives(self) -> list:
        """从现有原语中选择表现最好的"""
        all_prims = get_default_primitives()

        # 废弃Chaotic类别
        all_prims = [p for p in all_prims if p.category != "chaotic"]

        # 弱化Temporal类别(得分最低)
        all_prims = [p for p in all_prims if p.category != "temporal"]

        # 保留Relational, Spectral, Geometric, Structural
        # 每个类别选前5个（扩大种群）
        by_category = defaultdict(list)
        for p in all_prims:
            by_category[p.category].append(p)

        selected = []
        for cat in ["relational", "spectral", "geometric", "structural", "multi_scale", "sequence_pattern", "combinatorial"]:
            prims = by_category.get(cat, [])
            selected.extend(prims[:5])

        return selected

    def develop_formulas(self) -> list:
        """开发新公式"""
        print("\n" + "="*70)
        print("  高级公式开发引擎 V3.0 — 精准突破版")
        print("="*70)

        prims = self.new_primitives
        print(f"\n  可用原语: {len(prims)} 个")
        print(f"  其中新原语: {sum(1 for p in prims if p.name.startswith(('dynamic_', 'spectral_', 'extreme_', 'blue_', 'multi_', 'trend_')))} 个")

        # 策略1: 新原语共振组合
        print("\n  [策略1] 新原语共振组合...")
        self._develop_resonance_formulas(prims)

        # 策略2: 级联筛选
        print("\n  [策略2] 级联筛选组合...")
        self._develop_cascade_formulas(prims)

        # 策略3: 多尺度共振
        print("\n  [策略3] 多尺度共振组合...")
        self._develop_multiscale_formulas(prims)

        # 策略4: 极端号码专项
        print("\n  [策略4] 极端号码专项公式...")
        self._develop_extreme_formulas(prims)

        # 策略5: 3原语共振组合 (扩大种群)
        print("\n  [策略5] 3原语共振组合...")
        self._develop_3prism_resonance(prims)

        # 策略6: 混合组合 (扩大种群)
        print("\n  [策略6] 混合组合...")
        self._develop_mixed_formulas(prims)

        # 策略7: 自适应混合组合 — 替代resonance的新策略
        print("\n  [策略7] 自适应混合组合 (adaptive_blend)...")
        self._develop_adaptive_blend_formulas(prims)

        # 评估所有公式
        print("\n  评估所有公式...")
        self._evaluate_all()

        # 排序
        self.results.sort(key=lambda r: -r.avg_hits)

        # 输出
        print(f"\n{'='*70}")
        print(f"  开发完成 — 共开发 {len(self.results)} 个公式")
        print(f"{'='*70}")

        if self.results:
            print(f"\n  Top-5 公式:")
            for i, r in enumerate(self.results[:5]):
                status = "[超越随机]" if r.beats_random else "[未超越]"
                print(f"    {i+1}. {r.name[:50]}")
                print(f"       avg_hits={r.avg_hits:.4f} stable={r.stable:.4f} p={r.p_value:.4f} {status}")
                print(f"       原语: {[p.name for p in r.primitives]}")

        # 保存
        self._save_results()

        return self.results

    def _develop_resonance_formulas(self, prims: list):
        """共振组合公式"""
        # 新原语之间的共振
        new_prims = [p for p in prims if p.name in [
            "dynamic_cooccurrence", "spectral_cooccurrence_fusion",
            "multi_scale_resonance", "trend_momentum"
        ]]

        for i in range(len(new_prims)):
            for j in range(i+1, len(new_prims)):
                if len(new_prims) > 1:
                    f = FormulaGrammar.resonance(
                        [new_prims[i], new_prims[j]],
                        name=f"resonance_{new_prims[i].name[:10]}_{new_prims[j].name[:10]}"
                    )
                    uid = f"{new_prims[i].uuid[-6]}{new_prims[j].uuid[-6]}"
                    f.name = f"{f.name}_{uid}"
                    self.results.append(self._make_result(f))

        # 新原语 + 精选旧原语
        old_selected = [p for p in prims if p.name not in [
            "dynamic_cooccurrence", "spectral_cooccurrence_fusion",
            "multi_scale_resonance", "trend_momentum",
            "extreme_number_detector", "blue_ball_periodicity"
        ]]

        for np in new_prims:
            for op in old_selected[:5]:  # 限制数量
                f = FormulaGrammar.resonance(
                    [np, op],
                    name=f"hybrid_resonance_{np.name[:10]}_{op.name[:10]}"
                )
                uid = f"{np.uuid[-6]}{op.uuid[-6]}"
                f.name = f"{f.name}_{uid}"
                self.results.append(self._make_result(f))

    def _develop_cascade_formulas(self, prims: list):
        """级联筛选公式"""
        # 强→弱顺序级联
        strong_prims = [p for p in prims if p.name in [
            "spectral_cooccurrence_fusion", "dynamic_cooccurrence",
            "multi_scale_resonance"
        ]]

        for i in range(len(strong_prims)):
            for j in range(i+1, min(i+3, len(strong_prims))):
                f = FormulaGrammar.cascade(
                    [strong_prims[i], strong_prims[j]],
                    name=f"cascade_{strong_prims[i].name[:10]}_{strong_prims[j].name[:10]}"
                )
                uid = f"{strong_prims[i].uuid[-6]}{strong_prims[j].uuid[-6]}"
                f.name = f"{f.name}_{uid}"
                self.results.append(self._make_result(f))

    def _develop_multiscale_formulas(self, prims: list):
        """多尺度共振公式"""
        ms_prims = [p for p in prims if p.category == "multi_scale"]

        if ms_prims:
            # 多尺度 + 关系
            for rp in [p for p in prims if p.category == "relational"]:
                f = FormulaGrammar.phase_align(
                    [ms_prims[0], rp],
                    name=f"phase_ms_rel_{rp.name[:10]}"
                )
                uid = f"{ms_prims[0].uuid[-6]}{rp.uuid[-6]}"
                f.name = f"{f.name}_{uid}"
                self.results.append(self._make_result(f))

    def _develop_extreme_formulas(self, prims: list):
        """极端号码专项公式"""
        ext_prims = [p for p in prims if p.name == "extreme_number_detector"]

        if ext_prims:
            # 极端号码 + 趋势动量
            for tp in [p for p in prims if p.name == "trend_momentum"]:
                f = FormulaGrammar.weighted_sum(
                    [ext_prims[0], tp],
                    name="extreme_trend_weighted"
                )
                self.results.append(self._make_result(f))

                # 极端号码 + 多尺度
                for mp in [p for p in prims if p.name == "multi_scale_resonance"]:
                    f = FormulaGrammar.resonance(
                        [ext_prims[0], mp],
                        name="extreme_ms_resonance"
                    )
                    self.results.append(self._make_result(f))

    def _develop_3prism_resonance(self, prims: list):
        """3原语共振组合 — 扩大种群"""
        # 选取最强的原语组合
        strong_prims = [p for p in prims if p.category in ("relational", "spectral", "multi_scale")]
        if len(strong_prims) < 3:
            return

        # 三重共振
        for i in range(min(len(strong_prims), 12)):
            for j in range(i + 1, min(len(strong_prims), 12)):
                for k in range(j + 1, min(len(strong_prims), 12)):
                    combo = [strong_prims[i], strong_prims[j], strong_prims[k]]
                    f = FormulaGrammar.resonance(combo, name=f"tri_res_{combo[0].name[:8]}_{combo[1].name[:8]}")
                    uid = ''.join(c.uuid[-6] for c in combo)
                    f.name = f"{f.name}_{uid}"
                    self.results.append(self._make_result(f))

    def _develop_mixed_formulas(self, prims: list):
        """混合组合 — 新原语 × 旧原语 × 各种算子"""
        new_prims = [p for p in prims if p.name in [
            "dynamic_cooccurrence", "spectral_cooccurrence_fusion",
            "multi_scale_resonance", "trend_momentum", "extreme_number_detector"
        ]]
        old_prims = [p for p in prims if p not in new_prims]

        # 2原语 + 多种算子
        for np in new_prims[:6]:
            for op in old_prims[:8]:
                # 共振
                f = FormulaGrammar.resonance([np, op], name=f"mix_res_{np.name[:8]}_{op.name[:8]}")
                uid = f"{np.uuid[-6]}{op.uuid[-6]}"
                f.name = f"{f.name}_{uid}"
                self.results.append(self._make_result(f))
                # 级联
                f = FormulaGrammar.cascade([np, op], name=f"mix_cas_{np.name[:8]}_{op.name[:8]}")
                f.name = f"{f.name}_{uid}"
                self.results.append(self._make_result(f))
                # 相位对齐
                f = FormulaGrammar.phase_align([np, op], name=f"mix_ph_{np.name[:8]}_{op.name[:8]}")
                f.name = f"{f.name}_{uid}"
                self.results.append(self._make_result(f))

    def _develop_adaptive_blend_formulas(self, prims: list):
        """自适应混合组合 — 替代resonance乘积的新策略

        核心洞察: resonance乘积压缩区分度。
        mutual_exclusion单独命中率1.2667，和bayesian做resonance后反而降到1.1。
        adaptive_blend用加权平均保留区分度。

        优先使用表现最好的原语: mutual_exclusion, bayesian, scale_transition, trend_momentum
        """
        # 精选高表现原语 (实测Top组合: ms+me+tm = 1.1850)
        elite_prims = [p for p in prims if p.name in [
            "mutual_exclusion", "multi_scale_resonance", "trend_momentum",
            "bayesian_bias_estimator", "hierarchical_bayesian_estimator",
            "empirical_bayes_shrinkage", "adaptive_bayesian_window",
            "scale_transition", "regime_switch",
            "lag_correlation", "recurrence_window", "seasonal_resonance",
            "skewness_signal", "tail_risk",
            "dynamic_cooccurrence", "spectral_cooccurrence_fusion",
            "adjacent_bias", "gap_pattern", "modulo_distribution",
        ]]

        if len(elite_prims) < 2:
            return

        # 2原语 adaptive_blend
        for i in range(min(len(elite_prims), 10)):
            for j in range(i+1, min(len(elite_prims), 10)):
                f = FormulaGrammar.adaptive_blend(
                    [elite_prims[i], elite_prims[j]],
                    name=f"blend_{elite_prims[i].name[:12]}_{elite_prims[j].name[:12]}"
                )
                uid = f"{elite_prims[i].uuid[-6]}{elite_prims[j].uuid[-6]}"
                f.name = f"{f.name}_{uid}"
                self.results.append(self._make_result(f))

        # 3原语 adaptive_blend (选最强的 — 确保包含ms+me+tm)
        top_elite = elite_prims[:10]
        for i in range(min(len(top_elite), 6)):
            for j in range(i+1, min(len(top_elite), 6)):
                for k in range(j+1, min(len(top_elite), 6)):
                    combo = [top_elite[i], top_elite[j], top_elite[k]]
                    f = FormulaGrammar.adaptive_blend(
                        combo,
                        name=f"tri_blend_{combo[0].name[:8]}_{combo[1].name[:8]}"
                    )
                    uid = ''.join(c.uuid[-6] for c in combo)
                    f.name = f"{f.name}_{uid}"
                    self.results.append(self._make_result(f))

    def _make_result(self, formula: Formula) -> FormulaResult:
        """创建FormulaResult占位符"""
        return FormulaResult(
            name=formula.name,
            primitives=formula.primitives,
            operator=formula.operators[0] if formula.operators else "unknown",
            avg_hits=0, stable=0, p_value=1, beats_random=False,
            details={}
        )

    def _evaluate_all(self):
        """评估所有公式"""
        formulas = []
        for r in self.results:
            f = Formula(
                name=r.name,
                primitives=r.primitives,
                operators=[r.operator] * max(len(r.primitives) - 1, 1),
                parameters={}
            )
            formulas.append((f, r))

        # 批量评估 — 减少窗口数加速
        eval_results = self.evaluator.evaluate_batch(
            [f for f, _ in formulas],
            self.draws,
            n_windows=3,
            window_size=500,
            step=100
        )

        for (f, result), name in zip(formulas, eval_results.keys()):
            perf = eval_results.get(name, {})
            result.avg_hits = perf.get("avg_hits", 0)
            result.stable = perf.get("stable", 0)
            result.p_value = perf.get("p_value", 1)
            result.beats_random = perf.get("beats_random", False)
            result.details = perf

        # Skip evaluate_for_all_numbers — too slow for 439 formulas
        # top_numbers will be computed later during validation if needed

    def _save_results(self):
        """保存结果"""
        output = {
            "timestamp": datetime.now().isoformat(),
            "total_formulas": len(self.results),
            "best_formula": self.results[0].name if self.results else None,
            "best_avg_hits": self.results[0].avg_hits if self.results else 0,
            "formulas_beating_random": sum(1 for r in self.results if r.beats_random),
            "results": [
                {
                    "name": r.name,
                    "avg_hits": r.avg_hits,
                    "stable": r.stable,
                    "p_value": r.p_value,
                    "beats_random": r.beats_random,
                    "top_numbers": r.top_numbers,
                    "primitives": [p.name for p in r.primitives],
                }
                for r in self.results
            ]
        }

        path = _PROJECT_ROOT / "advanced_formula_results_v3.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n  结果已保存: advanced_formula_results_v3.json")


# ═══════════════════════════════════════════════════════════
# 蓝球专用预测器
# ═══════════════════════════════════════════════════════════

class BlueBallPredictor:
    """蓝球专用预测器"""

    def __init__(self, draws: list):
        self.draws = draws

    def predict(self, top_n: int = 5) -> list:
        """预测Top-N蓝球"""
        pattern = blue_ball_pattern(self.draws, 300)

        scores = {}
        for b in range(1, 17):
            # 因素1: 遗漏接近平均周期
            omission = pattern["omissions"].get(b, 999)

            # 因素2: 周期性稳定性
            period_info = pattern["periods"].get(b, {})
            cv = period_info.get("cv", 999)
            appearances = period_info.get("appearances", 0)

            # 因素3: 近期频率趋势
            freq = pattern["freq"].get(b, 0)

            # 综合评分
            score = 0
            if cv < 999 and appearances >= 3:
                # 有周期性
                mean_period = period_info.get("mean_period", 16)
                proximity = 1.0 - abs(omission - mean_period) / mean_period
                score += max(0, proximity) * 0.5

            # 遗漏因子
            if omission < 30:
                score += 0.3
            elif omission < 60:
                score += 0.15

            scores[b] = score

        # 排序
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return ranked[:top_n]


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="高级公式开发引擎 V3.0")
    parser.add_argument("--blue-predict", action="store_true", help="只运行蓝球预测")
    parser.add_argument("--full", action="store_true", help="完整开发+蓝球预测")
    args = parser.parse_args()

    draws = load_history()
    print(f"数据: {len(draws)} 期 | 最新: #{draws[-1].period}")

    if args.blue_predict or args.full:
        print("\n" + "="*70)
        print("  蓝球专用预测器")
        print("="*70)
        predictor = BlueBallPredictor(draws)
        blue_preds = predictor.predict(top_n=5)
        print(f"\n  Top-5 蓝球预测:")
        for b, score in blue_preds:
            print(f"    蓝球 {b:02d} — 评分: {score:.3f}")

    if not args.blue_predict:
        developer = AdvancedFormulaDeveloper(draws)
        results = developer.develop_formulas()

        # 输出最佳公式的Top-6
        if results:
            best = results[0]
            print(f"\n  最佳公式的Top-10号码:")
            for i, n in enumerate(best.top_numbers[:10]):
                print(f"    {i+1}. 号码 {n:02d}")
