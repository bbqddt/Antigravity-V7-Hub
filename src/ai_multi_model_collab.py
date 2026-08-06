# -*- coding: utf-8 -*-
"""
AI多模型协同计算 - Gemma4 + Gemma2 + 公式语言联合分析
"""
import sys, json, time, requests, os
from collections import Counter
sys.path.insert(0, 'E:/享中')
from data_layer import load_history
from formula_lang import get_default_primitives, FormulaGrammar
from luckcast_antigravity_v1 import predict_v15, LearningState, _DIM_NAMES

draws = load_history()
latest = draws[-1]
prev = draws[-2]

print('='*70)
print('  AI多模型协同计算 - 公式分析与预测')
print('='*70)
print('数据: #%d %s+%d | 上期: #%d %s+%d' % (latest.period, latest.reds, latest.blue, prev.period, prev.reds, prev.blue))

# ═══════════════════════════════════════════════════════════
# 1. Gemma4 本地推理
# ═══════════════════════════════════════════════════════════
print('\n--- [1/5] Gemma4 本地分析 ---')
t0 = time.time()
gemma4_response = ''
try:
    prompt = """最近5期:
#%d: %s + %d
#%d: %s + %d
#%d: %s + %d
#%d: %s + %d
#%d: %s + %d
共%d期。请推荐红球6个+蓝球1个，附简短理由。""" % (
        latest.period, latest.reds, latest.blue,
        prev.period, prev.reds, prev.blue,
        draws[-3].period, draws[-3].reds, draws[-3].blue,
        draws[-4].period, draws[-4].reds, draws[-4].blue,
        draws[-5].period, draws[-5].reds, draws[-5].blue,
        len(draws)
    )
    # Gemma4: 增加timeout到300s，使用精简prompt减少输出量
    resp = requests.post('http://localhost:11434/api/chat', json={
        'model': 'gemma4',
        'messages': [
            {'role': 'system', 'content': '双色球分析专家。只输出号码推荐和分析要点，不要长篇大论。'},
            {'role': 'user', 'content': prompt}
        ],
        'stream': False,
        'options': {'num_predict': 500, 'temperature': 0.7}
    }, timeout=300)
    if resp.status_code == 200:
        gemma4_response = resp.json().get('message', {}).get('content', '')
        print(gemma4_response[:600])
    else:
        gemma4_response = 'HTTP %d' % resp.status_code
except Exception as e:
    gemma4_response = 'ERROR: ' + str(e)
print('耗时: %.1fs' % (time.time()-t0))

# ═══════════════════════════════════════════════════════════
# 2. Gemma2 本地推理 (交叉验证)
# ═══════════════════════════════════════════════════════════
print('\n--- [2/5] Gemma2 本地分析 ---')
t0 = time.time()
gemma2_response = ''
try:
    resp = requests.post('http://localhost:11434/api/chat', json={
        'model': 'gemma2',
        'messages': [
            {'role': 'system', 'content': '你是双色球数据分析专家。用简洁中文回答。'},
            {'role': 'user', 'content': prompt}
        ],
        'stream': False,
        'options': {'num_predict': 1000, 'temperature': 0.7}
    }, timeout=300)
    if resp.status_code == 200:
        gemma2_response = resp.json().get('message', {}).get('content', '')
        print(gemma2_response[:600])
    else:
        gemma2_response = 'HTTP %d' % resp.status_code
except Exception as e:
    gemma2_response = 'ERROR: ' + str(e)
print('耗时: %.1fs' % (time.time()-t0))

# ═══════════════════════════════════════════════════════════
# 3. 公式语言 + AI协同打分
# ═══════════════════════════════════════════════════════════
print('\n--- [3/5] 公式语言 + AI协同打分 ---')
primitives = get_default_primitives()

# 回测Top-10原语
bt_top10 = ['binary_topology', 'digit_pair_freq', 'recency_gradient',
            'distance_cluster', 'gap_pattern', 'cooccurrence_affinity',
            'scale_transition', 'periodic_echo', 'attractor_distance', 'periodic_gap']

score_card = {}
for n in range(1, 34): score_card[n] = 0

# 原语打分
for name in bt_top10:
    prim = next((p for p in primitives if p.name == name), None)
    if not prim: continue
    scores = prim.score_all(draws)
    sorted_s = sorted(scores.items(), key=lambda x: -x[1])
    top_val = sorted_s[0][1]
    bot_val = sorted_s[-1][1]
    spread = top_val - bot_val if top_val != bot_val else 1

    for n in range(1, 34):
        norm = (scores[n] - bot_val) / spread if spread > 0 else 0.5
        score_card[n] += norm

# 特征1: 遗漏回补
omit_val = {}
for n in range(1, 34):
    o = 0
    for i in range(len(draws)-1, -1, -1):
        if n not in draws[i].reds: o += 1
        else: break
    omit_val[n] = o
    if o > 500: score_card[n] += 0.5
    elif o > 100: score_card[n] += 0.2

# 特征2: 近期频率
recent_freq = {}
for n in range(1, 34): recent_freq[n] = 0
for d in draws[-20:]:
    for r in d.reds: recent_freq[r] += 1
for n in range(1, 34):
    if recent_freq[n] >= 3: score_card[n] += 0.3
    elif recent_freq[n] == 0: score_card[n] -= 0.1

# 特征3: 位置偏好
pos_pref = [[0]*6 for _ in range(34)]
for d in draws:
    reds = sorted(d.reds)
    for i, r in enumerate(reds): pos_pref[r][i] += 1
for pos in range(6):
    pos_freq = [(n, pos_pref[n][pos]) for n in range(1, 34)]
    pos_freq.sort(key=lambda x: -x[1])
    for n, _ in pos_freq[:5]:
        score_card[n] += 0.1

# 特征4: 共现网络
cooccur = {}
for n in range(1, 34): cooccur[n] = {}
for d in draws[-50:]:
    reds = sorted(d.reds)
    for i in range(6):
        for j in range(i+1, 6):
            a, b = reds[i], reds[j]
            cooccur[a][b] = cooccur[a].get(b, 0) + 1
            cooccur[b][a] = cooccur[b].get(a, 0) + 1
for n in range(1, 34):
    if n in cooccur:
        top_p = sorted(cooccur[n].items(), key=lambda x: -x[1])[:3]
        score_card[n] += sum(c for _,c in top_p) * 0.01

print('AI协同打分完成')
print('Top-12号码:')
sorted_cards = sorted(score_card.items(), key=lambda x: -x[1])
for n, s in sorted_cards[:12]:
    om = omit_val.get(n, 0)
    rf = recent_freq.get(n, 0)
    sig = ''
    if om > 500: sig += ' [大遗漏]'
    if rf >= 3: sig += ' [近期热]'
    elif rf == 0: sig += ' [近期冷]'
    print('  %2d. 号码%2d: %.2f%s' % (sorted_cards.index((n,s))+1, n, s, sig))

# ═══════════════════════════════════════════════════════════
# 4. 公式组合验证
# ═══════════════════════════════════════════════════════════
print('\n--- [4/5] 公式组合验证 ---')
top5_bt_names = bt_top10[:5]
top5_prims = [next(p for p in primitives if p.name == n) for n in top5_bt_names]

for op_name in ['cascade', 'phase_align', 'weighted_sum']:
    op_func = getattr(FormulaGrammar, op_name)
    try:
        f = op_func(top5_prims, name='ai_%s' % op_name)
        scores = f.evaluate_for_all_numbers(draws)
        top6 = sorted(scores.items(), key=lambda x: -x[1])[:6]
        top6_nums = sorted([n for n,_ in top6])
        hits = len(set(top6_nums) & set(latest.reds))
        print('  %s: %s (最新一期命中=%d/6)' % (op_name, top6_nums, hits))
    except Exception as e:
        print('  %s: ERROR - %s' % (op_name, e))

# ═══════════════════════════════════════════════════════════
# 5. V15引擎 + 公式组合 + AI打分 三合一
# ═══════════════════════════════════════════════════════════
print('\n--- [5/5] 三合一综合推荐 ---')

# V15引擎
v15_state = LearningState(_DIM_NAMES)
v15_top, _ = predict_v15(draws, v15_state, top_k=10, seed=42)
for red, blue, scores in v15_top[:5]:
    for n in red:
        score_card[n] += 0.5

# 公式组合
for op_name in ['cascade', 'phase_align', 'weighted_sum']:
    op_func = getattr(FormulaGrammar, op_name)
    try:
        f = op_func(top5_prims, name='final_%s' % op_name)
        scores = f.evaluate_for_all_numbers(draws)
        top6 = sorted(scores.items(), key=lambda x: -x[1])[:6]
        for n, _ in top6:
            score_card[n] += 0.3
    except:
        pass

# 最终排序
final_ranked = sorted(score_card.items(), key=lambda x: -x[1])

print('\nAI + 公式 + V15 三合一推荐 Top-12:')
for rank, (n, s) in enumerate(final_ranked[:12], 1):
    om = omit_val.get(n, 0)
    rf = recent_freq.get(n, 0)
    sig = ''
    if om > 500: sig += ' [大遗漏]'
    if rf >= 3: sig += ' [近期热]'
    elif rf == 0: sig += ' [近期冷]'
    in_latest = ' ***' if n in latest.reds else ''
    print('  %2d. 号码%2d: %.2f%s%s' % (rank, n, s, sig, in_latest))

# 蓝球
blue_recent = [d.blue for d in draws[-20:]]
blue_ctr = Counter(blue_recent)
blue_scores = {}
for n in range(1, 17):
    blue_scores[n] = blue_ctr.get(n, 0) * 2 + (16 - abs(n - latest.blue)) * 0.1
sorted_blue = sorted(blue_scores.items(), key=lambda x: -x[1])

print('\n蓝球推荐 Top-5:')
for n, s in sorted_blue[:5]:
    print('  %d (得分%.1f)' % (n, s))

# 最终推荐
top6_final = sorted([n for n,_ in final_ranked[:6]])
top5_blue = [n for n,_ in sorted_blue[:5]]

print('\n' + '='*70)
print('  最终推荐 - 第%d期' % (latest.period + 1))
print('='*70)
print('  红球: %s' % top6_final)
print('  蓝球: %s' % top5_blue)
print('='*70)

# 保存结果
result = {
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'target_period': latest.period + 1,
    'gemma4_used': 'gemma4' in gemma4_response if gemma4_response else False,
    'gemma2_used': 'gemma2' in gemma2_response if gemma2_response else False,
    'ai_collab_scores': {str(k): round(v, 4) for k, v in sorted_cards[:12]},
    'final_recommendation': {
        'red': top6_final,
        'blue': top5_blue,
        'scores': {str(k): round(v, 4) for k, v in final_ranked[:12]}
    }
}
with open('E:/享中/ai_collab_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print('\n结果已保存: ai_collab_result.json')
