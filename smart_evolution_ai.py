# -*- coding: utf-8 -*-
"""
AI驱动的智能公式演进引擎 V2.0
================================
连接LLM(创意生成) ↔ 公式语言(结构化表达) ↔ 演化引擎(筛选优化)

核心功能:
1. LLM分析历史公式表现，提出改进建议
2. 自动将LLM建议转化为公式变体
3. 智能选择哪些公式需要AI深度分析
"""
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm_innovation.llm_multi_client import LLMClient
from data_layer import load_history, get_latest_period
from formula_lang import get_default_primitives, FormulaGrammar
from formula_evolution import FormulaEvolutionEngine


logger = logging.getLogger("SmartEvolutionAI")


class AISmartEvolutionOrchestrator:
    """AI驱动的智能演进编排器"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.engine = None
        self.history_cache = deque(maxlen=100)  # 最近历史
        self.ai_analysis_depth = "balanced"  # quick/balanced/deep

        # 加载数据
        self._load_data()

    def _load_data(self):
        """加载历史数据"""
        try:
            self.history = load_history()
            self.legacy_periods = len(self.history)
            logger.info(f"[AI] 加载历史数据: {self.legacy_periods} 期")
        except Exception as e:
            logger.warning(f"[AI] 数据加载失败: {e}")
            self.history = []
            self.legacy_periods = 0

    def analyze_and_enhance(self, evolution_result: Dict) -> Dict:
        """
        分析演化结果，获取AI深度反馈

        Args:
            evolution_result: 最近一轮演化的结果

        Returns:
            增强后的分析结果和建议
        """
        if not self.llm_client.available:
            return {"ai_enhancements": "LLM不可用", "suggestions": []}

        # 准备分析Prompt
        best_formula = evolution_result.get("best_formula", "")
        best_score = evolution_result.get("best_score", 0)
        avg_hits = evolution_result.get("best_hits", 0)
        hits_vs_random = evolution_result.get("beats_random", False)

        # 分析历史表现
        recent_history = list(self.history_cache)[-10:]  # 最近10轮

        prompt = f"""
你是双色球AI公式演化专家，请分析当前公式表现并给出改进建议。

当前最佳公式: {best_formula}
综合得分: {best_score:.4f}
平均命中: {avg_hits:.2f} (随机期望: 1.09)
击败随机: {hits_vs_random}

最近5轮演化历史:
{json.dumps([{'formula': h.get('best_formula'), 'score': h.get('best_score')} for h in recent_history[-5:]], ensure_ascii=False, indent=2)}

请从以下角度分析:
1. 当前公式的主要特征是什么? (时序/结构/关系等)
2. 是否存在哪些潜在的改进方向?
3. 是否可以建议新的公式语言原语组合?
4. 具体的改进建议(用JSON格式):
   {{
     "insight": "分析结论",
     "primitives_to_try": ["原语1", "原语2"],
     "mutation_strategy": "建议的变异方法",
     "new_combination": "新的公式组合思路"
   }}

请用中文回答，保持简洁专业。
"""

        system_prompt = """
你是双色球公式演化专家。熟悉公式语言系统的36个原语，包括:
- 时序: PeriodicEcho, RecencyGradient, SeasonalResonance
- 关系: CooccurrenceAffinity, MutualExclusionScore, PairOrbit  
- 结构: BinaryTopology, DigitManifold, PositionSignature
- 频谱: SpectralPower, WaveletCoherence
- 几何: SphereProjection, DistanceCluster
- 混沌: AttractorDistance, LyapunovSignal
- 序列模式: SumRangeTracker, GapPatternAnalyzer, TrendReversalDetector
- 高阶统计: SkewnessSignal, KurtosisSignal, TailRiskSignal
- 信息论: MutualInformationPair, ResidualSignal, ConditionalProbabilityMatrix

分析双色球数据特征，提出具体的公式改进方案。
"""

        try:
            response = self.llm_client.generate_content(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=1500,
                temperature=0.7
            )

            if response:
                # 尝试解析JSON结果（支持嵌套大括号）
                suggestions = []
                parsed = self._extract_json(response)
                if parsed:
                    suggestions.append(parsed)
                else:
                    suggestions.append({"raw_response": response})

                return {
                    "ai_enhancements": response[:500],
                    "suggestions": suggestions,
                    "analysis_time": datetime.now().isoformat()
                }
        except Exception as e:
            logger.warning(f"[AI] 智能分析失败: {e}")

        return {"ai_enhancements": "分析失败", "suggestions": []}

    def generate_formula_variants(self, base_formula: str, count: int = 5) -> List[str]:
        """
        使用AI生成公式变体

        Args:
            base_formula: 基础公式
            count: 生成数量

        Returns:
            公式变体列表
        """
        if not self.llm_client.available:
            return []

        prompt = f"""
基于公式 "{base_formula}"，生成 {count} 个改进变体。

公式语言使用组合算子:
- weighted_sum: 线性加权
- resonance: 共振(加权乘积)
- cascade: 级联(筛选→精炼)
- phase_align: 相位对齐(加权平均)

请直接输出公式列表，每行一个:
"""

        try:
            response = self.llm_client.generate_content(
                prompt=prompt,
                max_tokens=500,
                temperature=0.8
            )

            if response:
                variants = []
                for line in response.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and 'formula' not in line.lower():
                        variants.append(line)
                return variants[:count]
        except Exception as e:
            logger.warning(f"[AI] 生成变体失败: {e}")

        return []

    def should_use_ai_analysis(self, current_generation: int, population_elite: List[Dict]) -> bool:
        """
        决策何时使用AI深度分析

        Returns:
            bool: 是否需要AI分析
        """
        # 前3代不分析
        if current_generation < 3:
            return False

        # 连续 stagnation 超过5代时分析
        if len(self.history_cache) >= 5:
            scores = [h.get("best_score", 0) for h in list(self.history_cache)[-5:]]
            if max(scores) == min(scores) and max(scores) > 0.4:
                return True  # 停滞

        # 种群精英分散时分析
        elite_scores = [f.get("score", 0) for f in population_elite]
        if max(elite_scores) - min(elite_scores) > 0.1:
            return True

        return False

    def run_evolution_with_ai(self, generations: int = 5, population: int = 30) -> Dict:
        """
        运行带AI增强的演化 — 使用真实引擎API (initialize_population + evolve)

        Returns:
            演化结果
        """
        logger.info(f"[AI-ROCKET] 开始AI增强演生 ({generations}代, 种群{population})")

        if not self.history:
            logger.error("[AI] 无历史数据，终止")
            return {"error": "no_history"}

        # 1. 运行标准演化（调用真实引擎API）
        try:
            self.engine = FormulaEvolutionEngine(self.history)
            self.engine.initialize_population(size=population)
            self.engine.evolve(generations=generations, population_size=population)
            self.engine.save_history()
            best = self.engine.get_best_formula() or {}
        except Exception as e:
            logger.error(f"[AI] 引擎演化失败: {e}")
            return {"error": str(e)}

        # 2. 组装结果
        result = {
            "best_formula": best.get("formula").name if best.get("formula") else None,
            "best_score": best.get("score", 0),
            "best_hits": best.get("avg_hits", 0),
            "beats_random": best.get("beats_random", False),
        }

        # 3. 缓存结果
        self.history_cache.append(result)

        # 4. 判断是否需要AI分析
        if self.should_use_ai_analysis(generations, [result]):
            logger.info("[AI] 检测到需要AI深度分析")
            ai_insights = self.analyze_and_enhance(result)
            result["ai_suggestions"] = ai_insights

            # 5. 影子模式生成变体（仅建议，不自动注入种群）
            if self.llm_client.available:
                variants = self.generate_formula_variants(
                    result.get("best_formula", "") or "",
                    count=3
                )
                if variants:
                    logger.info(f"[AI] 生成变体建议: {variants[:2]}")
                    result["ai_variants"] = variants

        # 6. 保存增强结果（仅审计用途）
        self._save_ai_enhanced_state(result)

        return result

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict]:
        """从LLM回复中提取JSON对象（支持嵌套大括号和markdown代码块）。"""
        import re
        # 优先从```json代码块提取
        block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        candidates = [block.group(1)] if block else []
        # 再尝试括号配对扫描（支持嵌套）
        start = text.find('{')
        while start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        candidates.append(text[start:i + 1])
                        break
            start = text.find('{', start + 1)
        # 返回第一个合法JSON
        for cand in candidates:
            try:
                obj = json.loads(cand)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
        return None

    def _save_ai_enhanced_state(self, result: Dict):
        """保存AI增强状态"""
        try:
            state_file = PROJECT_ROOT / "ai_enhanced_state.json"

            # 加载现有数据
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"iterations": []}

            # 添加本轮
            data["iterations"].append({
                "timestamp": datetime.now().isoformat(),
                "generation": len(data.get("iterations", [])),
                "best_formula": result.get("best_formula"),
                "best_score": result.get("best_score"),
                "ai_analyzed": "ai_suggestions" in result,
                "model_used": self.llm_client.active_model if hasattr(self.llm_client, 'active_model') else None
            })

            # 保留最近50轮
            if len(data["iterations"]) > 50:
                data["iterations"] = data["iterations"][-50:]

            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.warning(f"[AI] 保存状态失败: {e}")


def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser(description="AI增强演进")
    parser.add_argument("--generations", type=int, default=5, help="演化代数")
    parser.add_argument("--population", type=int, default=30, help="种群大小")
    parser.add_argument("--deep", action="store_true", help="深度AI分析")
    args = parser.parse_args()

    orchestrator = AISmartEvolutionOrchestrator()

    if args.deep:
        orchestrator.ai_analysis_depth = "deep"

    result = orchestrator.run_evolution_with_ai(
        generations=args.generations,
        population=args.population
    )

    print(f"\n[AI-ROCKET] 演化完成!")
    print(f"   最佳公式: {result.get('best_formula')}")
    print(f"   最佳得分: {result.get('best_score', 0):.4f}")
    print(f"   击败随机: {result.get('beats_random', False)}")

    if result.get("ai_suggestions"):
        print(f"   AI建议: {result['ai_suggestions'].get('insight', '无')}")


if __name__ == "__main__":
    main()