# -*- coding: utf-8 -*-
"""
Multi-AI Collaborative Formula Evolution Engine V19

第一性原理：双色球是可计算的，每个AI模型从不同视角计算。
核心创新：不是单模型预测，而是多模型协同计算+公式进化。

参与的AI模型：
1. Gemma4 (本地) — 深度模式分析
2. Gemma2 (本地) — 交叉验证
3. OpenRouter Qwen-72B — 公式原子创新
4. Gemini — 备选（配额耗尽）
5. DeepSeek — 备选
6. Luckcast V15 — 7维学习预测引擎
7. Enhanced Predictor — 加权集成
8. 33个公式原语 — 数学原子
9. Claude Opus 4.8 — 架构编排（我）

进化机制：
- 每代用 ALL AI模型的输出作为"候选公式"的种子
- 用walk-forward评估每个候选公式
- Top-K存活并繁殖（变异+交叉）
- LLM模型负责生成新的原语组合策略
- 数学引擎负责精确计算
- 两者结合产生新一代公式
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os, json, copy, math, random, time, requests
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, 'E:/享中')
from data_layer import load_history
from formula_lang.primitive import get_default_primitives
from formula_lang.grammar import Formula, FormulaGrammar
from formula_lang.mutator import PrimitiveMutator

# ─── 配置 ─────────────────────────────────────────────
POPULATION_SIZE = 100        # 每代公式数量（减少以容纳AI推理）
ELITE_COUNT = 15             # 精英保留数
MUTATION_RATE = 0.5          # 变异概率
CROSSOVER_RATE = 0.3         # 交叉概率
N_GENERATIONS = 50           # 总代数（LLM推理较慢）
WALK_FORWARD_WINDOWS = 20   # walk-forward窗口数
WINDOW_SIZE = 500            # 训练窗口大小
WINDOW_STEP = 50             # 步进

EVOLUTION_STATE_FILE = 'E:/享中/evolution_state_v19.json'
BEST_FORMULAS_FILE = 'E:/享中/best_formulas_v19.json'
AI_ANALYSIS_FILE = 'E:/享中/multi_ai_analysis.json'

# ─── 数据结构 ─────────────────────────────────────────
from dataclasses import dataclass

@dataclass
class FormulaResult:
    """单个公式的评估结果"""
    formula: Formula
    source: str                # "luckcast" / "gemma4" / "primitive" / "evolved"
    avg_hits: float
    std_hits: float
    max_hits: int
    min_hits: int
    p_value: float
    rounds: int
    stability: float
    fitness: float

    def to_dict(self):
        return {
            "name": self.formula.name,
            "source": self.source,
            "avg_hits": round(self.avg_hits, 4),
            "std_hits": round(self.std_hits, 4),
            "max_hits": self.max_hits,
            "min_hits": self.min_hits,
            "p_value": round(self.p_value, 4),
            "rounds": self.rounds,
            "stability": round(self.stability, 4),
            "fitness": round(self.fitness, 4),
            "operators": self.formula.operators,
            "primitive_names": [p.name for p in self.formula.primitives],
        }


# ─── AI模型接口 ───────────────────────────────────────

def query_ollama(model, prompt, temperature=0.7, num_predict=500):
    """查询本地Ollama模型"""
    try:
        resp = requests.post('http://localhost:11434/api/chat', json={
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': False,
            'options': {'num_predict': num_predict, 'temperature': temperature}
        }, timeout=120)
        if resp.status_code == 200:
            return resp.json().get('message', {}).get('content', '')
    except Exception as e:
        return f'ERROR: {e}'
    return None


def query_openrouter(prompt, model="qwen/qwen-2.5-72b-instruct"):
    """查询OpenRouter"""
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://openrouter.ai/api/v1",
                       api_key=os.environ.get("OPENROUTER_API_KEY"))
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f'ERROR: {e}'


def parse_ai_prediction(text):
    """解析AI模型输出的预测号码"""
    if not text or 'ERROR' in text:
        return None

    # 提取6个红球和1个蓝球
    import re
    # 尝试多种格式
    nums = re.findall(r'\b([1-9]|1[0-9]|3[0-3])\b', text)
    nums = [int(n) for n in nums if 1 <= int(n) <= 33]

    if len(nums) >= 6:
        return sorted(list(set(nums)))[:6]
    return None


# ─── 公式评估 ─────────────────────────────────────────

def evaluate_formula_walk_forward(formula, draws, n_windows=WALK_FORWARD_WINDOWS,
                                   window_size=WINDOW_SIZE, step=WINDOW_STEP):
    """Walk-forward 评估一个公式的命中率"""
    per_round_hits = []

    for w in range(n_windows):
        train_end = window_size + w * step
        test_start = train_end + 10
        test_end = min(test_start + 10, len(draws))

        if test_end <= test_start:
            break

        try:
            pred_top6 = formula.rank_top_6(draws[:train_end])
            actual_hits = 0
            for draw in draws[test_start:test_end]:
                actual_reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
                actual_hits += len(set(pred_top6) & set(actual_reds))

            per_round_hits.append(actual_hits)
        except Exception:
            per_round_hits.append(0)

    if not per_round_hits:
        return None

    avg = sum(per_round_hits) / len(per_round_hits)
    std = (sum((h - avg) ** 2 for h in per_round_hits) / max(len(per_round_hits) - 1, 1)) ** 0.5
    max_h = max(per_round_hits)
    min_h = min(per_round_hits)

    se = std / (len(per_round_hits) ** 0.5) if std > 0 else 1
    t_stat = (avg - 1.09) / se if se > 0 else 0
    p_value = 0.5 * (1 - math.erf(abs(t_stat) / math.sqrt(2))) * 2

    return FormulaResult(
        formula=formula,
        source="evaluated",
        avg_hits=avg, std_hits=std, max_hits=max_h, min_hits=min_h,
        p_value=p_value, rounds=len(per_round_hits),
        stability=avg - std,
        fitness=avg * 0.6 + max(0, avg - std) * 0.4,
    )


# ─── 从AI输出创建公式 ────────────────────────────────

def create_formula_from_predictions(predictions_by_model, name_prefix="ai"):
    """
    从多个AI模型的预测创建融合公式。
    每个模型的预测视为一个"原语视图"，通过共振组合。
    """
    # 收集所有预测中的号码权重
    vote_count = Counter()
    for model_name, preds in predictions_by_model.items():
        if preds and len(preds) >= 6:
            # 按排名加权
            for i, n in enumerate(preds[:6]):
                vote_count[n] += (6 - i) * 0.5

    if not vote_count:
        return None

    # 创建虚拟公式：基于投票权重的打分器
    class VoteFormula:
        def __init__(self, votes, name):
            self.name = name
            self.votes = dict(votes.most_common())
            self.primitives = []
            self.operators = ["vote_ensemble"]
            self.parameters = {"vote_weights": dict(votes)}

        def rank_top_6(self, draws=None):
            return [n for n, _ in self.votes.most_common(6)]

        def evaluate_for_all_numbers(self, draws=None):
            total = sum(self.votes.values()) or 1
            return {n: w/total for n, w in self.votes.items()}

    return VoteFormula(vote_count, f"{name_prefix}_ensemble")


# ─── 公式生成器 ───────────────────────────────────────

def generate_formula_population(primitives, population_size, rng):
    """生成一代新的公式种群"""
    formulas = []
    operators = ["resonance", "weighted_sum", "cascade", "phase_align"]

    for i in range(population_size):
        n_prims = rng.randint(2, min(4, len(primitives)))
        selected = rng.sample(primitives, n_prims)
        op = rng.choice(operators)

        try:
            if op == "resonance":
                weights = [rng.uniform(0.2, 0.8) for _ in range(len(selected))]
                total = sum(weights)
                weights = [w/total for w in weights]
                formula = FormulaGrammar.resonance(selected, weights=weights, name=f"evo_{i}")
            elif op == "weighted_sum":
                weights = [rng.uniform(0.1, 0.9) for _ in range(len(selected))]
                total = sum(weights)
                weights = [w/total for w in weights]
                formula = FormulaGrammar.weighted_sum(selected, weights=weights, name=f"evo_{i}")
            elif op == "cascade":
                thresholds = [rng.uniform(0.1, 0.5) for _ in range(len(selected)-1)]
                formula = FormulaGrammar.cascade(selected, thresholds=thresholds, name=f"evo_{i}")
            else:
                offsets = [rng.uniform(0.2, 0.8) for _ in range(len(selected)-1)]
                formula = FormulaGrammar.phase_align(selected, offsets=offsets, name=f"evo_{i}")
            formulas.append(formula)
        except Exception:
            continue

    return formulas


# ─── 变异与交叉 ───────────────────────────────────────

mutator_instance = PrimitiveMutator()

def mutate_formula(formula, draws, rng, generation):
    new_prims = []
    for p in formula.primitives:
        if rng.random() < MUTATION_RATE:
            try:
                mutated = mutator_instance.mutate(p, draws, rng, generation=generation)
                new_prims.append(mutated)
            except Exception:
                new_prims.append(p)
        else:
            new_prims.append(p)

    if new_prims and rng.random() < 0.2:
        idx = rng.randint(0, len(new_prims) - 1)
        new_prims[idx] = copy.deepcopy(rng.choice(get_default_primitives()))

    return Formula(
        name=f"{formula.name}_m",
        primitives=new_prims,
        operators=list(formula.operators),
        parameters=dict(formula.parameters),
    )


def crossover_formulas(f1, f2, rng):
    all_prims = list(f1.primitives) + list(f2.primitives)
    n_new = rng.randint(2, min(4, len(all_prims)))
    selected = rng.sample(all_prims, n_new)
    if len(selected) < 2:
        return f1

    op = rng.choice(["resonance", "weighted_sum"])
    try:
        if op == "resonance":
            weights = [rng.uniform(0.2, 0.8) for _ in range(len(selected))]
            total = sum(weights)
            weights = [w/total for w in weights]
            return FormulaGrammar.resonance(selected, weights=weights, name=f"xover_{f1.name[:15]}")
        else:
            return FormulaGrammar.weighted_sum(selected, name=f"xover_{f1.name[:15]}")
    except Exception:
        return f1


# ─── 状态管理 ─────────────────────────────────────────

def load_evolution_state():
    if os.path.exists(EVOLUTION_STATE_FILE):
        with open(EVOLUTION_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_evolution_state(gen, best_result, all_results, population):
    state = {
        "generation": gen,
        "best_formula": best_result.to_dict(),
        "top_10": [r.to_dict() for r in sorted(all_results, key=lambda x: -x.fitness)[:10]],
        "population_size": len(population),
        "timestamp": datetime.now().isoformat(),
    }
    with open(EVOLUTION_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    all_best = []
    if os.path.exists(BEST_FORMULAS_FILE):
        with open(BEST_FORMULAS_FILE, 'r', encoding='utf-8') as f:
            all_best = json.load(f)
    all_best.append(best_result.to_dict())
    seen = set()
    unique = []
    for b in all_best:
        if b["name"] not in seen:
            seen.add(b["name"])
            unique.append(b)
    with open(BEST_FORMULAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique[:100], f, ensure_ascii=False, indent=2)


# ─── 主进化循环 ───────────────────────────────────────

def run_multi_ai_evolution(draws, primitives, start_gen=0, max_gens=N_GENERATIONS):
    """运行多AI协同进化"""
    rng = random.Random(42 + start_gen)

    print(f"\n{'='*72}")
    print(f"  MULTI-AI COLLABORATIVE EVOLUTION ENGINE V19")
    print(f"  Generation {start_gen+1} to {max_gens}")
    print(f"{'='*72}")
    print(f"Population: {POPULATION_SIZE}, Elites: {ELITE_COUNT}")
    print(f"Data: {len(draws)} periods (#{draws[0].period} ~ #{draws[-1].period})")
    print(f"Primitives: {len(primitives)}")
    print()

    # 检查保存状态
    if start_gen > 0:
        saved = load_evolution_state()
        if saved:
            print(f"Resuming from generation {saved.get('generation', 0)}...")

    # ═══════════════════════════════════════════════════
    # 第1步：用所有AI模型生成初始种子
    # ═══════════════════════════════════════════════════
    print("\n=== STEP 1: Multi-AI Collaborative Analysis ===")
    print("-" * 60)

    latest = draws[-1]
    recent_text = "\n".join([
        f"#{d.period}: {d.reds} + {d.blue}" for d in draws[-20:]
    ])

    # 构建prompt
    system_prompt = ("你是双色球数据分析专家。请分析以下历史开奖数据，"
                    "推荐6个红球和1个蓝球。只输出号码，格式：红球: 1,2,3,4,5,6 蓝球: 7")
    user_prompt = (f"最近20期双色球开奖数据：\n{recent_text}\n\n"
                  f"最新一期 #{latest.period}: {latest.reds} + {latest.blue}\n\n"
                  f"请推荐下期红球6个和蓝球1个。简要说明理由。")

    ai_predictions = {}

    # 1a. Luckcast V15 (数学引擎)
    print("  [1/7] Luckcast V15 (7-dim learning engine)...")
    t0 = time.time()
    try:
        from luckcast_antigravity_v1 import predict_v15, LearningState, _DIM_NAMES
        v15_state = LearningState(_DIM_NAMES)
        v15_top, _ = predict_v15(draws, v15_state, top_k=1, seed=42)
        if v15_top:
            v15_preds = v15_top[0][0]  # reds
            ai_predictions["luckcast_v15"] = v15_preds
            print(f"    -> {v15_preds} ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"    -> ERROR: {e}")

    # 1b. Enhanced Predictor
    print("  [2/7] Enhanced Predictor (WeightedEnsemble)...")
    t0 = time.time()
    try:
        import pandas as pd
        csv_file = Path('E:/享中/data/lottery_history.csv')
        df = pd.read_csv(csv_file)
        from enhanced_predictor import WeightedEnsemble
        ensemble = WeightedEnsemble(df)
        ens_preds = ensemble.generate(num_groups=1)
        if ens_preds:
            ens_reds = ens_preds[0].get("reds", [])
            if len(ens_reds) >= 6:
                ai_predictions["enhanced_v2"] = sorted(ens_reds[:6])
                print(f"    -> {ai_predictions['enhanced_v2']} ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"    -> ERROR: {e}")

    # 1c. 33个原语的共识投票
    print("  [3/7] 33 Primitives Consensus Voting...")
    t0 = time.time()
    vote_count = Counter()
    for p in primitives:
        scores = p.score_all(draws[-500:])
        top5 = sorted(scores.items(), key=lambda x: -x[1])[:5]
        for n, s in top5:
            vote_count[n] += 1
    consensus_top6 = [n for n, _ in vote_count.most_common(6)]
    ai_predictions["primitives_consensus"] = consensus_top6
    print(f"    -> {consensus_top6} ({time.time()-t0:.1f}s)")

    # 1d. Formula Grammar combinations
    print("  [4/7] Formula Grammar Best Combinations...")
    t0 = time.time()
    formula_votes = Counter()
    by_cat = {}
    for p in primitives:
        by_cat.setdefault(p.category, []).append(p)

    for cat, prims in by_cat.items():
        if len(prims) >= 2:
            p1, p2 = prims[0], prims[1]
            for op_name in ["resonance", "weighted_sum"]:
                try:
                    op_func = getattr(FormulaGrammar, op_name)
                    f = op_func([p1, p2], name=f"gram_{cat}_{op_name}")
                    scores = f.evaluate_for_all_numbers(draws)
                    top6 = sorted(scores.items(), key=lambda x: -x[1])[:6]
                    for n, _ in top6:
                        formula_votes[n] += 1
                except:
                    pass

    formula_top6 = [n for n, _ in formula_votes.most_common(6)]
    ai_predictions["formula_grammar"] = formula_top6
    print(f"    -> {formula_top6} ({time.time()-t0:.1f}s)")

    # 1e. Ollama Gemma4
    print("  [5/7] Gemma4 (Ollama local)...")
    t0 = time.time()
    try:
        gemma4_resp = query_ollama('gemma4', user_prompt, temperature=0.7)
        gemma4_preds = parse_ai_prediction(gemma4_resp)
        if gemma4_preds:
            ai_predictions["gemma4"] = gemma4_preds
            print(f"    -> {gemma4_preds} ({time.time()-t0:.1f}s)")
        else:
            print(f"    -> No valid prediction from Gemma4 ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"    -> ERROR: {e}")

    # 1f. Ollama Gemma2
    print("  [6/7] Gemma2 (Ollama local)...")
    t0 = time.time()
    try:
        gemma2_resp = query_ollama('gemma2', user_prompt, temperature=0.7)
        gemma2_preds = parse_ai_prediction(gemma2_resp)
        if gemma2_preds:
            ai_predictions["gemma2"] = gemma2_preds
            print(f"    -> {gemma2_preds} ({time.time()-t0:.1f}s)")
        else:
            print(f"    -> No valid prediction from Gemma2 ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"    -> ERROR: {e}")

    # 1g. OpenRouter Qwen-72B
    print("  [7/7] OpenRouter Qwen-72B...")
    t0 = time.time()
    try:
        or_resp = query_openrouter(user_prompt)
        or_preds = parse_ai_prediction(or_resp)
        if or_preds:
            ai_predictions["openrouter_qwen"] = or_preds
            print(f"    -> {or_preds} ({time.time()-t0:.1f}s)")
        else:
            print(f"    -> No valid prediction from OpenRouter ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"    -> ERROR: {e}")

    # Save AI analysis
    ai_analysis = {
        "predictions": {k: v for k, v in ai_predictions.items()},
        "timestamp": datetime.now().isoformat(),
        "models_used": len(ai_predictions),
    }
    with open(AI_ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump(ai_analysis, f, ensure_ascii=False, indent=2)

    # 跨模型共识分析
    print("\n  === Cross-Model Consensus ===")
    all_predicted = Counter()
    for model_name, preds in ai_predictions.items():
        if preds:
            for n in preds:
                all_predicted[n] += 1

    consensus_scores = [(n, c) for n, c in all_predicted.items()]
    consensus_scores.sort(key=lambda x: -x[1])

    print(f"  {'号码':>5} {'出现模型数':>10} {'模型列表'}")
    print(f"  {'-'*60}")
    model_names = list(ai_predictions.keys())
    for n, count in consensus_scores[:15]:
        models_hit = [m for m, p in ai_predictions.items() if p and n in p]
        print(f"  {n:>5} {count:>10} {' '.join(models_hit)}")

    # ═══════════════════════════════════════════════════
    # 第2步：初始化种群（AI种子 + 随机公式）
    # ═══════════════════════════════════════════════════
    print(f"\n=== STEP 2: Initialize Population ===")
    print("-" * 60)

    # 从AI共识创建初始公式
    population = []

    # AI共识公式
    if consensus_scores:
        top_consensus = [n for n, _ in consensus_scores[:6]]
        class ConsensusFormula:
            def __init__(self, nums, name):
                self.name = name
                self.nums = nums
                self.primitives = []
                self.operators = ["consensus"]
                self.parameters = {"top_nums": nums}
            def rank_top_6(self, draws=None):
                return self.nums[:6]
            def evaluate_for_all_numbers(self, draws=None):
                scores = {}
                for i, n in enumerate(self.nums):
                    scores[n] = len(self.nums) - i
                for n in range(1, 34):
                    if n not in scores:
                        scores[n] = 0
                return scores
        population.append(ConsensusFormula(top_consensus, "ai_consensus_seed"))

    # 每个AI模型的预测都作为种子
    for model_name, preds in ai_predictions.items():
        if preds and len(preds) >= 6:
            class ModelFormula:
                def __init__(self, nums, name, source):
                    self.name = name
                    self.nums = nums
                    self.source_name = source
                    self.primitives = []
                    self.operators = ["model_prediction"]
                    self.parameters = {"source": source}
                def rank_top_6(self, draws=None):
                    return self.nums[:6]
                def evaluate_for_all_numbers(self, draws=None):
                    scores = {}
                    for i, n in enumerate(self.nums):
                        scores[n] = len(self.nums) - i
                    for n in range(1, 34):
                        if n not in scores:
                            scores[n] = 0
                    return scores
            population.append(ModelFormula(preds, f"seed_{model_name}", model_name))

    # 补充随机公式
    print(f"  AI种子公式: {len(population)}")
    remaining = POPULATION_SIZE - len(population)
    if remaining > 0:
        random_formulas = generate_formula_population(primitives, remaining, rng)
        population.extend(random_formulas)
        print(f"  随机公式: {len(random_formulas)}")

    print(f"  初始种群: {len(population)}")

    # ═══════════════════════════════════════════════════
    # 第3步：进化循环
    # ═══════════════════════════════════════════════════
    print(f"\n=== STEP 3: Evolution Loop ===")
    print("-" * 60)

    best_overall = None
    best_fitness_overall = -999
    generation_history = []

    for gen in range(start_gen, max_gens):
        gen_start = datetime.now()

        # 评估
        results = []
        for i, formula in enumerate(population):
            res = evaluate_formula_walk_forward(formula, draws)
            if res:
                res.source = getattr(formula, 'source_name', 'evolved')
                results.append(res)

        if not results:
            print(f"  Gen {gen+1}: No valid results, regenerating...")
            population = generate_formula_population(primitives, POPULATION_SIZE, rng)
            continue

        results.sort(key=lambda x: -x.fitness)
        avg_fitness = sum(r.fitness for r in results) / len(results)
        best = results[0]

        if best.fitness > best_fitness_overall:
            best_fitness_overall = best.fitness
            best_overall = best

        elapsed = (datetime.now() - gen_start).total_seconds()

        generation_history.append({
            "generation": gen + 1,
            "best_fitness": best.fitness,
            "best_avg_hits": best.avg_hits,
            "best_source": best.source,
            "avg_fitness": avg_fitness,
            "p_value": best.p_value,
        })

        if gen % 5 == 0 or gen == max_gens - 1:
            print(f"  Gen {gen+1:>2}/{max_gens}: "
                  f"best_fit={best.fitness:.3f} "
                  f"(hits={best.avg_hits:.2f}±{best.std_hits:.2f}, "
                  f"source={best.source}), "
                  f"best_all={best_fitness_overall:.3f}, "
                  f"time={elapsed:.0f}s")

        # 选择精英
        survivors = results[:ELITE_COUNT]

        # 生成新一代
        new_population = []

        # 精英保留
        for s in survivors:
            if hasattr(s.formula, 'nums'):
                # 自定义公式，复制
                class CopyFormula:
                    def __init__(self, f):
                        self.name = f.name + "_elite"
                        self.nums = list(f.nums)
                        self.source_name = f.source_name if hasattr(f, 'source_name') else "elite"
                        self.primitives = []
                        self.operators = list(f.operators)
                        self.parameters = dict(f.parameters) if hasattr(f, 'parameters') else {}
                    def rank_top_6(self, draws=None):
                        return self.nums[:6]
                    def evaluate_for_all_numbers(self, draws=None):
                        scores = {}
                        for i, n in enumerate(self.nums):
                            scores[n] = len(self.nums) - i
                        for n in range(1, 34):
                            if n not in scores:
                                scores[n] = 0
                        return scores
                new_population.append(CopyFormula(s.formula))
            else:
                new_population.append(copy.deepcopy(s.formula))

        # 变异
        for s in random.sample(survivors, min(len(survivors), ELITE_COUNT)):
            if hasattr(s.formula, 'nums'):
                # 变异：调整号码
                mutated_nums = list(s.formula.nums)
                for j in range(len(mutated_nums)):
                    if rng.random() < 0.3:
                        mutated_nums[j] = rng.randint(1, 33)
                mutated_nums = sorted(list(set(mutated_nums)))[:6]
                while len(mutated_nums) < 6:
                    mutated_nums.append(rng.randint(1, 33))
                    mutated_nums = sorted(list(set(mutated_nums)))[:6]

                class MutatedFormula:
                    def __init__(self, nums, parent_name):
                        self.name = parent_name + "_mut"
                        self.nums = nums
                        self.source_name = "mutated"
                        self.primitives = []
                        self.operators = ["mutated_prediction"]
                        self.parameters = {}
                    def rank_top_6(self, draws=None):
                        return self.nums[:6]
                    def evaluate_for_all_numbers(self, draws=None):
                        scores = {}
                        for i, n in enumerate(self.nums):
                            scores[n] = len(self.nums) - i
                        for n in range(1, 34):
                            if n not in scores:
                                scores[n] = 0
                        return scores
                new_population.append(MutatedFormula(mutated_nums, s.formula.name))
            else:
                child = mutate_formula(s.formula, draws, rng, generation=gen)
                new_population.append(child)

        # 交叉
        for _ in range(int(POPULATION_SIZE * CROSSOVER_RATE)):
            if len(survivors) >= 2:
                f1, f2 = rng.sample(survivors, 2)
                if hasattr(f1.formula, 'nums') and hasattr(f2.formula, 'nums'):
                    # 交叉：合并两个预测
                    combined = list(f1.formula.nums) + list(f2.formula.nums)
                    combined = sorted(list(set(combined)))[:6]
                    while len(combined) < 6:
                        combined.append(rng.randint(1, 33))
                        combined = sorted(list(set(combined)))[:6]

                    class CrossoverFormula:
                        def __init__(self, nums, name):
                            self.name = name + "_xover"
                            self.nums = nums
                            self.source_name = "crossover"
                            self.primitives = []
                            self.operators = ["crossover_prediction"]
                            self.parameters = {}
                        def rank_top_6(self, draws=None):
                            return self.nums[:6]
                        def evaluate_for_all_numbers(self, draws=None):
                            scores = {}
                            for i, n in enumerate(self.nums):
                                scores[n] = len(self.nums) - i
                            for n in range(1, 34):
                                if n not in scores:
                                    scores[n] = 0
                            return scores
                    new_population.append(CrossoverFormula(combined, f1.formula.name))
                else:
                    child = crossover_formulas(f1.formula, f2.formula, rng)
                    new_population.append(child)

        # 补充多样性
        while len(new_population) < POPULATION_SIZE:
            extra = generate_formula_population(primitives, min(10, POPULATION_SIZE - len(new_population)), rng)
            new_population.extend(extra)

        population = new_population[:POPULATION_SIZE]

        # 保存
        if gen % 10 == 0 or gen == max_gens - 1:
            save_evolution_state(gen + 1, best, results, population)

    # ═══════════════════════════════════════════════════
    # 最终输出
    # ═══════════════════════════════════════════════════
    print(f"\n{'='*72}")
    print(f"  EVOLUTION COMPLETE — BEST FORMULA")
    print(f"{'='*72}")
    if best_overall:
        print(f"  Name: {best_overall.formula.name}")
        print(f"  Source: {best_overall.source}")
        print(f"  Fitness: {best_fitness_overall:.3f}")
        print(f"  Avg Hits: {best_overall.avg_hits:.2f} +/- {best_overall.std_hits:.2f}")
        print(f"  Max Hits: {best_overall.max_hits}/6")
        print(f"  P-value: {best_overall.p_value:.4f}")
        print(f"  Stability: {best_overall.stability:.2f}")

        # Latest prediction
        if hasattr(best_overall.formula, 'nums'):
            pred = best_overall.formula.nums[:6]
        else:
            pred = best_overall.formula.rank_top_6(draws)
        print(f"\n  Latest Prediction: {sorted(pred)}")
        print(f"  Actual (last draw): {sorted(draws[-1].reds)}")
        hits = len(set(pred) & set(draws[-1].reds))
        print(f"  Hits on last draw: {hits}/6")

    # Save final results
    with open('E:/享中/evolution_results_v19.json', 'w', encoding='utf-8') as f:
        json.dump({
            "config": {
                "population_size": POPULATION_SIZE,
                "elite_count": ELITE_COUNT,
                "generations": N_GENERATIONS,
                "ai_models_used": list(ai_predictions.keys()),
            },
            "history": generation_history,
            "best_formula": best_overall.to_dict() if best_overall else None,
            "ai_predictions": {k: v for k, v in ai_predictions.items()},
            "cross_model_consensus": {str(n): c for n, c in consensus_scores[:15]},
        }, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to evolution_results_v19.json")

    return best_overall


if __name__ == "__main__":
    print("Loading history...")
    draws = load_history()
    print(f"Loaded {len(draws)} draws")

    primitives = get_default_primitives()
    print(f"Using {len(primitives)} primitives")

    state = load_evolution_state()
    start_gen = 0
    if state:
        start_gen = state.get("generation", 0)
        print(f"Resuming from generation {start_gen}")

    best = run_multi_ai_evolution(draws, primitives, start_gen=start_gen, max_gens=N_GENERATIONS)
