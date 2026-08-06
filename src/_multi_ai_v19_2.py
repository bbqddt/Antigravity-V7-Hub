# -*- coding: utf-8 -*-
"""
Multi-AI Collaborative Analysis V19.2 — ALL 7 MODELS ONLINE

Configured:
1. Luckcast V15 ✅
2. Enhanced Predictor V2 ✅
3. 33 Primitives Consensus ✅
4. Formula Grammar ✅
5. Gemma4 (Ollama) ✅ OLLAMA RUNNING
6. Gemma2 (Ollama) ✅ OLLAMA RUNNING
7. Gemini (API Key configured) ✅ KEY PROVIDED
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os, json, math, random, time, requests, re
from pathlib import Path
from collections import Counter
from datetime import datetime

# Set Gemini API key
os.environ["GEMINI_API_KEY"] = "AQ.Ab8RN6LOOMImRtxDePp4_AZ_6QF3gO0VYs3q-50kDf3Tq4kKog"

sys.path.insert(0, 'E:/享中')
from data_layer import load_history

draws = load_history()
latest = draws[-1]

print("=" * 80)
print("MULTI-AI COLLABORATIVE ANALYSIS V19.2 — ALL 7 MODELS")
print("=" * 80)
print(f"Latest draw: #{latest.period} {latest.reds} + {latest.blue}")
print(f"Data: {len(draws)} periods")

# ─── Recent data context ───
recent_text = "\n".join([
    f"#{d.period}: reds={d.reds}, blue={d.blue}" for d in draws[-30:]
])

# ═══════════════════════════════════════════════════════
# MODEL 1: Luckcast V15
# ═══════════════════════════════════════════════════════
print("\n[1/7] Luckcast V15 (7-dim learning engine)...")
t0 = time.time()
try:
    from luckcast_antigravity_v1 import predict_v15, LearningState, _DIM_NAMES
    v15_state = LearningState(_DIM_NAMES)
    v15_top, _ = predict_v15(draws, v15_state, top_k=1, seed=42)
    if v15_top:
        v15_preds = v15_top[0][0]
        v15_blue = v15_top[0][1] if len(v15_top[0]) > 1 else None
        print(f"    Red: {v15_preds}, Blue: {v15_blue} ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"    ERROR: {e}")

# ═══════════════════════════════════════════════════════
# MODEL 2: Enhanced Predictor
# ═══════════════════════════════════════════════════════
print("[2/7] Enhanced Predictor (WeightedEnsemble)...")
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
        print(f"    Red: {sorted(reds[:6])}, Blue: {blue} ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"    ERROR: {e}")

# ═══════════════════════════════════════════════════════
# MODEL 3: 33 Primitives Consensus
# ═══════════════════════════════════════════════════════
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
print(f"    Red: {consensus_top6} ({time.time()-t0:.1f}s)")

# ═══════════════════════════════════════════════════════
# MODEL 4: Formula Grammar Best Combinations
# ═══════════════════════════════════════════════════════
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
print(f"    Red: {formula_top6} ({time.time()-t0:.1f}s)")

# ═══════════════════════════════════════════════════════
# MODEL 5: Gemma4 via Ollama
# ═══════════════════════════════════════════════════════
print("[5/7] Gemma4 (Ollama local)...")
t0 = time.time()
gemma4_red = gemma4_blue = None
try:
    resp = requests.post('http://localhost:11434/api/chat', json={
        'model': 'gemma4',
        'messages': [
            {
                'role': 'system',
                'content': 'You are a lottery number analyst. Analyze patterns in SSQ (双色球) lottery data. Predict the next 6 red balls (1-33) and 1 blue ball (1-16). Output ONLY in this exact format: Red: n,n,n,n,n,n Blue: n. Do not add any other text.'
            },
            {
                'role': 'user',
                'content': f'''Analyze these 30 recent SSQ draws:

{recent_text}

Based on frequency, omission, co-occurrence, and temporal patterns, predict the next draw.
Output format: Red: n,n,n,n,n,n Blue: n'''
            }
        ],
        'stream': False,
        'options': {'num_predict': 300, 'temperature': 0.8}
    }, timeout=180)

    if resp.status_code == 200:
        content = resp.json().get('message', {}).get('content', '')
        # Parse: Red: n,n,n,n,n,n Blue: n
        red_match = re.search(r'Red:\s*([\d,\s]+)', content, re.IGNORECASE)
        blue_match = re.search(r'Blue:\s*(\d+)', content, re.IGNORECASE)

        if red_match:
            raw_nums = re.findall(r'\d+', red_match.group(1))
            gemma4_red = sorted(list(set(int(n) for n in raw_nums if 1 <= int(n) <= 33)))[:6]
        if blue_match:
            b = int(blue_match.group(1))
            gemma4_blue = b if 1 <= b <= 16 else None

        if gemma4_red:
            print(f"    Red: {gemma4_red}, Blue: {gemma4_blue} ({time.time()-t0:.1f}s)")
        else:
            print(f"    Raw output: {content[:200]}")
            print(f"    Parsing failed ({time.time()-t0:.1f}s)")
    else:
        print(f"    HTTP {resp.status_code} ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"    ERROR: {e} ({time.time()-t0:.1f}s)")

# ═══════════════════════════════════════════════════════
# MODEL 6: Gemma2 via Ollama
# ═══════════════════════════════════════════════════════
print("[6/7] Gemma2 (Ollama local)...")
t0 = time.time()
gemma2_red = gemma2_blue = None
try:
    resp = requests.post('http://localhost:11434/api/chat', json={
        'model': 'gemma2',
        'messages': [
            {
                'role': 'system',
                'content': 'You are a lottery number analyst. Analyze patterns in SSQ (双色球) lottery data. Predict the next 6 red balls (1-33) and 1 blue ball (1-16). Output ONLY in this exact format: Red: n,n,n,n,n,n Blue: n. Do not add any other text.'
            },
            {
                'role': 'user',
                'content': f'''Analyze these 30 recent SSQ draws:

{recent_text}

Based on frequency, omission, co-occurrence, and temporal patterns, predict the next draw.
Output format: Red: n,n,n,n,n,n Blue: n'''
            }
        ],
        'stream': False,
        'options': {'num_predict': 300, 'temperature': 0.8}
    }, timeout=180)

    if resp.status_code == 200:
        content = resp.json().get('message', {}).get('content', '')
        red_match = re.search(r'Red:\s*([\d,\s]+)', content, re.IGNORECASE)
        blue_match = re.search(r'Blue:\s*(\d+)', content, re.IGNORECASE)

        if red_match:
            raw_nums = re.findall(r'\d+', red_match.group(1))
            gemma2_red = sorted(list(set(int(n) for n in raw_nums if 1 <= int(n) <= 33)))[:6]
        if blue_match:
            b = int(blue_match.group(1))
            gemma2_blue = b if 1 <= b <= 16 else None

        if gemma2_red:
            print(f"    Red: {gemma2_red}, Blue: {gemma2_blue} ({time.time()-t0:.1f}s)")
        else:
            print(f"    Raw output: {content[:200]}")
            print(f"    Parsing failed ({time.time()-t0:.1f}s)")
    else:
        print(f"    HTTP {resp.status_code} ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"    ERROR: {e} ({time.time()-t0:.1f}s)")

# ═══════════════════════════════════════════════════════
# MODEL 7: Gemini via Google AI API
# ═══════════════════════════════════════════════════════
print("[7/7] Gemini (Google AI)...")
t0 = time.time()
gemini_red = gemini_blue = None
try:
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""Analyze these 30 recent SSQ (双色球) lottery draws:

{recent_text}

Based on frequency analysis, omission patterns, co-occurrence pairs, and temporal trends, predict the next draw.
Output ONLY in this exact format:
Red: n,n,n,n,n,n
Blue: n

Where red balls are 1-33 and blue ball is 1-16."""

    result = model.generate_content(prompt, request_options={'timeout': 120})
    content = result.text

    red_match = re.search(r'Red:\s*([\d,\s]+)', content, re.IGNORECASE)
    blue_match = re.search(r'Blue:\s*(\d+)', content, re.IGNORECASE)

    if red_match:
        raw_nums = re.findall(r'\d+', red_match.group(1))
        gemini_red = sorted(list(set(int(n) for n in raw_nums if 1 <= int(n) <= 33)))[:6]
    if blue_match:
        b = int(blue_match.group(1))
        gemini_blue = b if 1 <= b <= 16 else None

    if gemini_red:
        print(f"    Red: {gemini_red}, Blue: {gemini_blue} ({time.time()-t0:.1f}s)")
    else:
        print(f"    Raw output: {content[:300]}")
        print(f"    Parsing failed ({time.time()-t0:.1f}s)")
except ImportError:
    print(f"    google-generativeai not installed ({time.time()-t0:.1f}s)")
except Exception as e:
    print(f"    ERROR: {e} ({time.time()-t0:.1f}s)")

# ═══════════════════════════════════════════════════════
# CROSS-MODEL CONSENSUS ANALYSIS
# ═══════════════════════════════════════════════════════
print(f"\n{'='*80}")
print("CROSS-MODEL CONSENSUS ANALYSIS")
print(f"{'='*80}")

all_predictions = {}
for name, preds in [
    ('luckcast_v15', locals().get('v15_preds')),
    ('enhanced_v2', locals().get('reds')),
    ('primitives_consensus', consensus_top6),
    ('formula_grammar', formula_top6),
    ('gemma4', gemma4_red),
    ('gemma2', gemma2_red),
    ('gemini', gemini_red),
]:
    if preds and isinstance(preds, list) and len(preds) >= 6:
        all_predictions[name] = preds[:6]
        print(f"  ✅ {name:<25}: {preds[:6]}")
    else:
        print(f"  ❌ {name:<25}: FAILED")

print(f"\nModels with valid predictions: {len(all_predictions)}/7")

if len(all_predictions) < 3:
    print("\n⚠️  Not enough models produced valid predictions.")
    print("   Need at least 3 models for meaningful consensus.")
    sys.exit(1)

# Build number vote distribution
number_votes = Counter()
for name, preds in all_predictions.items():
    for n in preds:
        number_votes[n] += 1

print(f"\nNumber vote distribution:")
print(f"  {'号码':>5} {'票数':>5} {'共识等级'} {'模型列表'}")
print(f"  {'-'*70}")
for n, votes in sorted(number_votes.items(), key=lambda x: -x[1]):
    models_hit = [m for m, p in all_predictions.items() if n in p]
    level = " unanimity" if votes == len(all_predictions) else "strong" if votes >= len(all_predictions)*0.7 else "moderate" if votes >= 2 else "weak"
    print(f"  {n:>5} {votes:>5} {level:<12} {', '.join(models_hit)}")

# Final recommendation
consensus_nums = [(n, v) for n, v in number_votes.most_common() if v >= 2]
final_red = [n for n, _ in consensus_nums[:6]]
if len(final_red) < 6:
    for n, v in number_votes.most_common():
        if n not in final_red:
            final_red.append(n)
        if len(final_red) >= 6:
            break

# Blue ball: majority vote
all_blues = []
for name, blue_var in [('luckcast_v15', locals().get('v15_blue')),
                        ('gemma4', gemma4_blue),
                        ('gemma2', gemma2_blue),
                        ('gemini', gemini_blue)]:
    if blue_var is not None and isinstance(blue_var, int):
        all_blues.append(blue_var)

if all_blues:
    blue_counter = Counter(all_blues)
    final_blue = blue_counter.most_common(1)[0][0]
else:
    blue_recent = [d.blue for d in draws[-20:]]
    final_blue = Counter(blue_recent).most_common(1)[0][0]

print(f"\n{'='*80}")
print(f"FINAL RECOMMENDATION for Period #{latest.period + 1}")
print(f"{'='*80}")
print(f"  Red balls: {sorted(final_red)}")
print(f"  Blue ball: {final_blue}")
print(f"  Models used: {len(all_predictions)}/7")
unanimous = [n for n, v in number_votes.items() if v == len(all_predictions)]
print(f"  Unanimous numbers: {unanimous}")
print(f"  Strong consensus (≥70%): {[n for n,v in number_votes.items() if v >= len(all_predictions)*0.7]}")

# Verification against latest draw
hits = len(set(final_red) & set(latest.reds))
print(f"\n  Verification vs latest draw #{latest.period}:")
print(f"    Actual:   {sorted(latest.reds)}")
print(f"    Predicted: {sorted(final_red)}")
print(f"    Hits: {hits}/6")
for n in final_red:
    marker = " ✅" if n in latest.reds else ""
    print(f"    {n}{marker}")

# Save results
result = {
    'timestamp': datetime.now().isoformat(),
    'target_period': latest.period + 1,
    'models_used': len(all_predictions),
    'total_models': 7,
    'predictions': {k: v for k, v in all_predictions.items()},
    'number_votes': dict(number_votes),
    'consensus_threshold_2plus': [n for n, v in number_votes.items() if v >= 2],
    'unanimous_numbers': unanimous,
    'final_recommendation': {
        'red': sorted(final_red),
        'blue': final_blue,
    },
    'verification_vs_latest': {
        'period': latest.period,
        'actual_reds': latest.reds,
        'predicted_reds': sorted(final_red),
        'hits': hits,
    },
}

with open('E:/享中/multi_ai_analysis_v19_2.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nResults saved to multi_ai_analysis_v19_2.json")
