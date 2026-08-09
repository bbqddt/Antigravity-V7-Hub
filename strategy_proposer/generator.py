# -*- coding: utf-8 -*-
"""
Antigravity 策略框架 — 假设生成器 V1.0

核心理念:
- 从数据信号中自动生成可测试的假设
- 信号来源: nonrandomness_results.json, position_prior.json, analysis_prior.json
- 每个信号都对应一个或多个假设模板
- 生成的假设数量可配置

用法:
    from strategy_proposer.generator import HypothesisGenerator

    gen = HypothesisGenerator()
    hypotheses = gen.generate_from_signals()  # 从所有信号生成
    hypotheses = gen.generate_from_hurst()    # 只从Hurst信号生成
"""
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any

from strategy_proposer.hypothesis import Hypothesis, HypothesisTemplate

_PROJECT_ROOT = Path(__file__).resolve().parent


class HypothesisGenerator:
    """假设生成器 — 从数据信号生成可测试假设"""

    def __init__(self):
        self.templates = HypothesisTemplate.get_all_templates()
        self._signal_files = {
            "nonrandomness": _PROJECT_ROOT / ".." / "nonrandomness_results.json",
            "position_prior": _PROJECT_ROOT / ".." / "position_prior.json",
            "analysis_prior": _PROJECT_ROOT / ".." / "analysis_prior.json",
            "attribute_freq": _PROJECT_ROOT / ".." / "attribute_frequencies.json",
            "number_profiles": _PROJECT_ROOT / ".." / "number_profiles.json",
            "time_existence": _PROJECT_ROOT / ".." / "time_existence_test.json",
        }

    def generate_from_signals(self) -> List[Hypothesis]:
        """从所有可用信号生成假设"""
        hypotheses = []

        hypotheses.extend(self._generate_from_nonrandomness())
        hypotheses.extend(self._generate_from_position_prior())
        hypotheses.extend(self._generate_from_analysis_prior())
        hypotheses.extend(self._generate_from_attribute_freq())
        hypotheses.extend(self._generate_from_time_existence())

        # 去重（基于statement相似度）
        hypotheses = self._deduplicate(hypotheses)

        return hypotheses

    def _generate_from_nonrandomness(self) -> List[Hypothesis]:
        """从非随机性检测结果生成假设"""
        hypotheses = []
        data = self._load_json("nonrandomness")
        if not data:
            return hypotheses

        deviations = data.get("deviations", [])
        for dev in deviations:
            test_type = dev.get("type", "")
            name = dev.get("name", "")
            deviation = dev.get("deviation", 0)

            # 根据偏离类型生成不同假设
            if "hurst" in test_type:
                h = self._make_hypothesis(
                    "spectral_cycle",
                    {"n": name, "period": str(int(deviation * 100)), "hurst": str(round(deviation, 2))},
                    f"Hurst指数在位置{name}显示{deviation:.2f}的偏离 → 可能存在{int(deviation*100)}期周期",
                )
                if h:
                    hypotheses.append(h)

            elif "spectral" in test_type:
                h = self._make_hypothesis(
                    "spectral_cycle",
                    {"n": name, "period": str(int(deviation * 50)), "freq": str(round(deviation, 3))},
                    f"频谱分析在位置{name}检测到周期信号 → 偏离={deviation:.3f}",
                )
                if h:
                    hypotheses.append(h)

            elif "mi" in test_type or "mutual_information" in test_type.lower():
                h = self._make_hypothesis(
                    "cooccurrence_pair",
                    {"n_a": name, "cooccur_freq": str(round(deviation, 3)), "expected": "0.09"},
                    f"互信息在位置{name}显示{deviation:.3f} → 号码间存在非线性依赖",
                )
                if h:
                    hypotheses.append(h)

            elif "pe" in test_type:
                h = self._make_hypothesis(
                    "positional_bias",
                    {"pos": name, "range_label": "ordered", "range_min": "1", "range_max": "33"},
                    f"排列熵在位置{name}显示{deviation:.3f} → 序列有序性偏离随机",
                )
                if h:
                    hypotheses.append(h)

            elif "lz" in test_type:
                h = self._make_hypothesis(
                    "structural",
                    {"n": name, "binary_feature": "lz_complexity", "freq": str(round(deviation, 3))},
                    f"LZ复杂度在位置{name}显示{deviation:.3f} → 序列算法性偏离随机",
                )
                if h:
                    hypotheses.append(h)

        return hypotheses

    def _generate_from_position_prior(self) -> List[Hypothesis]:
        """从位置先验生成假设"""
        hypotheses = []
        data = self._load_json("position_prior")
        if not data:
            return hypotheses

        deviations = data.get("position_deviations", {})

        for pos, metrics in deviations.items():
            hurst_dev = metrics.get("hurst_dev", 0)
            if abs(hurst_dev) > 0.1:
                direction = "均值回归" if hurst_dev > 0 else "趋势延续"
                h = self._make_hypothesis(
                    "omission_rebound",
                    {"pos": pos, "omit_threshold": str(int(abs(hurst_dev) * 20)),
                     "hurst": str(round(hurst_dev, 2)), "window": "50"},
                    f"位置{pos}的Hurst偏差={hurst_dev:.2f} → {direction}信号强",
                )
                if h:
                    hypotheses.append(h)

            runs_z = metrics.get("runs_z", 0)
            if abs(runs_z) > 0.5:
                h = self._make_hypothesis(
                    "positional_bias",
                    {"pos": pos, "range_label": "run_anomaly", "range_min": "1", "range_max": "33"},
                    f"位置{pos}的游程检验z={runs_z:.2f} → 游程模式异常",
                )
                if h:
                    hypotheses.append(h)

        # 蓝球特殊处理
        blue_metrics = deviations.get("blue", {})
        blue_hurst = blue_metrics.get("hurst_dev", 0)
        if abs(blue_hurst) > 0.1:
            h = self._make_hypothesis(
                "blue_hurst_mean_revert",
                {"hurst": str(round(blue_hurst, 2)), "window": "30"},
                f"蓝球Hurst偏差={blue_hurst:.2f} → 强均值回归信号",
            )
            if h:
                hypotheses.append(h)

        return hypotheses

    def _generate_from_analysis_prior(self) -> List[Hypothesis]:
        """从共享先验生成假设"""
        hypotheses = []
        data = self._load_json("analysis_prior")
        if not data:
            return hypotheses

        if data.get("has_structure", False):
            h = self._make_hypothesis(
                "periodic_resonance",
                {"pos": "1-6", "hurst_range": "[0.1, 0.4]", "num_set": "all", "window": "100"},
                "共享先验检测到数据结构 → 多位置可能存在协同模式",
            )
            if h:
                hypotheses.append(h)

        return hypotheses

    def _generate_from_attribute_freq(self) -> List[Hypothesis]:
        """从属性频率生成假设"""
        hypotheses = []
        data = self._load_json("attribute_freq")
        if not data:
            return hypotheses

        # 找偏差最大的属性
        sorted_items = sorted(data.items(), key=lambda x: -abs(x[1].get("deviation", 0)))[:5]
        for name, stats in sorted_items:
            deviation = stats.get("deviation", 0)
            if abs(deviation) > 0.05:
                h = self._make_hypothesis(
                    "digit_sum_cluster" if "digit" in name else "structural",
                    {"sum_range": name, "freq": str(round(stats.get("hit_rate", 0), 3)),
                     "expected": str(round(stats.get("expected", 0.18), 3))},
                    f"属性'{name}'的命中率={stats.get('hit_rate', 0):.3f} vs 期望={stats.get('expected', 0):.3f} → 偏差={deviation:.3f}",
                )
                if h:
                    hypotheses.append(h)

        return hypotheses

    def _generate_from_time_existence(self) -> List[Hypothesis]:
        """从时间存在性检验生成假设"""
        hypotheses = []
        data = self._load_json("time_existence")
        if not data:
            return hypotheses

        summary = data.get("summary", {})
        failed = summary.get("failed", 0)

        if failed >= 4:
            h = self._make_hypothesis(
                "periodic_resonance",
                {"pos": "all", "hurst_range": "[0, 0.5]", "num_set": "structured", "window": "all"},
                f"时间存在性检验中{failed}项证伪 → 数据有强烈非随机结构",
            )
            if h:
                hypotheses.append(h)

        return hypotheses

    def _make_hypothesis(self, template_name: str, params: Dict, statement: str) -> Optional[Hypothesis]:
        """从模板和参数创建假设"""
        try:
            template_map = {t.name: t for t in self.templates}
            template = template_map.get(template_name)
            if template:
                h = template.fill(params)
                h.statement = statement  # 覆盖为中文描述
                return h
        except Exception:
            pass
        return None

    def _load_json(self, key: str) -> Optional[Dict]:
        """加载JSON文件"""
        path = self._signal_files.get(key)
        if not path or not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _deduplicate(self, hypotheses: List[Hypothesis], threshold: float = 0.8) -> List[Hypothesis]:
        """去重 — 基于statement相似度"""
        if not hypotheses:
            return hypotheses

        result = [hypotheses[0]]
        for h in hypotheses[1:]:
            is_dup = False
            for existing in result:
                if self._similarity(h.statement, existing.statement) > threshold:
                    is_dup = True
                    break
            if not is_dup:
                result.append(h)
        return result

    @staticmethod
    def _similarity(s1: str, s2: str) -> float:
        """简化的字符串相似度（基于共同词）"""
        words1 = set(s1.lower().split())
        words2 = set(s2.lower().split())
        if not words1 or not words2:
            return 0
        return len(words1 & words2) / max(len(words1 | words2), 1)
