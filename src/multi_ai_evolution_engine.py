# -*- coding: utf-8 -*-
"""
Antigravity 多AI协同进化引擎 V1.0 — 并行竞争 + 优胜劣汰

核心理念:
- 每个AI模型独立工作：各自分析数据、各自生成公式、各自推荐号码
- 统一验证层：所有候选公式用同一套walk-forward标准评估
- 优胜劣汰：存活者进入下一轮进化，淘汰者归档记录原因
- 并行计算：利用concurrent.futures让所有AI同时工作

AI模型矩阵:
  [本地] Gemma4 (Ollama)    → 深度推理分析
  [本地] Gemma2 (Ollama)    → 交叉验证
  [云端] Qwen-2.5-72B       → 创新公式生成
  [云端] Gemini             → 备用分析
  [云端] DeepSeek           → 备用分析
  [数学] Luckcast V15       → 核心预测引擎
  [数学] Enhanced Predictor → 加权集成引擎

用法:
    from multi_ai_evolution_engine import MultiAIEvolutionEngine

    engine = MultiAIEvolutionEngine()
    results = engine.run_evolution_cycle(generations=3, candidates_per_ai=10)
    engine.export_top_candidates(top_k=5)
"""
import sys
import json
import time
import math
import random
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# Fix Windows GBK encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

from data_layer import load_history, Draw
from formula_lang.primitive import Primitive, get_default_primitives
from formula_lang.grammar import FormulaGrammar, Formula
from formula_lang.evaluator_v3 import FormulaEvaluatorV3
from formula_lang.validator import FormulaValidator
from llm_innovation.llm_engine import LLMEngine
from strategy_proposer.hypothesis import Hypothesis, HypothesisTemplate
from strategy_proposer.generator import HypothesisGenerator
from strategy_proposer.validator import HypothesisValidator
from luckcast_antigravity_v1 import predict_v15, LearningState, _DIM_NAMES
from enhanced_predictor import WeightedEnsemble as EnhancedPredictorV2


# ═══════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════

class CandidateFormula:
    """候选公式 — 所有AI模型产出的统一格式"""

    def __init__(self, formula_id: str, source_ai: str, name: str,
                 primitives: List[str], composition: str,
                 description: str, params: Dict = None):
        self.id = formula_id
        self.source_ai = source_ai          # "gemma4" | "qwen" | "luckcast" | ...
        self.name = name
        self.primitives = primitives        # 使用的原语列表
        self.composition = composition      # "cascade" | "resonance" | "weighted_sum" | ...
        self.description = description
        self.params = params or {}
        self.birth_time = datetime.now().isoformat()

        # 评估结果
        self.fitness_score = 0.0            # 综合适应度分数
        self.avg_hits = 0.0                 # 平均命中数
        self.p_value = 1.0                  # 显著性
        self.calibration_error = 1.0        # 校准误差
        self.brier_score = 1.0              # Brier分数
        self.walk_forward_results: List[Dict] = []
        self.status = "proposed"            # proposed | tested | survived | eliminated | evolved

        # 进化历史
        self.parent_ids: List[str] = []
        self.generation = 0
        self.children: List[str] = []

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source_ai": self.source_ai,
            "name": self.name,
            "primitives": self.primitives,
            "composition": self.composition,
            "description": self.description,
            "params": self.params,
            "fitness_score": round(self.fitness_score, 4),
            "avg_hits": round(self.avg_hits, 4),
            "p_value": round(self.p_value, 4),
            "calibration_error": round(self.calibration_error, 4),
            "brier_score": round(self.brier_score, 4),
            "status": self.status,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "birth_time": self.birth_time,
        }


class EvolutionRound:
    """单轮进化结果"""

    def __init__(self, round_num: int):
        self.round_num = round_num
        self.timestamp = datetime.now().isoformat()
        self.candidates_generated = 0
        self.candidates_tested = 0
        self.survived = []
        self.eliminated = []
        self.evolved = []
        self.ai_performance = {}            # {ai_name: {"generated": N, "survived": N}}
        self.top_formula: Optional[CandidateFormula] = None

    def to_dict(self) -> Dict:
        return {
            "round_num": self.round_num,
            "timestamp": self.timestamp,
            "candidates_generated": self.candidates_generated,
            "candidates_tested": self.candidates_tested,
            "survived_count": len(self.survived),
            "eliminated_count": len(self.eliminated),
            "evolved_count": len(self.evolved),
            "top_formula": self.top_formula.to_dict() if self.top_formula else None,
            "ai_performance": self.ai_performance,
        }


# ═══════════════════════════════════════════════════════════
# AI模型工作者 — 每个AI独立生成公式的接口
# ═══════════════════════════════════════════════════════════

class AIWorker:
    """AI工作者基类 — 所有AI模型的统一接口"""

    def __init__(self, name: str, ai_type: str):
        self.name = name
        self.ai_type = ai_type  # "llm" | "math_engine" | "hybrid"

    def generate_candidates(self, draws: List[Draw], n: int, rng: random.Random) -> List[CandidateFormula]:
        """生成n个候选公式"""
        raise NotImplementedError

    def predict(self, draws: List[Draw], state: Any = None) -> Tuple[List[int], List[int]]:
        """直接预测下一期号码 (红球, 蓝球)"""
        raise NotImplementedError


class Gemma4Worker(AIWorker):
    """Gemma4 (Ollama本地) — 深度推理分析"""

    def __init__(self):
        super().__init__("gemma4", "llm")
        self.base_url = "http://localhost:11434"
        self.available = False
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                if any("gemma4" in m.get("name", "") for m in models):
                    self.available = True
        except Exception:
            pass

    def generate_candidates(self, draws: List[Draw], n: int, rng: random.Random) -> List[CandidateFormula]:
        if not self.available:
            return []

        try:
            import requests
            # 构建数据摘要
            summary = self._build_data_summary(draws, rng)

            prompt = f"""你是双色球公式设计专家。基于以下数据分析，设计{min(n, 3)}个评分公式。

数据摘要:
{summary}

要求:
1. 每个公式使用不同的原语组合
2. 公式类型可以是: 遗漏回补型、共现共振型、周期回声型、结构特征型
3. 每个公式需要说明: 使用的原语、组合方式、预期逻辑

按以下JSON格式输出(只输出JSON，不要其他文字):
[
  {{"name": "公式名", "type": "遗漏回补/共现共振/周期回声/结构特征",
     "primitives": ["原语1", "原语2"], "composition": "weighted_sum/cascade/resonance",
     "description": "公式逻辑说明", "weights": [0.4, 0.3, 0.3]}},
  ...
]"""

            resp = requests.post(f"{self.base_url}/api/chat", json={
                "model": "gemma4",
                "messages": [
                    {"role": "system", "content": "你是双色球公式设计专家，擅长从历史数据中发现模式并设计评分公式。只输出JSON。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {"num_predict": 2000, "temperature": 0.8}
            }, timeout=180)

            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "").strip()
                # 提取JSON
                start = content.find("[")
                end = content.rfind("]") + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                    specs = json.loads(json_str)

                    candidates = []
                    for spec in specs[:n]:
                        c = CandidateFormula(
                            formula_id=f"gemma4_{rng.randint(10000,99999)}",
                            source_ai="gemma4",
                            name=spec.get("name", "unnamed"),
                            primitives=spec.get("primitives", []),
                            composition=spec.get("composition", "weighted_sum"),
                            description=spec.get("description", ""),
                            params={"weights": spec.get("weights", {}), "type": spec.get("type", "")}
                        )
                        candidates.append(c)
                    return candidates
        except Exception as e:
            print(f"  [WARN] Gemma4生成失败: {e}")

        # 降级: 返回空列表
        return []

    def _build_data_summary(self, draws: List[Draw], rng: random.Random) -> str:
        """构建数据摘要"""
        latest = draws[-1]
        recent_omit = {}
        recent_freq = {}
        for n in range(1, 34):
            recent_freq[n] = 0
            o = 0
            for i in range(len(draws)-1, max(len(draws)-50, -1), -1):
                if n in draws[i].reds:
                    recent_freq[n] += 1
                    break
                o += 1
            recent_omit[n] = min(o, 50)

        lines = [f"最新一期 #{latest.period}: {sorted(latest.reds)} + {latest.blue}"]
        lines.append(f"共 {len(draws)} 期数据 ({draws[0].period} ~ {latest.period})")

        # 最热5个
        hot = sorted(range(1, 34), key=lambda x: -recent_freq[x])[:5]
        lines.append(f"近50期最热: {[f'{n}({recent_freq[n]})' for n in hot]}")

        # 最冷5个
        cold = sorted(range(1, 34), key=lambda x: recent_omit[x])[:5]
        lines.append(f"近50期最冷(遗漏最高): {[f'{n}({recent_omit[n]})' for n in cold]}")

        # 最近5期
        for d in draws[-5:]:
            lines.append(f"  #{d.period}: {sorted(d.reds)} + {d.blue}")

        return "\n".join(lines)

    def predict(self, draws: List[Draw], state=None) -> Tuple[List[int], List[int]]:
        """Gemma4直接预测"""
        try:
            import requests
            summary = self._build_data_summary(draws, random.Random(42))

            prompt = f"""双色球分析。最近5期:
{chr(10).join(f'#{d.period}: {sorted(d.reds)} + {d.blue}' for d in draws[-5:])}

请推荐下期(#{draws[-1].period + 1})号码:
- 红球6个(从小到大)
- 蓝球1个

按JSON格式: {{"red": [r1,r2,r3,r4,r5,r6], "blue": b1, "reason": "简短理由"}}"""

            resp = requests.post(f"{self.base_url}/api/chat", json={
                "model": "gemma4",
                "messages": [
                    {"role": "system", "content": "双色球分析专家。只输出JSON格式的号码推荐。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {"num_predict": 500, "temperature": 0.7}
            }, timeout=180)

            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "")
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    pred = json.loads(content[start:end])
                    return pred.get("red", []), [pred.get("blue", 1)]
        except Exception as e:
            print(f"  [WARN] Gemma4预测失败: {e}")

        return [], []


class Gemma2Worker(AIWorker):
    """Gemma2 (Ollama本地) — 交叉验证"""

    def __init__(self):
        super().__init__("gemma2", "llm")
        self.base_url = "http://localhost:11434"
        self.available = False
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                if any("gemma2" in m.get("name", "") for m in models):
                    self.available = True
        except Exception:
            pass

    def generate_candidates(self, draws: List[Draw], n: int, rng: random.Random) -> List[CandidateFormula]:
        if not self.available:
            return []

        try:
            import requests
            summary = self._build_data_summary(draws, rng)

            prompt = f"""你是双色球策略分析师。基于以下数据，提出{min(n, 3)}种不同的号码评分策略。

数据摘要:
{summary}

注意: 你的策略应该与gemma4的策略角度不同。如果gemma4关注遗漏，你就关注频率或共现。

JSON格式:
[
  {{"name": "策略名", "type": "频率/共现/位置/结构",
     "primitives": ["原语1"], "composition": "weighted_sum/cascade",
     "description": "策略逻辑", "weights": [0.5, 0.5]}},
  ...
]"""

            resp = requests.post(f"{self.base_url}/api/chat", json={
                "model": "gemma2",
                "messages": [
                    {"role": "system", "content": "双色球策略分析师。只输出JSON。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {"num_predict": 2000, "temperature": 0.8}
            }, timeout=180)

            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "").strip()
                start = content.find("[")
                end = content.rfind("]") + 1
                if start >= 0 and end > start:
                    specs = json.loads(content[start:end])
                    candidates = []
                    for spec in specs[:n]:
                        c = CandidateFormula(
                            formula_id=f"gemma2_{rng.randint(10000,99999)}",
                            source_ai="gemma2",
                            name=spec.get("name", "unnamed"),
                            primitives=spec.get("primitives", []),
                            composition=spec.get("composition", "weighted_sum"),
                            description=spec.get("description", ""),
                            params={"weights": spec.get("weights", {}), "type": spec.get("type", "")}
                        )
                        candidates.append(c)
                    return candidates
        except Exception as e:
            print(f"  [WARN] Gemma2生成失败: {e}")

        return []

    def _build_data_summary(self, draws: List[Draw], rng: random.Random) -> str:
        latest = draws[-1]
        lines = [f"最新一期 #{latest.period}: {sorted(latest.reds)} + {latest.blue}"]
        lines.append(f"共 {len(draws)} 期数据")
        for d in draws[-5:]:
            lines.append(f"  #{d.period}: {sorted(d.reds)} + {d.blue}")
        return "\n".join(lines)

    def predict(self, draws: List[Draw], state=None) -> Tuple[List[int], List[int]]:
        try:
            import requests
            prompt = f"最近5期: {' | '.join(f'#{d.period}:{sorted(d.reds)}+{d.blue}' for d in draws[-5:])}\n推荐下期#{draws[-1].period+1}号码: {{\"red\":[],\"blue\":1}}"
            resp = requests.post(f"{self.base_url}/api/chat", json={
                "model": "gemma2",
                "messages": [
                    {"role": "system", "content": "双色球分析。只输出JSON。"},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {"num_predict": 500, "temperature": 0.7}
            }, timeout=180)
            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "")
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    pred = json.loads(content[start:end])
                    return pred.get("red", []), [pred.get("blue", 1)]
        except Exception:
            pass
        return [], []


class OpenRouterWorker(AIWorker):
    """OpenRouter (Qwen-2.5-72B) — 创新公式生成"""

    def __init__(self):
        super().__init__("qwen-openrouter", "llm")
        self.available = False
        self.client = None
        try:
            from openai import OpenAI
            key = __import__('os').environ.get('OPENROUTER_API_KEY', '')
            if key:
                self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
                self.available = True
        except Exception:
            pass

    def generate_candidates(self, draws: List[Draw], n: int, rng: random.Random) -> List[CandidateFormula]:
        if not self.available or not self.client:
            return []

        try:
            summary = self._build_data_summary(draws, rng)

            prompt = f"""Analyze this Chinese lottery (SSQ/双色球) data and design {min(n, 5)} innovative scoring formulas.

Data Summary:
{summary}

Design formulas that capture different patterns:
- Temporal decay patterns (numbers getting due)
- Cooccurrence resonance (pairs/triples that appear together)
- Structural properties (binary, digit features)
- Positional bias (where numbers tend to appear in sorted order)

Output JSON array:
[
  {{"name": "formula_name", "type": "temporal/cooccurrence/structural/positional",
     "primitives": ["prim1", "prim2"], "composition": "weighted_sum/cascade/resonance/phase_align",
     "description": "English description of the formula logic",
     "weights": [0.4, 0.3, 0.3]}},
  ...
]"""

            resp = self.client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": "You are a lottery formula designer. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000,
                timeout=60,
            )

            content = resp.choices[0].message.content
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                specs = json.loads(content[start:end])
                candidates = []
                for spec in specs[:n]:
                    c = CandidateFormula(
                        formula_id=f"qwen_{rng.randint(10000,99999)}",
                        source_ai="qwen-openrouter",
                        name=spec.get("name", "unnamed"),
                        primitives=spec.get("primitives", []),
                        composition=spec.get("composition", "weighted_sum"),
                        description=spec.get("description", ""),
                        params={"weights": spec.get("weights", {}), "type": spec.get("type", "")}
                    )
                    candidates.append(c)
                return candidates
        except Exception as e:
            print(f"  [WARN] Qwen生成失败: {e}")

        return []

    def _build_data_summary(self, draws: List[Draw], rng: random.Random) -> str:
        latest = draws[-1]
        lines = [f"Latest #{latest.period}: {sorted(latest.reds)} + {latest.blue}"]
        lines.append(f"Total {len(draws)} periods")
        for d in draws[-10:]:
            lines.append(f"  #{d.period}: {sorted(d.reds)} sum={sum(d.reds)} blue={d.blue}")

        # Frequency analysis
        freq = Counter()
        for d in draws[-20:]:
            for r in d.reds:
                freq[r] += 1
        hot = freq.most_common(5)
        lines.append(f"Hot (last 20): {[(n, c) for n, c in hot]}")

        # Omission
        omit = {}
        for n in range(1, 34):
            o = 0
            for i in range(len(draws)-1, -1, -1):
                if n not in draws[i].reds:
                    o += 1
                else:
                    break
            omit[n] = o
        coldest = sorted(omit.items(), key=lambda x: -x[1])[:5]
        lines.append(f"Coldest (omission): {[(n, c) for n, c in coldest]}")

        return "\n".join(lines)

    def predict(self, draws: List[Draw], state=None) -> Tuple[List[int], List[int]]:
        if not self.available or not self.client:
            return [], []
        try:
            summary = self._build_data_summary(draws, random.Random(42))
            resp = self.client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[
                    {"role": "system", "content": "Lottery prediction expert. Output only JSON."},
                    {"role": "user", "content": f"Data:\n{summary}\n\nPredict next: {{\"red\":[],\"blue\":1}}"},
                ],
                temperature=0.7,
                max_tokens=500,
                timeout=60,
            )
            content = resp.choices[0].message.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                pred = json.loads(content[start:end])
                return pred.get("red", []), [pred.get("blue", 1)]
        except Exception:
            pass
        return [], []


class LuckcastWorker(AIWorker):
    """Luckcast V15 — 7维学习预测器 (数学引擎)"""

    def __init__(self):
        super().__init__("luckcast_v15", "math_engine")
        self.available = True

    def generate_candidates(self, draws: List[Draw], n: int, rng: random.Random) -> List[CandidateFormula]:
        """Luckcast不生成公式，但可以作为预测引擎直接参与竞争"""
        return []  # 数学引擎不走公式生成路径

    def predict(self, draws: List[Draw], state=None) -> Tuple[List[int], List[int]]:
        try:
            # 在线程环境中需要重新导入以确保全局变量可用
            from luckcast_antigravity_v1 import predict_v15 as _pv15
            from luckcast_antigravity_v1 import LearningState as _LS
            from luckcast_antigravity_v1 import _DIM_NAMES as _DN

            v15_state = _LS(_DN)
            top_results, _ = _pv15(draws, v15_state, top_k=5, seed=42)
            if top_results:
                red = sorted(top_results[0][0])
                blue = top_results[0][1]
                return red, [blue]
        except Exception as e:
            print(f"  [WARN] Luckcast V15预测失败: {e}")
        return [], []


class EnhancedWorker(AIWorker):
    """Enhanced Predictor V2 — WeightedEnsemble"""

    def __init__(self):
        super().__init__("enhanced_v2", "math_engine")
        self.available = True

    def generate_candidates(self, draws: List[Draw], n: int, rng: random.Random) -> List[CandidateFormula]:
        return []

    @staticmethod
    def _draws_to_df(draws: List[Draw]) -> Any:
        """将 Draw 列表转为 enhanced_predictor 需要的 DataFrame"""
        import pandas as pd
        records = []
        for d in draws:
            records.append({
                "period": d.period,
                "red": ",".join(str(n) for n in sorted(d.reds)),
                "blue": d.blue,
            })
        return pd.DataFrame(records)

    def predict(self, draws: List[Draw], state=None) -> Tuple[List[int], List[int]]:
        """使用 enhanced_predictor 的 WeightedEnsemble 预测"""
        try:
            from enhanced_predictor import WeightedEnsemble

            df = self._draws_to_df(draws)
            ensemble = WeightedEnsemble(df)
            results = ensemble.generate(num_groups=5)

            # 收集所有红球投票
            red_votes = Counter()
            blue_votes = Counter()
            for r in results:
                for n in r.get("reds", []):
                    red_votes[n] += 1
                blue_votes[r.get("blue", 0)] += 1

            top_red = sorted([n for n, _ in red_votes.most_common(12)])[:6]
            top_blue = [n for n, _ in blue_votes.most_common(1)]
            return top_red, top_blue
        except Exception as e:
            print(f"  [WARN] Enhanced V2预测失败: {e}")
        return [], []


class PrimitiveCombinerWorker(AIWorker):
    """原语组合器 — 当LLM不可用时的后备方案

    从已有的33个原语库中，按不同策略组合生成候选公式。
    这是系统自举能力：不需要AI语言模型也能工作。
    """

    def __init__(self, primitives: List[Primitive]):
        super().__init__("primitive_combiner", "hybrid")
        self.available = True
        self.primitives = primitives
        self.primitive_map = {p.name: p for p in primitives}
        self.composition_ops = ["weighted_sum", "cascade", "resonance", "phase_align"]

    def generate_candidates(self, draws: List[Draw], n: int, rng: random.Random) -> List[CandidateFormula]:
        candidates = []
        used_names = set()

        # 策略1: 随机原语组合 (weighted_sum)
        for i in range(n // 3):
            k = rng.randint(2, min(5, len(self.primitives)))
            chosen = rng.sample(self.primitives, k)
            names = [p.name for p in chosen]
            name_key = tuple(sorted(names))
            if name_key not in used_names:
                used_names.add(name_key)
                c = CandidateFormula(
                    formula_id=f"pc_{rng.randint(100000,999999)}",
                    source_ai="primitive_combiner",
                    name=f"wc_{len(candidates)+1}",
                    primitives=names,
                    composition="weighted_sum",
                    description=f"随机组合{k}个原语的加权求和",
                    params={"strategy": "random_weighted_sum"},
                )
                candidates.append(c)

        # 策略2: 同类别原语组合
        categories = {}
        for p in self.primitives:
            categories.setdefault(p.category, []).append(p)
        for cat, prims in categories.items():
            if len(prims) >= 2 and len(candidates) < n:
                k = min(rng.randint(2, 4), len(prims))
                chosen = rng.sample(prims, k)
                names = [p.name for p in chosen]
                c = CandidateFormula(
                    formula_id=f"pc_{rng.randint(100000,999999)}",
                    source_ai="primitive_combiner",
                    name=f"{cat}_combo_{len(candidates)+1}",
                    primitives=names,
                    composition=rng.choice(["cascade", "resonance"]),
                    description=f"同类别{cat}原语组合",
                    params={"strategy": "same_category", "category": cat},
                )
                candidates.append(c)

        # 策略3: 跨类别原语组合
        cats = list(categories.keys())
        while len(candidates) < n and len(cats) >= 2:
            chosen_cats = rng.sample(cats, min(2, len(cats)))
            all_prims = []
            for cc in chosen_cats:
                all_prims.extend(categories[cc])
            k = rng.randint(2, min(4, len(all_prims)))
            chosen = rng.sample(all_prims, k)
            names = [p.name for p in chosen]
            c = CandidateFormula(
                formula_id=f"pc_{rng.randint(100000,999999)}",
                source_ai="primitive_combiner",
                name=f"cross_cat_{len(candidates)+1}",
                primitives=names,
                composition="weighted_sum",
                description=f"跨类别组合({'+'.join(chosen_cats)})" ,
                params={"strategy": "cross_category", "categories": chosen_cats},
            )
            candidates.append(c)

        return candidates[:n]

    def predict(self, draws: List[Draw], state=None) -> Tuple[List[int], List[int]]:
        """使用原语投票预测"""
        scores = {}
        for n in range(1, 34):
            scores[n] = 0.0

        # 每个原语打分并累加
        for p in self.primitives:
            try:
                s = p.score_all(draws)
                vals = list(s.values())
                if vals:
                    mn, mx = min(vals), max(vals)
                    spread = mx - mn if mx != mn else 1
                    for num in range(1, 34):
                        norm = (s[num] - mn) / spread
                        scores[num] += norm
            except Exception:
                pass

        top6 = sorted(scores.items(), key=lambda x: -x[1])[:6]
        return [n for n, _ in top6], []


# ═══════════════════════════════════════════════════════════
# 统一验证器 — 所有候选公式用同一套标准评估
# ═══════════════════════════════════════════════════════════

class UnifiedValidator:
    """统一验证器 — walk-forward V3 + Brier Score + EWMA"""

    def __init__(self, draws: List[Draw]):
        self.draws = draws
        self.evaluator = FormulaEvaluatorV3()
        self.primitives = get_default_primitives()
        self.primitive_map = {p.name: p for p in self.primitives}

    def validate_candidate(self, candidate: CandidateFormula,
                           initial_window: int = 500, step: int = 30) -> Dict:
        """验证单个候选公式"""
        # Step 1: 解析原语，构建公式
        primitives_used = []
        for pname in candidate.primitives:
            prim = self.primitive_map.get(pname)
            if prim:
                primitives_used.append(prim)
            else:
                # 尝试模糊匹配
                found = None
                for p in self.primitives:
                    if pname in p.name or p.name in pname:
                        found = p
                        break
                if found:
                    primitives_used.append(found)

        if not primitives_used:
            candidate.status = "eliminated"
            candidate.elimination_reason = "no_valid_primitives"
            return {"valid": False, "reason": "no_valid_primitives"}

        # Step 2: 用组合算子构建公式
        try:
            op_name = candidate.composition
            op_func = getattr(FormulaGrammar, op_name, None)
            if not op_func:
                op_func = getattr(FormulaGrammar, "weighted_sum")

            formula = op_func(primitives_used, name=candidate.id)
        except Exception as e:
            candidate.status = "eliminated"
            candidate.elimination_reason = f"composition_failed: {str(e)[:50]}"
            return {"valid": False, "reason": "composition_failed"}

        # Step 3: Walk-forward验证 (使用V3 Brier Score评估器)
        try:
            result = self.evaluator.evaluate(
                formula, self.draws,
                n_windows=10,
                window_size=initial_window,
                step=step,
            )

            # V3评估器返回的字段: avg_brier, red_brier, blue_hit_rate, stability, generalization_gap
            red_brier = result.get("red_brier", 1.0)
            blue_hit_rate = result.get("blue_hit_rate", 0.0)
            stability = abs(result.get("stability", 0))
            overfit_risk = result.get("overfitting_risk", "UNKNOWN")

            # 转换到与旧系统兼容的指标
            # Brier Score < 随机基线(0.139) = 好信号
            # 随机命中率 ~2.0/6
            brier_baseline = 0.139
            improvement = max(0, (brier_baseline - red_brier) / brier_baseline)  # 相对基线的改善

            # 综合适应度分数
            # 核心: Brier改善度(40%) + 蓝球命中率(20%) + 稳定性(20%) + 泛化检验(20%)
            stability_score = max(0, 1 - stability * 100)  # 越稳定越高
            generalization_bonus = 0.0
            if overfit_risk == "LOW":
                generalization_bonus = 0.2
            elif overfit_risk == "MODERATE":
                generalization_bonus = 0.1

            fitness = (improvement * 0.4 +
                       blue_hit_rate * 0.2 +
                       stability_score * 0.2 +
                       generalization_bonus * 0.2)

            candidate.avg_hits = improvement * 6  # 映射到等效命中数
            candidate.p_value = max(0, 1 - improvement)
            candidate.calibration_error = red_brier
            candidate.brier_score = red_brier
            candidate.fitness_score = fitness
            candidate.walk_forward_results = [result]

            # 决策: 初始阶段放宽阈值，让有潜力的公式存活进入进化
            if fitness > 0.2 and red_brier < brier_baseline * 1.1:
                candidate.status = "survived"
            elif fitness > 0.15:
                candidate.status = "borderline"
            else:
                candidate.status = "eliminated"
                candidate.elimination_reason = f"low_fitness({fitness:.2f}),brier={red_brier:.4f}"

            return {
                "valid": True,
                "fitness": fitness,
                "red_brier": red_brier,
                "blue_hit_rate": blue_hit_rate,
                "status": candidate.status,
            }
        except Exception as e:
            candidate.status = "eliminated"
            candidate.elimination_reason = f"validation_error: {str(e)[:50]}"
            return {"valid": False, "reason": str(e)[:100]}

    def validate_all(self, candidates: List[CandidateFormula],
                     max_workers: int = 4) -> Dict[str, Dict]:
        """并行验证所有候选公式"""
        results = {}

        def validate_one(c):
            return c.id, self.validate_candidate(c)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(validate_one, c): c for c in candidates}
            for future in as_completed(futures):
                cid, result = future.result()
                results[cid] = result

        return results


# ═══════════════════════════════════════════════════════════
# 进化器 — 存活者的变异和交叉
# ═══════════════════════════════════════════════════════════

class EvolutionEngine:
    """进化引擎 — 对存活公式进行变异和交叉"""

    def __init__(self, primitives: List[Primitive]):
        self.available_primitives = primitives
        self.primitive_names = [p.name for p in self.available_primitives]

    def mutate(self, candidate: CandidateFormula, rng: random.Random) -> CandidateFormula:
        """变异: 替换/增减原语"""
        new = CandidateFormula(
            formula_id=f"mutant_{rng.randint(100000,999999)}",
            source_ai=candidate.source_ai + "_mutant",
            name=f"mutant_of_{candidate.name}",
            primitives=list(candidate.primitives),
            composition=candidate.composition,
            description=f"变异自: {candidate.description}",
            params=dict(candidate.params),
        )
        new.parent_ids = [candidate.id]
        new.generation = candidate.generation + 1

        # 变异策略
        strategy = rng.choice(["swap", "add", "remove"])

        if strategy == "swap" and new.primitives:
            idx = rng.randint(0, len(new.primitives) - 1)
            new.primitives[idx] = rng.choice(self.primitive_names)
        elif strategy == "add":
            new.primitives.append(rng.choice(self.primitive_names))
        elif strategy == "remove" and len(new.primitives) > 1:
            new.primitives.pop(rng.randint(0, len(new.primitives) - 1))

        return new

    def crossover(self, a: CandidateFormula, b: CandidateFormula,
                  rng: random.Random) -> CandidateFormula:
        """交叉: 混合两个存活公式"""
        # 随机选择a或b的原语
        mid = rng.randint(1, max(len(a.primitives), 1))
        mixed_prims = a.primitives[:mid] + b.primitives[mid:]

        # 随机选择a或b的组合方式
        comp = rng.choice([a.composition, b.composition])

        new = CandidateFormula(
            formula_id=f"crossover_{rng.randint(100000,999999)}",
            source_ai=f"{a.source_ai}_x_{b.source_ai}",
            name=f"child_of_{a.name}_x_{b.name}",
            primitives=list(set(mixed_prims)),
            composition=comp,
            description=f"交叉: {a.description[:30]} + {b.description[:30]}",
            params={},
        )
        new.parent_ids = [a.id, b.id]
        new.generation = max(a.generation, b.generation) + 1

        return new


# ═══════════════════════════════════════════════════════════
# 主引擎 — 多AI协同进化
# ═══════════════════════════════════════════════════════════

class MultiAIEvolutionEngine:
    """
    多AI协同进化引擎 — 并行竞争 + 优胜劣汰

    工作流程:
    1. 初始化: 注册所有AI工作者
    2. 生成阶段: 各AI并行生成候选公式
    3. 验证阶段: 统一walk-forward验证
    4. 选择阶段: 存活者晋级，淘汰者归档
    5. 进化阶段: 存活者变异/交叉产生下一代
    6. 循环: 重复步骤2-5直到指定代数
    """

    def __init__(self, draws: Optional[List[Draw]] = None):
        self.draws = draws or load_history()
        print(f"[EvolutionEngine] 加载 {len(self.draws)} 期数据 ({self.draws[0].period} ~ {self.draws[-1].period})")

        # 注册AI工作者
        self.workers: Dict[str, AIWorker] = {}
        self._register_workers()

        # 组件
        self.validator = UnifiedValidator(self.draws)
        self.evolution = EvolutionEngine(get_default_primitives())

        # 状态
        self.all_candidates: List[CandidateFormula] = []
        self.current_generation = 0
        self.evolution_history: List[EvolutionRound] = []
        self.survival_pool: List[CandidateFormula] = []  # 存活池

        print(f"[EvolutionEngine] 已注册 {len(self.workers)} 个AI工作者:")
        for name, w in self.workers.items():
            status = "在线" if w.available else "离线"
            print(f"  - {name}: {w.ai_type} [{status}]")

    def _register_workers(self):
        """注册所有AI工作者"""
        # LLM工作者
        gemma4 = Gemma4Worker()
        if gemma4.available:
            self.workers["gemma4"] = gemma4
            print(f"  [OK] Gemma4 (Ollama) 已注册")

        gemma2 = Gemma2Worker()
        if gemma2.available:
            self.workers["gemma2"] = gemma2
            print(f"  [OK] Gemma2 (Ollama) 已注册")

        qwen = OpenRouterWorker()
        if qwen.available:
            self.workers["qwen"] = qwen
            print(f"  [OK] Qwen-2.5-72B (OpenRouter) 已注册")

        # 数学引擎工作者
        self.workers["luckcast_v15"] = LuckcastWorker()
        self.workers["enhanced_v2"] = EnhancedWorker()

        # 原语组合器 — 总是注册，作为LLM不可用时的后备
        self.workers["primitive_combiner"] = PrimitiveCombinerWorker(get_default_primitives())
        print(f"  [OK] PrimitiveCombiner (原语组合后备) 已注册")

    def run_evolution_cycle(self, generations: int = 3, candidates_per_ai: int = 5,
                            initial_window: int = 500, max_workers: int = 6) -> Dict:
        """
        运行完整的进化周期。

        Args:
            generations: 进化代数
            candidates_per_ai: 每个AI生成的候选数量
            initial_window: walk-forward初始窗口
            max_workers: 最大并行验证线程数

        Returns:
            进化结果汇总
        """
        rng = random.Random(42)
        all_survivors = []

        for gen in range(1, generations + 1):
            self.current_generation = gen
            print(f"\n{'='*70}")
            print(f"  第 {gen}/{generations} 代进化")
            print(f"{'='*70}")

            # ─── Phase 1: 并行生成 ──────────────────────────────
            print(f"\n[Phase 1/4] 并行生成候选公式...")
            generation_candidates = []
            worker_stats = {}

            with ThreadPoolExecutor(max_workers=len(self.workers)) as executor:
                future_to_worker = {
                    executor.submit(w.generate_candidates, self.draws, candidates_per_ai, rng): name
                    for name, w in self.workers.items()
                    if w.ai_type in ("llm", "hybrid")  # LLM + 原语组合器都能生成公式
                }

                for future in as_completed(future_to_worker):
                    worker_name = future_to_worker[future]
                    try:
                        candidates = future.result()
                        generation_candidates.extend(candidates)
                        worker_stats[worker_name] = {
                            "generated": len(candidates),
                            "status": "success" if candidates else "empty"
                        }
                        print(f"  [{worker_name}] 生成 {len(candidates)} 个候选")
                    except Exception as e:
                        worker_stats[worker_name] = {"error": str(e)[:50]}
                        print(f"  [{worker_name}] 错误: {e}")

            # 数学引擎直接参与预测竞争（不生成公式）
            math_predictions = {}
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_to_math = {
                    executor.submit(w.predict, self.draws): name
                    for name, w in self.workers.items()
                    if w.ai_type == "math_engine"
                }
                for future in as_completed(future_to_math):
                    worker_name = future_to_math[future]
                    try:
                        reds, blues = future.result()
                        math_predictions[worker_name] = {"red": reds, "blue": blues}
                        print(f"  [{worker_name}] 预测: 红{sorted(reds)} 蓝{blues}")
                    except Exception as e:
                        print(f"  [{worker_name}] 预测错误: {e}")

            self.all_candidates.extend(generation_candidates)
            print(f"\n  总计生成 {len(generation_candidates)} 个候选公式")

            # ─── Phase 2: 并行验证 ──────────────────────────────
            print(f"\n[Phase 2/4] 并行验证候选公式...")
            if generation_candidates:
                validation_results = self.validator.validate_all(
                    generation_candidates, max_workers=max_workers
                )

                for c in generation_candidates:
                    vr = validation_results.get(c.id, {})
                    print(f"  [{c.source_ai}] {c.name}: fitness={c.fitness_score:.2f} "
                          f"hits={c.avg_hits:.2f} p={c.p_value:.4f} [{c.status}]")
            else:
                validation_results = {}
                print(f"  无候选公式可验证")

            # ─── Phase 3: 选择 ──────────────────────────────────
            print(f"\n[Phase 3/4] 选择存活者...")
            survived = [c for c in generation_candidates if c.status == "survived"]
            borderline = [c for c in generation_candidates if c.status == "borderline"]
            eliminated = [c for c in generation_candidates if c.status == "eliminated"]

            # 合并到存活池
            all_survivors = survived + borderline
            for s in all_survivors:
                s.status = "survived"

            # 更新worker统计
            for w_name in worker_stats:
                w_survived = len([c for c in survived if c.source_ai.startswith(w_name.split("_")[0])])
                worker_stats[w_name]["survived"] = w_survived

            print(f"  存活: {len(survived)}, 边缘: {len(borderline)}, 淘汰: {len(eliminated)}")

            # 记录本轮
            round_result = EvolutionRound(gen)
            round_result.candidates_generated = len(generation_candidates)
            round_result.candidates_tested = len(validation_results)
            round_result.survived = [c.to_dict() for c in survived]
            round_result.eliminated = [c.to_dict() for c in eliminated[:10]]  # 只记前10个
            round_result.ai_performance = worker_stats
            if survived:
                round_result.top_formula = max(survived, key=lambda c: c.fitness_score)
            self.evolution_history.append(round_result)

            # ─── Phase 4: 进化 ──────────────────────────────────
            print(f"\n[Phase 4/4] 进化存活者...")
            evolved = []
            if len(all_survivors) >= 2 and gen < generations:
                # 变异
                for survivor in all_survivors[:3]:  # 最多变异Top-3
                    mutant = self.evolution.mutate(survivor, rng)
                    evolved.append(mutant)

                # 交叉
                for i in range(min(3, len(all_survivors))):
                    for j in range(i+1, min(5, len(all_survivors))):
                        child = self.evolution.crossover(all_survivors[i], all_survivors[j], rng)
                        evolved.append(child)
                        if len(evolved) >= 5:
                            break
                    if len(evolved) >= 5:
                        break

                print(f"  进化出 {len(evolved)} 个新候选")
            else:
                print(f"  存活者不足，跳过进化")

            # 将进化产物标记为当前代
            if evolved:
                for e in evolved:
                    e.generation = gen + 1
                generation_candidates.extend(evolved)
                self.all_candidates.extend(evolved)
                all_survivors.extend(evolved)
                round_result.evolved = [e.to_dict() for e in evolved]

            # 更新存活池
            self.survival_pool = all_survivors[:10]  # 保留Top-10

        # ─── 最终汇总 ──────────────────────────────────────────
        final_summary = self._build_final_summary(math_predictions)

        # 保存
        self._save_state(final_summary)

        return final_summary

    def _build_final_summary(self, math_predictions: Dict) -> Dict:
        """构建最终汇总"""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_generations": self.current_generation,
            "total_candidates": len(self.all_candidates),
            "survival_pool": [c.to_dict() for c in self.survival_pool],
            "math_engine_predictions": math_predictions,
            "evolution_history": [r.to_dict() for r in self.evolution_history],
            "best_formula": max(self.survival_pool, key=lambda c: c.fitness_score).to_dict() if self.survival_pool else None,
        }

    def _save_state(self, summary: Dict):
        """保存进化状态"""
        path = _PROJECT_ROOT / "evolution_state_v20.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\n  状态已保存到 {path}")

    def export_top_candidates(self, top_k: int = 5) -> Dict:
        """导出Top-K候选公式"""
        ranked = sorted(self.all_candidates, key=lambda c: -c.fitness_score)
        top = ranked[:top_k]

        output = {
            "exported_at": datetime.now().isoformat(),
            "top_candidates": [c.to_dict() for c in top],
            "final_recommendation": self._aggregate_recommendation(top),
        }

        path = _PROJECT_ROOT / "top_candidates_export.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"  Top-{top_k} 已导出到 {path}")

        return output

    def _aggregate_recommendation(self, candidates: List[CandidateFormula]) -> Dict:
        """聚合Top候选的推荐"""
        red_votes = Counter()
        blue_votes = Counter()

        for c in candidates:
            # 从walk-forward结果中提取高频号码
            for wf in c.walk_forward_results:
                if "top_numbers" in wf:
                    for n in wf["top_numbers"][:6]:
                        red_votes[n] += 1
                if "top_blue" in wf:
                    blue_votes[wf["top_blue"]] += 1

        top_red = sorted([n for n, _ in red_votes.most_common(12)])
        top_blue = sorted([n for n, _ in blue_votes.most_common(5)])

        return {
            "red": top_red[:12],
            "blue": top_blue[:5],
            "vote_counts": {str(k): v for k, v in red_votes.most_common(12)},
        }

    def status_report(self) -> str:
        """生成状态报告"""
        lines = [
            "=" * 70,
            "  多AI协同进化引擎 — 状态报告",
            "=" * 70,
            f"总代数: {self.current_generation}",
            f"总候选: {len(self.all_candidates)}",
            f"存活池: {len(self.survival_pool)}",
            "",
            "AI工作者状态:",
        ]

        for name, w in self.workers.items():
            status = "在线" if w.available else "离线"
            lines.append(f"  - {name}: {w.ai_type} [{status}]")

        lines.append("")
        lines.append("代数摘要:")
        for r in self.evolution_history:
            lines.append(
                f"  第{r.round_num}代: 生成{r.candidates_generated} | "
                f"存活{len(r.survived)} | 淘汰{len(r.eliminated)}"
            )

        if self.survival_pool:
            best = max(self.survival_pool, key=lambda c: c.fitness_score)
            lines.append("")
            lines.append(f"最佳公式: {best.name} (fitness={best.fitness_score:.2f})")
            lines.append(f"  来源: {best.source_ai}")
            lines.append(f"  原语: {best.primitives}")
            lines.append(f"  组合: {best.composition}")

        lines.append("=" * 70)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 便捷入口
# ═══════════════════════════════════════════════════════════

def quick_evolution(generations: int = 2, candidates_per_ai: int = 3):
    """快速进化测试"""
    engine = MultiAIEvolutionEngine()
    result = engine.run_evolution_cycle(
        generations=generations,
        candidates_per_ai=candidates_per_ai,
    )
    print("\n" + engine.status_report())
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="多AI协同进化引擎 V1.0")
    parser.add_argument("--generations", type=int, default=3, help="进化代数")
    parser.add_argument("--candidates", type=int, default=5, help="每AI候选数")
    parser.add_argument("--export", action="store_true", help="导出Top-K")
    parser.add_argument("--status", action="store_true", help="显示状态")
    args = parser.parse_args()

    engine = MultiAIEvolutionEngine()

    if args.status:
        print(engine.status_report())
    else:
        result = engine.run_evolution_cycle(
            generations=args.generations,
            candidates_per_ai=args.candidates,
        )
        print("\n" + engine.status_report())

        if args.export:
            engine.export_top_candidates(top_k=5)
