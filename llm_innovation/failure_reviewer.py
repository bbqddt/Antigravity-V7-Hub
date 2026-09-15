# -*- coding: utf-8 -*-
"""
Antigravity LLM创新 — 失败审查器 V1.0

核心理念:
- 失败也是数据。记录和分析失败原因，指导后续创新方向。
- 失败分类: overfit / noise_chase / cliche / fragile / spatial / temporal

用法:
    from llm_innovation.failure_reviewer import FailureReviewer

    reviewer = FailureReviewer()
    classification = reviewer.classify_failure(hypothesis, result)
    lesson = reviewer.extract_lesson(classification)
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from llm_innovation.llm_client import GeminiClient

_PROJECT_ROOT = Path(__file__).resolve().parent


class FailureReviewer:
    """失败审查器 — 分类失败原因并提取教训"""

    FAILURE_TYPES = {
        "overfit": "过拟合 — 在训练集上表现好但测试集上差",
        "noise_chase": "追逐噪声 — 捕捉的是随机波动而非信号",
        "cliche": "陈词滥调 — 只是已知策略的变体，没有创新",
        "fragile": "脆弱 — 对参数微小变化极度敏感",
        "spatial": "空间不合理 — 号码选择在空间分布上不合理",
        "temporal": "时序不稳定 — 时序依赖不稳定",
        "insufficient_data": "数据不足 — 验证轮数太少",
        "below_random": "低于随机 — 甚至不如随机猜测",
    }

    LESSONS = {
        "overfit": "减少参数复杂度，增加正则化，使用更严格的交叉验证",
        "noise_chase": "检查信号是否来自统计涨落，增加验证窗口",
        "cliche": "跳出已知策略框架，尝试全新的原语类别",
        "fragile": "增加参数鲁棒性测试，使用贝叶斯方法估计不确定性",
        "spatial": "检查号码的空间分布是否合理（区间覆盖、跨度等）",
        "temporal": "检查时序依赖是否稳定，使用滚动窗口验证",
        "insufficient_data": "增加验证轮数或使用更大的训练窗口",
        "below_random": "彻底重新设计该假设，或将其作为反面教材",
    }

    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or GeminiClient()

    def classify(self, hypothesis: Any, result: Dict) -> str:
        """
        分类一个假设的失败原因。

        Args:
            hypothesis: 假设对象
            result: 验证结果

        Returns:
            失败类型
        """
        if result.get("avg_hits", 0) < 1.0:
            return "below_random"

        if result.get("rounds", 0) < 3:
            return "insufficient_data"

        # 基于结果的启发式分类
        avg = result.get("avg_hits", 0)
        std = result.get("std", 1)
        p_value = result.get("p_value", 1.0)
        stable = result.get("stable", 0)

        if std > avg * 0.5:
            return "fragile"

        if p_value > 0.3 and avg < 1.5:
            return "noise_chase"

        if result.get("elimination_reason") == "below_random_baseline":
            return "below_random"

        # 默认分类
        return "overfit"

    def extract_lessons(self, failure_type: str) -> List[str]:
        """
        从失败类型中提取教训。

        Args:
            failure_type: 失败类型

        Returns:
            教训列表
        """
        lessons = [self.LESSONS.get(failure_type, "重新审视假设的基本前提")]
        return lessons

    def review_batch(self, hypotheses_results: List[Dict]) -> Dict:
        """
        批量审查假设的失败结果。

        Args:
            hypotheses_results: [{"hypothesis": {...}, "result": {...}}, ...]

        Returns:
            审查报告
        """
        classification_counts = {}
        all_lessons = {}

        for item in hypotheses_results:
            h = item.get("hypothesis", {})
            r = item.get("result", {})
            failure_type = self.classify(h, r)

            classification_counts[failure_type] = classification_counts.get(failure_type, 0) + 1

            if failure_type not in all_lessons:
                all_lessons[failure_type] = self.extract_lessons(failure_type)

        # 排序: 最常见的失败类型排在前面
        sorted_counts = sorted(classification_counts.items(), key=lambda x: -x[1])

        report = {
            "total_reviewed": len(hypotheses_results),
            "classification_counts": dict(sorted_counts),
            "lessons": all_lessons,
            "top_recommendation": sorted_counts[0][0] if sorted_counts else "none",
            "reviewed_at": datetime.now().isoformat(),
        }

        return report

    def suggest_improvements(self, report: Dict) -> List[str]:
        """
        根据审查报告提出改进建议。

        Args:
            report: 审查报告

        Returns:
            改进建议列表
        """
        recommendations = []

        top_failure = report.get("top_recommendation", "")
        if top_failure == "overfit":
            recommendations.append("增加交叉验证轮数，减少公式复杂度")
            recommendations.append("使用正则化方法防止过拟合")
        elif top_failure == "noise_chase":
            recommendations.append("检查信号是否来自统计涨落")
            recommendations.append("增加验证窗口大小")
        elif top_failure == "cliche":
            recommendations.append("尝试全新的原语类别，跳出已知框架")
            recommendations.append("使用LLM提出创新假设")
        elif top_failure == "fragile":
            recommendations.append("增加参数鲁棒性测试")
            recommendations.append("使用贝叶斯方法估计不确定性")
        elif top_failure == "below_random":
            recommendations.append("彻底重新设计该假设")
            recommendations.append("将其作为反面教材，分析为什么无效")

        return recommendations

    def to_gemini(self, report: Dict) -> Optional[str]:
        """
        将审查报告发送给Gemini进行深入分析。

        Returns:
            Gemini的分析结果，失败时返回None
        """
        if not self.client.available:
            return None

        prompt = f"""以下是{report['total_reviewed']}个假设的失败审查报告:

失败分类: {json.dumps(report['classification_counts'], ensure_ascii=False)}

顶级失败原因: {report['top_recommendation']}

请给出:
1. 对失败模式的深入分析
2. 针对性的改进建议
3. 下一步行动方向

只输出JSON:
{{
  "analysis": "分析",
  "suggestions": ["建议1", "建议2", ...],
  "next_steps": ["步骤1", "步骤2", ...]
}}

只输出JSON，不要其他文字。"""

        return self.client.generate_content(prompt)
