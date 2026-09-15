# -*- coding: utf-8 -*-
"""
Antigravity LLM创新 — Gemini分析器 V1.0

核心理念:
- Gemini不是代码生成器，是创意伙伴
- 它提出"规格"（spec），系统负责实现和验证
- 它提出的原语规格必须经过数据验证才会被采纳

用法:
    from llm_innovation.gemini_analyzer import GeminiAnalyzer

    analyzer = GeminiAnalyzer()
    if analyzer.available:
        specs = analyzer.propose_new_primitives(draws)
        # specs是原语规格列表，需要系统实现
"""
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from llm_innovation.llm_client import GeminiClient

_PROJECT_ROOT = Path(__file__).resolve().parent


class GeminiAnalyzer:
    """Gemini分析器 — 提出新原语规格"""

    SYSTEM_PROMPT = """你是一个彩票数据分析专家。你的任务是提出全新的"预测原语"规格。

规则:
1. 原语必须是对33个号码打分的新方法
2. 原语应该基于数据的结构性特征，不是简单的频率/遗漏
3. 每个原语需要: 名称、类别、描述、计算方法、参数
4. 不要输出代码，只输出规格
5. 类别可以是: temporal, relational, structural, spectral, geometric, chaotic

输出格式必须是JSON数组:
[
  {
    "name": "原语名称",
    "category": "类别",
    "description": "人类可读描述",
    "calculation_method": "计算方法说明",
    "parameters": {"参数名": "默认值"},
    "rationale": "为什么这个原语可能有效"
  }
]"""

    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or GeminiClient()

    def propose_new_primitives(self, draws: Any, n_specs: int = 5) -> List[Dict]:
        """
        让Gemini提出新的原语规格。

        Args:
            draws: 历史数据（用于构建上下文）
            n_specs: 希望提出的规格数量

        Returns:
            原语规格列表（JSON格式）
        """
        # 构建数据上下文
        context = self._build_context(draws)

        prompt = f"""请提出{n_specs}个全新的预测原语规格。

数据上下文:
{context}

要求:
- 这些原语不能是已知的数学函数（mod, sin, digit_sum等）
- 应该基于对彩票数据的深层结构理解
- 每个原语都应该有独特的视角
- 如果可能，参考以下信号:
  - Hurst指数显示强反持久性
  - 频谱检测到28期、50期周期
  - 互信息显示非线性依赖
"""

        if not self.client.available:
            print("[WARN] Gemini不可用，返回空规格列表")
            return []

        result = self.client.generate_content(prompt, self.SYSTEM_PROMPT)
        if not result:
            return []

        # 解析JSON
        try:
            # 尝试找到JSON数组
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                json_str = result[start:end]
                specs = json.loads(json_str)
                return specs
        except json.JSONDecodeError:
            print(f"[WARN] 解析Gemini输出失败: {result[:200]}")

        return []

    def analyze_failure_patterns(self, eliminated_hypotheses: List[Dict]) -> Dict:
        """
        让Gemini分析失败假设的模式。

        Args:
            eliminated_hypotheses: 被淘汰的假设列表

        Returns:
            失败模式分析
        """
        if not eliminated_hypotheses:
            return {"patterns": [], "recommendations": []}

        context = json.dumps(eliminated_hypotheses, indent=2, ensure_ascii=False)[:3000]

        prompt = f"""分析以下{len(eliminated_hypotheses)}个失败假设的根本原因:

{context}

请分类失败模式:
1. overfit: 过拟合 — 在训练集上表现好但测试集上差
2. noise_chase: 追逐噪声 — 捕捉的是随机波动
3. cliche: 陈词滥调 — 只是已知策略的变体
4. fragile: 脆弱 — 对参数微小变化极度敏感
5. spatial: 空间不合理 — 号码选择在空间分布上不合理
6. temporal: 时序不稳定 — 时序依赖不稳定

输出格式:
{{
  "patterns": [
    {{"type": "失败类型", "count": N, "examples": ["假设描述..."]}}
  ],
  "recommendations": ["建议..."]
}}

只输出JSON，不要其他文字。"""

        result = self.client.generate_content(prompt, self.SYSTEM_PROMPT)
        if not result:
            return {"patterns": [], "recommendations": []}

        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except json.JSONDecodeError:
            pass

        return {"patterns": [], "recommendations": []}

    def suggest_grammar_improvements(self, current_primitives: List[Dict]) -> List[Dict]:
        """
        让Gemini建议新的公式组合算子。

        Args:
            current_primitives: 当前原语列表

        Returns:
            新组合算子建议
        """
        prompt = f"""当前系统有{len(current_primitives)}个原语，使用以下组合算子:
- resonance (共振): 加权乘积
- cascade (级联): 筛选→精炼
- phase_align (相位对齐): 加权平均
- weighted_sum (加权和): 线性加权

请建议3-5个新的组合算子，每个算子应该有:
1. 名称
2. 数学含义
3. 适用场景
4. 与现有算子的区别

输出JSON数组:
[
  {{"name": "算子名", "math_meaning": "数学含义", "use_case": "适用场景", "difference": "与现有算子的区别"}},
  ...
]

只输出JSON。"""

        result = self.client.generate_content(prompt, self.SYSTEM_PROMPT)
        if not result:
            return []

        try:
            start = result.find("[")
            end = result.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except json.JSONDecodeError:
            pass

        return []

    def _build_context(self, draws: Any) -> str:
        """构建数据上下文"""
        n_draws = len(draws) if draws else 0

        # 加载已有信号
        signal_files = {
            "nonrandomness": _PROJECT_ROOT.parent / "nonrandomness_results.json",
            "position_prior": _PROJECT_ROOT.parent / "position_prior.json",
            "analysis_prior": _PROJECT_ROOT.parent / "analysis_prior.json",
        }

        signals = {}
        for name, path in signal_files.items():
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        signals[name] = json.load(f)
                except Exception:
                    pass

        context_lines = [f"数据规模: {n_draws} 期"]

        if "position_prior" in signals:
            deviations = signals["position_prior"].get("position_deviations", {})
            for pos, metrics in list(deviations.items())[:5]:
                hurst = metrics.get("hurst_dev", 0)
                if abs(hurst) > 0.1:
                    context_lines.append(f"  位置{pos}: Hurst偏差={hurst:.3f}")

        if "nonrandomness" in signals:
            n_signals = signals["nonrandomness"].get("signals_found", 0)
            context_lines.append(f"  非随机信号数: {n_signals}")

        return "\n".join(context_lines)
