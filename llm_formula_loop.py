# -*- coding: utf-8 -*-
"""
LLM → Formula 反馈闭环系统 V1.0
================================

核心理念:
- LLM 分析金库中的优质公式、性能模式、失败案例
- 基于分析提出新原语建议、组合策略优化、参数调整方向
- 自动将建议转化为可执行的公式/原语，注入演进引擎
- 形成: 演进 → 评估 → LLM分析 → 新公式 → 演进 的闭环

集成位置: formula_evolution.py 每 N 代调用一次
"""

import sys
import os
import json
import time
import logging
import random
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

from unified_llm_client import UnifiedLLMClient, get_client
from data_layer import load_history, Draw

logger = logging.getLogger("LLMFormulaLoop")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


class FormulaVaultAnalyzer:
    """公式金库分析器 - 从演进历史中提取模式"""
    
    def __init__(self, draws: List[Draw]):
        self.draws = draws
        self.history_file = _PROJECT_ROOT / "formula_evolution_history.json"
        self.performance_file = _PROJECT_ROOT / "evolution_performance_log.json"
    
    def load_vault(self) -> Dict:
        """加载完整金库数据"""
        data = {
            "history": [],
            "performance": [],
            "best_formulas": [],
            "failed_patterns": [],
            "primitive_usage": Counter(),
            "operator_usage": Counter(),
        }
        
        # 加载演进历史
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    hist_data = json.load(f)
                    # 历史文件格式: {"history": [...], "best_formula": "...", ...}
                    if isinstance(hist_data, dict) and "history" in hist_data:
                        data["history"] = hist_data["history"]
                    elif isinstance(hist_data, list):
                        data["history"] = hist_data
            except Exception as e:
                logger.warning(f"加载历史失败: {e}")
        
        # 加载性能日志
        if self.performance_file.exists():
            try:
                with open(self.performance_file, 'r', encoding='utf-8') as f:
                    perf_data = json.load(f)
                    if isinstance(perf_data, dict) and "history" in perf_data:
                        data["performance"] = perf_data["history"]
                    elif isinstance(perf_data, list):
                        data["performance"] = perf_data
                    else:
                        data["performance"] = [perf_data]
            except:
                pass
        
        # 提取最佳公式 - 从历史的 top5 中收集
        all_formulas = []
        for gen_record in data["history"]:
            for f in gen_record.get("top5", []):
                all_formulas.append(f)
        
        # 按分数排序
        all_formulas.sort(key=lambda x: -x.get('score', 0))
        data["best_formulas"] = all_formulas[:20]
        
        # 提取失败模式 (分数<0.3 的)
        data["failed_patterns"] = [f for f in all_formulas if f.get('score', 0) < 0.3][:10]
        
        # 由于历史中没有完整的公式对象，只能从名称推断原语/操作符
        # 简单启发式：从名称解析
        for f in all_formulas:
            name = f.get('name', '')
            # 解析操作符
            for op in ['phasealign', 'resonance', 'cascade', 'weighted_sum']:
                if op in name.lower():
                    data["operator_usage"][op] += 1
                    break
            # 解析可能的原语 (简化)
            # 实际需要从完整公式对象获取
        
        return data
    
    def analyze_patterns(self, vault: Dict) -> Dict:
        """分析金库中的模式"""
        analysis = {
            "top_primitives": [],
            "avoid_primitives": [],
            "best_operators": [],
            "success_patterns": [],
            "failure_patterns": [],
            "recommendations": [],
        }
        
        # Top 原语
        if vault["primitive_usage"]:
            total = sum(vault["primitive_usage"].values())
            for prim, count in vault["primitive_usage"].most_common(10):
                analysis["top_primitives"].append({
                    "name": prim,
                    "count": count,
                    "frequency": round(count / total * 100, 1),
                })
        
        # 最佳操作符
        if vault["operator_usage"]:
            for op, count in vault["operator_usage"].most_common(4):
                analysis["best_operators"].append({"operator": op, "count": count})
        
        # 成功模式 - 从最佳公式中提取
        for f in vault["best_formulas"][:5]:
            formula_obj = f.get('formula')
            if formula_obj:
                analysis["success_patterns"].append({
                    "formula_name": formula_obj.name if hasattr(formula_obj, 'name') else 'unknown',
                    "score": f.get('score', 0),
                    "avg_hits": f.get('avg_hits', 0),
                    "avg_brier": f.get('avg_brier', 0),
                    "primitives": [p.name for p in formula_obj.primitives] if hasattr(formula_obj, 'primitives') else [],
                })
        
        # 失败模式
        for f in vault["failed_patterns"][:3]:
            formula_obj = f.get('formula')
            if formula_obj:
                analysis["failure_patterns"].append({
                    "formula_name": formula_obj.name if hasattr(formula_obj, 'name') else 'unknown',
                    "score": f.get('score', 0),
                    "primitives": [p.name for p in formula_obj.primitives] if hasattr(formula_obj, 'primitives') else [],
                })
        
        return analysis
    
    def generate_llm_prompt(self, vault: Dict, analysis: Dict) -> str:
        """生成发送给 LLM 的提示词"""
        # 构建简化的金库摘要
        last_hist = vault['history'][-1] if vault['history'] else {}
        last_perf = vault['performance'][-1] if vault['performance'] else {}
        
        summary = f"""
=== Antigravity 公式金库分析报告 ===

【数据概况】
- 总演进代数: {len(vault['history'])}
- 种群规模: {last_hist.get('population_size', 0)}
- 历史最佳分数: {last_hist.get('best_score', 0)}
- 最近最佳命中: {last_perf.get('best_avg_hits', 0)}

【Top 10 原语使用频率】
"""
        for p in analysis["top_primitives"]:
            summary += f"  {p['name']}: {p['count']}次 ({p['frequency']}%)\n"
        
        summary += "\n【最佳操作符】\n"
        for op in analysis["best_operators"]:
            summary += f"  {op['operator']}: {op['count']}次\n"
        
        summary += "\n【Top 5 成功公式】\n"
        for i, f in enumerate(analysis["success_patterns"]):
            summary += f"  {i+1}. {f['formula_name']} - Score:{f['score']:.4f}\n"
            summary += f"     原语组合: {', '.join(f['primitives'])}\n"
        
        summary += "\n【Bottom 3 失败公式】\n"
        for f in analysis["failure_patterns"]:
            summary += f"  {f['formula_name']} - Score:{f['score']:.4f}\n"
            summary += f"     原语组合: {', '.join(f['primitives'])}\n"
        
        summary += """
=== 任务 ===
请基于以上分析，提出 3-5 条具体的改进建议，格式如下：

{
  "recommendations": [
    {
      "type": "new_primitive|operator_adjust|parameter_tune|combination_strategy",
      "priority": "high|medium|low",
      "description": "具体建议描述",
      "actionable": "可执行的具体动作",
      "expected_impact": "预期影响"
    }
  ],
  "new_primitive_proposals": [
    {
      "name": "原语名称",
      "category": "时序|关系|结构|频谱|几何|混沌|序列模式|组合特征|高阶统计|跨期记忆|多尺度|环境感知|统计|信息论",
      "logic_description": "核心逻辑描述",
      "parameters": ["参数1", "参数2"],
      "expected_synergy": "与现有原语的协同预期"
    }
  ]
}

重点关注:
1. 哪些原语组合效果好？为何？
2. 失败公式的共同缺陷是什么？
3. 需要什么新原语填补空白？
4. 操作符参数如何调优？
5. 变异策略如何改进？
"""
        return summary


class LLMFormulaAdvisor:
    """LLM 公式顾问 - 调用 LLM 并解析建议"""
    
    def __init__(self):
        self.client = get_client()
        self.analyzer = None
    
    def set_draws(self, draws: List[Draw]):
        self.analyzer = FormulaVaultAnalyzer(draws)
    
    def get_recommendations(self) -> Dict:
        """获取 LLM 建议"""
        if not self.analyzer:
            return {"recommendations": [], "new_primitive_proposals": []}
        
        # 加载金库
        vault = self.analyzer.load_vault()
        if not vault["history"]:
            return {"recommendations": [], "new_primitive_proposals": []}
        
        # 分析模式
        analysis = self.analyzer.analyze_patterns(vault)
        
        # 生成提示词
        prompt = self.analyzer.generate_llm_prompt(vault, analysis)
        
        # 调用 LLM
        logger.info("请求 LLM 分析公式金库...")
        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat(messages, max_tokens=3000, temperature=0.7)
        
        if not response:
            logger.warning("LLM 响应为空")
            return {"recommendations": [], "new_primitive_proposals": []}
        
        # 解析 JSON
        try:
            # 提取 JSON 部分
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response)
            
            logger.info(f"LLM 返回建议: {len(result.get('recommendations', []))} 条策略, {len(result.get('new_primitive_proposals', []))} 个新原语")
            return result
            
        except Exception as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            logger.debug(f"原始响应: {response[:500]}")
            return {"recommendations": [], "new_primitive_proposals": []}


class FormulaLoopIntegrator:
    """公式闭环集成器 - 将 LLM 建议注入演进引擎"""
    
    def __init__(self, draws: List[Draw]):
        self.draws = draws
        self.advisor = LLMFormulaAdvisor()
        self.advisor.set_draws(draws)
        self.last_analysis_gen = 0
        self.analysis_interval = 5  # 每 5 代分析一次
    
    def should_analyze(self, current_generation: int) -> bool:
        return current_generation > 0 and current_generation % self.analysis_interval == 0 and current_generation != self.last_analysis_gen
    
    def inject_recommendations(self, engine, recommendations: Dict) -> int:
        """将建议注入演进引擎"""
        injected = 0
        
        # 1. 注入新原语建议
        for prop in recommendations.get("new_primitive_proposals", []):
            if self._create_primitive_from_proposal(prop):
                injected += 1
        
        # 2. 调整变异策略
        for rec in recommendations.get("recommendations", []):
            if rec.get("type") == "parameter_tune":
                self._apply_parameter_tuning(engine, rec)
                injected += 1
            elif rec.get("type") == "combination_strategy":
                self._apply_combination_strategy(engine, rec)
                injected += 1
            elif rec.get("type") == "operator_adjust":
                self._apply_operator_adjustment(engine, rec)
                injected += 1
        
        return injected
    
    def _create_primitive_from_proposal(self, proposal: Dict) -> bool:
        """根据提案动态创建新原语"""
        name = proposal.get("name", "").strip()
        if not name:
            return False
        
        # 检查是否已存在
        from formula_lang.primitive import PrimitiveFactory
        factory = PrimitiveFactory()
        if name in [p.name for p in factory.create_all()]:
            logger.info(f"原语 {name} 已存在，跳过")
            return False
        
        # 生成原语代码模板
        code_template = self._generate_primitive_code(proposal)
        
        # 写入新原语文件
        prim_file = _PROJECT_ROOT / "formula_lang" / f"primitive_{name.lower()}.py"
        try:
            with open(prim_file, 'w', encoding='utf-8') as f:
                f.write(code_template)
            logger.info(f"创建新原语文件: {prim_file}")
            
            # 更新 __init__.py 导出
            self._update_init_export(name)
            return True
        except Exception as e:
            logger.error(f"创建原语失败: {e}")
            return False
    
    def _generate_primitive_code(self, proposal: Dict) -> str:
        """生成原语代码"""
        name = proposal.get("name", "NewPrimitive")
        category = proposal.get("category", "统计")
        logic = proposal.get("logic_description", "")
        params = proposal.get("parameters", [])
        
        param_str = ", ".join([f"{p}: float = 1.0" for p in params]) if params else ""
        param_assign = "\n        ".join([f"self.{p} = {p}" for p in params]) if params else "pass"
        
        return f'''# -*- coding: utf-8 -*-
"""
{name} - LLM 提案生成的原语
类别: {category}
逻辑: {logic}
"""
import numpy as np
from formula_lang.primitive import Primitive

class {name}(Primitive):
    """{logic}"""
    
    def __init__(self, {param_str}):
        super().__init__("{name}")
        {param_assign}
        self.category = "{category}"
    
    def compute(self, draws) -> np.ndarray:
        """
        核心计算逻辑 - 需要根据具体提案实现
        返回: 每个号码的得分数组 (shape: [33])
        """
        # TODO: 实现具体逻辑
        # 示例: 基于历史数据计算特征得分
        from data_layer import Draw
        if not draws:
            return np.ones(33) / 33
        
        # 占位实现 - 返回均匀分布
        scores = np.ones(33) / 33
        return scores

# 注册到工厂
from formula_lang.primitive import PrimitiveFactory
PrimitiveFactory.register("{name}", {name})
'''
    
    def _update_init_export(self, name: str):
        """更新 __init__.py 导出新原语"""
        init_file = _PROJECT_ROOT / "formula_lang" / "__init__.py"
        try:
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 添加导入
            import_line = f"from .primitive_{name.lower()} import {name}\n"
            if import_line not in content:
                # 在最后一个 import 后添加
                lines = content.split('\n')
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith('from .primitive_') or line.startswith('from .evaluator'):
                        insert_idx = i
                lines.insert(insert_idx + 1, import_line.rstrip())
                content = '\n'.join(lines)
            
            # 添加到 __all__
            if '__all__' in content:
                content = content.replace(
                    '__all__ = [',
                    f'__all__ = [\n    "{name}",'
                )
            
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info(f"更新 {init_file} 导出 {name}")
        except Exception as e:
            logger.error(f"更新 __init__.py 失败: {e}")
    
    def _apply_parameter_tuning(self, engine, rec: Dict):
        """应用参数调优建议"""
        action = rec.get("actionable", "")
        logger.info(f"应用参数调优: {action}")
        # 可以调整 engine.mutator 的参数等
    
    def _apply_combination_strategy(self, engine, rec: Dict):
        """应用组合策略建议"""
        action = rec.get("actionable", "")
        logger.info(f"应用组合策略: {action}")
    
    def _apply_operator_adjustment(self, engine, rec: Dict):
        """应用操作符调整建议"""
        action = rec.get("actionable", "")
        logger.info(f"应用操作符调整: {action}")


def run_llm_formula_loop(draws: List[Draw], generations: int = 10, 
                         analysis_interval: int = 5) -> Dict:
    """
    运行完整的 LLM→Formula 闭环
    
    Args:
        draws: 历史开奖数据
        generations: 总演进代数
        analysis_interval: 每 N 代进行一次 LLM 分析
    
    Returns:
        闭环执行结果
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"启动 LLM→Formula 闭环演进")
    logger.info(f"总代数: {generations}, 分析间隔: {analysis_interval}")
    logger.info(f"{'='*60}")
    
    # 初始化引擎
    from formula_evolution import FormulaEvolutionEngine
    engine = FormulaEvolutionEngine(draws)
    engine.initialize_population(30)
    
    # 初始化闭环集成器
    integrator = FormulaLoopIntegrator(draws)
    integrator.analysis_interval = analysis_interval
    
    results = {
        "total_generations": generations,
        "analysis_points": [],
        "injected_count": 0,
        "llm_recommendations": [],
    }
    
    # 运行演进循环
    for gen in range(1, generations + 1):
        engine.generation = gen
        
        # 常规演进步骤
        from formula_lang.mutator import PrimitiveMutator
        from formula_lang.primitive import PrimitiveFactory
        from formula_lang.grammar import FormulaGrammar
        from formula_lang.evaluator_v3 import FormulaEvaluatorV3, evaluate_batch_parallel
        
        mutator = PrimitiveMutator()
        factory = PrimitiveFactory()
        prims = factory.create_all()
        ev = FormulaEvaluatorV3()
        operators = ['resonance', 'cascade', 'phase_align', 'weighted_sum']
        rng = random.Random()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"  第 {gen}/{generations} 代演进")
        logger.info(f"{'='*60}")
        
        # Step 1: 并行评估
        formulas_dict = {}
        for idx, member in enumerate(engine.population):
            formulas_dict[f"gen{gen}_{idx}"] = member['formula']
        
        eval_results = evaluate_batch_parallel(
            formulas_dict, draws, ev,
            n_windows=15, window_size=300, step=50,
            max_workers=min(8, len(engine.population)),
        )
        
        for idx, member in enumerate(engine.population):
            key = f"gen{gen}_{idx}"
            if key in eval_results:
                er = eval_results[key]
                member['score'] = er.get('combined_score', er.get('avg_hits', 0))
                member['eval_result'] = er
                member['avg_hits'] = er.get('avg_hits', 0)
                member['avg_brier'] = er.get('avg_brier', 0)
                member['beats_random'] = er.get('beats_random', False)
            else:
                member['score'] = -1
        
        engine.population.sort(key=lambda x: -x['score'])
        engine._update_best()
        
        logger.info(f"  最佳: {engine.best_formula.name if engine.best_formula else 'None'} Score={engine.best_score:.4f}")
        
        # Step 2: 保留精英
        elite_count = max(1, int(30 * 0.2))
        elites = engine.population[:elite_count]
        
        # Step 3: 变异 + 新生成
        new_population = list(elites)
        for elite in elites:
            try:
                mutated = mutator.mutate(elite['formula'], draws, generation=gen)
                quick_eval = ev.evaluate(mutated, draws, n_windows=5, window_size=300, step=50)
                new_population.append({
                    'formula': mutated,
                    'score': quick_eval.get('combined_score', 0),
                    'generation': gen,
                    'parent': elite['formula'].name,
                    'eval_result': quick_eval,
                })
            except:
                pass
        
        while len(new_population) < 30:
            n_prims = rng.randint(2, 4)
            selected = rng.sample(prims, min(n_prims, len(prims)))
            op = rng.choice(operators)
            try:
                f = getattr(FormulaGrammar, op)(selected, name=f'gen{gen}_new_{len(new_population)}')
                quick_eval = ev.evaluate(f, draws, n_windows=5, window_size=300, step=50)
                new_population.append({
                    'formula': f,
                    'score': quick_eval.get('combined_score', 0),
                    'generation': gen,
                    'parent': 'random',
                    'eval_result': quick_eval,
                })
            except:
                pass
        
        engine.population = new_population[:30]
        
        # === LLM 闭环触发点 ===
        if integrator.should_analyze(gen):
            logger.info(f"\n  🔄 触发 LLM 分析 (第 {gen} 代)...")
            integrator.last_analysis_gen = gen
            
            recommendations = integrator.advisor.get_recommendations()
            if recommendations.get("recommendations") or recommendations.get("new_primitive_proposals"):
                injected = integrator.inject_recommendations(engine, recommendations)
                results["injected_count"] += injected
                results["analysis_points"].append({
                    "generation": gen,
                    "recommendations": recommendations,
                    "injected": injected,
                })
                results["llm_recommendations"].append(recommendations)
                logger.info(f"  ✓ 注入 {injected} 项改进")
            else:
                logger.info(f"  ⊘ 无有效建议")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"LLM→Formula 闭环完成")
    logger.info(f"总分析次数: {len(results['analysis_points'])}")
    logger.info(f"总注入改进: {results['injected_count']}")
    logger.info(f"{'='*60}")
    
    return results


if __name__ == "__main__":
    # 测试
    from data_layer import load_history
    draws = load_history()
    
    print("加载数据:", len(draws), "期")
    
    # 测试分析器
    analyzer = FormulaVaultAnalyzer(draws)
    vault = analyzer.load_vault()
    print(f"历史代数: {len(vault['history'])}")
    
    if vault['history']:
        analysis = analyzer.analyze_patterns(vault)
        print(f"Top原语: {len(analysis['top_primitives'])}")
        print(f"成功模式: {len(analysis['success_patterns'])}")
        
        # 测试 LLM 调用
        advisor = LLMFormulaAdvisor()
        advisor.set_draws(draws)
        recs = advisor.get_recommendations()
        print(f"LLM建议: {len(recs.get('recommendations', []))} 条")
        for r in recs.get('recommendations', [])[:2]:
            print(f"  - {r.get('type')}: {r.get('description')[:80]}")
        for p in recs.get('new_primitive_proposals', [])[:2]:
            print(f"  - 新原语: {p.get('name')}")