# -*- coding: utf-8 -*-
"""
Fix LLM integration for Multi-AI Evolution Engine V19

Problems fixed:
1. Ollama prompt format (needs system message)
2. Number parsing regex (was too strict)
3. OpenRouter API call (was failing silently)
4. Add fallback: if LLM fails, use structured JSON output
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os, json, math, random, time, requests, re
from pathlib import Path
from collections import Counter
from datetime import datetime

sys.path.insert(0, 'E:/享中')
from data_layer import load_history

draws = load_history()
latest = draws[-1]

print("=" * 80)
print("FIXED: Multi-AI Collaborative Analysis (V19.1)")
print("=" * 80)
print(f"Latest draw: #{latest.period} {latest.reds} + {latest.blue}")

# ─── Recent data for context ───
recent_text = "\n".join([
    f"#{d.period}: reds={d.reds}, blue={d.blue}" for d in draws[-30:]
])

# ─── FIX 1: Ollama with proper format ───
def query_ollama_fixed(model, recent_draws_text):
    """Query Ollama with structured prompt that produces parseable output."""
    try:
        resp = requests.post('http://localhost:11434/api/chat', json={
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a lottery number analyst. Analyze the pattern of numbers in these draws and predict the next 6 red balls (1-33) and 1 blue ball (1-16). Output ONLY in this exact format: Red: n,n,n,n,n,n Blue: n. Do not add any other text.'
                },
                {
                    'role': 'user',
                    'content': f'''Analyze these 30 recent lottery draws:

{recent_draws_text}

Based on frequency analysis, omission patterns, and number relationships, predict the next draw.
Output format: Red: n,n,n,n,n,n Blue: n'''
                }
            ],
            'stream': False,
            'options': {'num_predict': 200, 'temperature': 0.8}
        }, timeout=180)

        if resp.status_code == 200:
            content = resp.json().get('message', {}).get('content', '')
            return content
        else:
            return f'HTTP {resp.status_code}'
    except Exception as e:
        return f'ERROR: {e}'


def parse_prediction(text):
    """Robust parser for lottery predictions in any format."""
    if not text or 'error' in text.lower()[:5]:
        return None, None

    # Extract all numbers 1-33 for red balls
    red_nums = re.findall(r'\b([1-9]|1[0-9]|2[0-9]|3[0-3])\b', text)
    red_nums = sorted(list(set(int(n) for n in red_nums if 1 <= int(n) <= 33)))

    # Extract blue ball (1-16)
    blue_nums = re.findall(r'Blue[:\s]*(\d+)', text, re.IGNORECASE)
    blue = int(blue_nums[0]) if blue_nums else None
    if blue and not (1 <= blue <= 16):
        blue = None

    # If we have at least 6 red numbers, return them
    if len(red_nums) >= 6:
        return red_nums[:6], blue

    # Fallback: if we found some numbers but not enough, fill from most common in history
    if red_nums:
        # Get omission for missing numbers
        omit = {}
        for n in range(1, 34):
            if n not in red_nums:
                o = 0
                for i in range(len(draws)-1, -1, -1):
                    if n not in draws[i].reds:
                        o += 1
                    else:
                        break
                omit[n] = o

        # Fill with highest omission numbers (cold numbers due for return)
        cold = sorted(omit.keys(), key=lambda x: -omit[x])
        red_nums.extend(cold[:6-len(red_nums)])
        red_nums = sorted(list(set(red_nums)))[:6]
        return red_nums, blue

    return None, blue


# ─── FIX 2: OpenRouter with better error handling ───
def query_openrouter_fixed():
    """Query OpenRouter with proper error handling."""
    try:
        from openai import OpenAI
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return "NO_API_KEY"

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

        resp = client.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[
                {"role": "system", "content": "You are a lottery number analyst. Predict the next 6 red balls (1-33) and 1 blue ball (1-16). Output ONLY: Red: n,n,n,n,n,n Blue: n"},
                {"role": "user", "content": f"Predict next SSQ draw. Recent data:\n{recent_text[-500:]}"}
            ],
            temperature=0.8,
            max_tokens=200,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"ERROR: {str(e)[:100]}"


# ─── Run all AI models ───
print("\n=== Running All AI Models ===\n")

ai_results = {}

# Model 1: Luckcast V15
print("[1/7] Luckcast V15...")
t0 = time.time()
try:
    from luckcast_antigravity_v1 import predict_v15, LearningState, _DIM_NAMES
    v15_state = LearningState(_DIM_NAMES)
    v15_top, _ = predict_v15(draws, v15_state, top_k=1, seed=42)
    if v15_top:
        v15_preds = v15_top[0][0]
        ai_results['luckcast_v15'] = {'red': v15_preds, 'blue': v15_top[0][1] if len(v15_top[0]) > 1 else None}
        print(f"    Red: {v15_preds}, Blue: {ai_results['luckcast_v15']['blue']} ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"    ERROR: {e}")

# Model 2: Enhanced Predictor
print("[2/7] Enhanced Predictor...")
t0 = time.time()
try:
    import pandas as pd
    df = pd.read_csv('E:/享中/data/lottery_history.csv')
    from enhanced_predictor import WeightedEnsemble
    ensemble = WeightedEnsemble(df)
    ens_preds = ensemble.generate(num_groups=1)
    if ens_preds:
        reds = ens_preds[0].get("reds", [])
        blue = ens_preds[0].get("blue", None)
        if len(reds) >= 6:
            ai_results['enhanced_v2'] = {'red': sorted(reds[:6]), 'blue': blue}
            print(f"    Red: {sorted(reds[:6])}, Blue: {blue} ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"    ERROR: {e}")

# Model 3: Primitives Consensus
print("[3/7] 33 Primitives Consensus...")
t0 = time.time()
from formula_lang.primitive import get_default_primitives
primitives = get_default_primitives()
vote_count = Counter()
for p in primitives:
    scores = p.score_all(draws[-500:])
    top5 = sorted(scores.items(), key=lambda x: -x[1])[:5]
    for n, s in top5:
        vote_count[n] += 1
consensus_top6 = [n for n, _ in vote_count.most_common(6)]
ai_results['primitives_consensus'] = {'red': consensus_top6, 'blue': None}
print(f"    Red: {consensus_top6} ({time.time()-t0:.1f}s)")

# Model 4: Formula Grammar
print("[4/7] Formula Grammar Best Combinations...")
t0 = time.time()
from formula_lang.grammar import FormulaGrammar
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
                f = op_func([p1, p2], name=f"g_{cat}_{op_name}")
                scores = f.evaluate_for_all_numbers(draws)
                top6 = sorted(scores.items(), key=lambda x: -x[1])[:6]
                for n, _ in top6:
                    formula_votes[n] += 1
            except:
                pass
formula_top6 = [n for n, _ in formula_votes.most_common(6)]
ai_results['formula_grammar'] = {'red': formula_top6, 'blue': None}
print(f"    Red: {formula_top6} ({time.time()-t0:.1f}s)")

# Model 5: Gemma4 (FIXED)
print("[5/7] Gemma4 (Ollama)...")
t0 = time.time()
gemma4_resp = query_ollama_fixed('gemma4', recent_text)
gemma4_red, gemma4_blue = parse_prediction(gemma4_resp)
if gemma4_red:
    ai_results['gemma4'] = {'red': gemma4_red, 'blue': gemma4_blue}
    print(f"    Red: {gemma4_red}, Blue: {gemma4_blue} ({time.time()-t0:.1f}s)")
else:
    print(f"    No valid prediction from Gemma4: {gemma4_resp[:200]} ({time.time()-t0:.1f}s)")

# Model 6: Gemma2 (FIXED)
print("[6/7] Gemma2 (Ollama)...")
t0 = time.time()
gemma2_resp = query_ollama_fixed('gemma2', recent_text)
gemma2_red, gemma2_blue = parse_prediction(gemma2_resp)
if gemma2_red:
    ai_results['gemma2'] = {'red': gemma2_red, 'blue': gemma2_blue}
    print(f"    Red: {gemma2_red}, Blue: {gemma2_blue} ({time.time()-t0:.1f}s)")
else:
    print(f"    No valid prediction from Gemma2: {gemma2_resp[:200]} ({time.time()-t0:.1f}s)")

# Model 7: OpenRouter Qwen-72B (FIXED)
print("[7/7] OpenRouter Qwen-72B...")
t0 = time.time()
or_resp = query_openrouter_fixed()
or_red, or_blue = parse_prediction(or_resp)
if or_red:
    ai_results['openrouter_qwen'] = {'red': or_red, 'blue': or_blue}
    print(f"    Red: {or_red}, Blue: {or_blue} ({time.time()-t0:.1f}s)")
else:
    print(f"    No valid prediction from OpenRouter: {or_resp[:200]} ({time.time()-t0:.1f}s)")

# ─── Cross-model consensus analysis ───
print(f"\n{'='*80}")
print("CROSS-MODEL CONSENSUS ANALYSIS")
print(f"{'='*80}")

all_red_predictions = {k: v['red'] for k, v in ai_results.items() if v.get('red')}
print(f"\nModels with valid predictions: {len(all_red_predictions)}")
for model, preds in all_red_predictions.items():
    print(f"  {model:<30}: {preds}")

# Build consensus
number_votes = Counter()
for preds in all_red_predictions.values():
    for n in preds:
        number_votes[n] += 1

print(f"\nNumber vote distribution:")
print(f"  {'号码':>5} {'票数':>5} {'共识等级'}")
print(f"  {'-'*40}")
for n, votes in sorted(number_votes.items(), key=lambda x: -x[1]):
    level = " unanimity" if votes == len(all_red_predictions) else "strong" if votes >= len(all_red_predictions)*0.7 else "moderate" if votes >= 2 else "weak"
    print(f"  {n:>5} {votes:>5} {level} ({votes}/{len(all_red_predictions)} models)")

# Top consensus numbers
top_consensus = [(n, v) for n, v in number_votes.most_common() if v >= 2]
print(f"\nConsensus numbers (≥2 models agree): {[n for n,_ in top_consensus]}")

# Final recommendation
if top_consensus:
    final_red = [n for n, _ in top_consensus[:6]]
    if len(final_red) < 6:
        # Fill with single-vote numbers
        for n, v in number_votes.most_common():
            if n not in final_red:
                final_red.append(n)
            if len(final_red) >= 6:
                break

    # Blue ball: majority vote or most recent
    blues = [v['blue'] for v in ai_results.values() if v.get('blue')]
    if blues:
        blue_counter = Counter(blues)
        final_blue = blue_counter.most_common(1)[0][0]
    else:
        # Use formula-based blue prediction
        blue_recent = [d.blue for d in draws[-20:]]
        final_blue = Counter(blue_recent).most_common(1)[0][0]

    print(f"\n{'='*80}")
    print(f"FINAL MULTI-AI RECOMMENDATION for Period #{latest.period + 1}")
    print(f"{'='*80}")
    print(f"  Red balls: {sorted(final_red)}")
    print(f"  Blue ball: {final_blue}")
    print(f"  Consensus strength: {len(top_consensus)}/{len(all_red_predictions)} models agreed on at least 1 number")
    print(f"  Unanimous numbers: {[n for n,v in number_votes.items() if v == len(all_red_predictions)]}")

    # Compare with latest actual
    hits = len(set(final_red) & set(latest.reds))
    print(f"\n  Verification against latest draw #{latest.period}:")
    print(f"    Actual:   {sorted(latest.reds)}")
    print(f"    Predicted: {sorted(final_red)}")
    print(f"    Hits: {hits}/6")

# Save results
with open('E:/享中/multi_ai_analysis_v19_1.json', 'w', encoding='utf-8') as f:
    json.dump({
        'timestamp': datetime.now().isoformat(),
        'models_used': len(all_red_predictions),
        'total_models_attempted': len(ai_results),
        'predictions': {k: v['red'] for k, v in ai_results.items()},
        'blue_predictions': {k: v['blue'] for k, v in ai_results.items() if v.get('blue')},
        'number_votes': dict(number_votes),
        'consensus_numbers': [n for n, v in number_votes.items() if v >= 2],
        'unanimous_numbers': [n for n, v in number_votes.items() if v == len(all_red_predictions)],
        'final_recommendation': {
            'red': sorted(final_red) if 'final_red' in dir() else [],
            'blue': final_blue if 'final_blue' in dir() else None,
        },
        'latest_actual': {
            'period': latest.period,
            'reds': latest.reds,
            'blue': latest.blue,
        },
    }, f, ensure_ascii=False, indent=2)

print(f"\nResults saved to multi_ai_analysis_v19_1.json")
