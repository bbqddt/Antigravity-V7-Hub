# -*- coding: utf-8 -*-
"""Multi-AI V19.4 — ALL 7 MODELS (bugfix + Gemini direct API + longer Ollama timeout)"""
import sys, os, json, re, time, requests
from collections import Counter
from datetime import datetime

os.environ["GEMINI_API_KEY"] = "AQ.Ab8RN6LOOMImRtxDePp4_AZ_6QF3gO0VYs3q-50kDf3Tq4kKog"
sys.path.insert(0, 'E:/享中')

from data_layer import load_history
draws = load_history()
latest = draws[-1]

print("="*80)
print(f"MULTI-AI V19.4 — ALL 7 MODELS | Latest: #{latest.period} {latest.reds}+{latest.blue}")
print("="*80)

recent_text = "\n".join([f"#{d.period}: {d.reds} B={d.blue}" for d in draws[-20:]])

all_preds = {}

# ── [1] Luckcast V15 ──
print("[1/7] Luckcast V15...", end=" ")
t0=time.time()
try:
    from luckcast_antigravity_v1 import predict_v15, LearningState, _DIM_NAMES
    st = LearningState(_DIM_NAMES)
    top,_ = predict_v15(draws,st,top_k=1,seed=42)
    p=top[0][0]; b=top[0][1] if len(top[0])>1 else None
    all_preds['luckcast_v15']={'red':p,'blue':b}
    print(f"OK ({time.time()-t0:.1f}s) R:{p} B:{b}")
except Exception as e: print(f"FAIL {e}")

# ── [2] Enhanced Predictor ──
print("[2/7] Enhanced Predictor...", end=" ")
t0=time.time()
try:
    import pandas as pd
    df=pd.read_csv('E:/享中/data/lottery_history.csv')
    from enhanced_predictor import WeightedEnsemble
    ep=WeightedEnsemble(df); pr=ep.generate(num_groups=1)
    if pr:
        all_preds['enhanced_v2']={'red':sorted(pr[0].get("reds",[])[:6]),'blue':pr[0].get("blue")}
        print(f"OK ({time.time()-t0:.1f}s) R:{all_preds['enhanced_v2']['red']}")
except Exception as e: print(f"FAIL {e}")

# ── [3] Primitives Consensus ──
print("[3/7] Primitives Consensus...", end=" ")
t0=time.time()
from formula_lang.primitive import get_default_primitives
pris=get_default_primitives(); vc=Counter()
for p in pris:
    sc=p.score_all(draws[-500:]); top5=sorted(sc.items(),key=lambda x:-x[1])[:5]
    for n,_ in top5: vc[n]+=1
ct=[n for n,_ in vc.most_common(6)]
all_preds['primitives']={'red':ct,'blue':None}
print(f"OK ({time.time()-t0:.1f}s) R:{ct}")

# ── [4] Formula Grammar ──
print("[4/7] Formula Grammar...", end=" ")
t0=time.time()
from formula_lang.grammar import FormulaGrammar
fv=Counter(); bc={}
for p in pris: bc.setdefault(p.category,[]).append(p)
for cat,ps in bc.items():
    if len(ps)>=2:
        for op in ["resonance","weighted_sum"]:
            try:
                f=getattr(FormulaGrammar,op)([ps[0],ps[1]],name=f"g_{cat}_{op}")
                sc=f.evaluate_for_all_numbers(draws)
                for n,_ in sorted(sc.items(),key=lambda x:-x[1])[:6]: fv[n]+=1
            except: pass
ft=[n for n,_ in fv.most_common(6)]
all_preds['formula_grammar']={'red':ft,'blue':None}
print(f"OK ({time.time()-t0:.1f}s) R:{ft}")

# ── [5] Gemma4 (Ollama, 180s timeout) ──
print("[5/7] Gemma4 (Ollama)...", end=" ")
t0=time.time()
g4r=g4b=None
try:
    resp=requests.post('http://localhost:11434/api/chat',json={
        'model':'gemma4','messages':[{'role':'user','content':
        'SSQ lottery prediction. Recent:\n'+recent_text+'\n\nOutput: Red: n,n,n,n,n,n Blue: n'}],
        'stream':False,'options':{'num_predict':100,'temperature':0.8}},timeout=180)
    if resp.status_code==200:
        c=resp.json().get('message',{}).get('content','')
        rm=re.search(r'Red:\s*([\d,\s]+)',c,re.I); bm=re.search(r'Blue:\s*(\d+)',c,re.I)
        if rm:
            nums=[int(x) for x in re.findall(r'\d+',rm.group(1)) if 1<=int(x)<=33]
            g4r=sorted(list(set(nums)))[:6]
        if bm:
            b=int(bm.group(1)); g4b=b if 1<=b<=16 else None
        if g4r: all_preds['gemma4']={'red':g4r,'blue':g4b}
    print(f"OK ({time.time()-t0:.1f}s) R:{g4r}" if g4r else f"EMPTY ({time.time()-t0:.1f}s)")
except Exception as e: print(f"FAIL {e} ({time.time()-t0:.1f}s)")

# ── [6] Gemma2 (Ollama, 180s timeout) ──
print("[6/7] Gemma2 (Ollama)...", end=" ")
t0=time.time()
g2r=g2b=None
try:
    resp=requests.post('http://localhost:11434/api/chat',json={
        'model':'gemma2','messages':[{'role':'user','content':
        'SSQ lottery prediction. Recent:\n'+recent_text+'\n\nOutput: Red: n,n,n,n,n,n Blue: n'}],
        'stream':False,'options':{'num_predict':100,'temperature':0.8}},timeout=180)
    if resp.status_code==200:
        c=resp.json().get('message',{}).get('content','')
        rm=re.search(r'Red:\s*([\d,\s]+)',c,re.I); bm=re.search(r'Blue:\s*(\d+)',c,re.I)
        if rm:
            nums=[int(x) for x in re.findall(r'\d+',rm.group(1)) if 1<=int(x)<=33]
            g2r=sorted(list(set(nums)))[:6]
        if bm:
            b=int(bm.group(1)); g2b=b if 1<=b<=16 else None
        if g2r: all_preds['gemma2']={'red':g2r,'blue':g2b}
    print(f"OK ({time.time()-t0:.1f}s) R:{g2r}" if g2r else f"EMPTY ({time.time()-t0:.1f}s)")
except Exception as e: print(f"FAIL {e} ({time.time()-t0:.1f}s)")

# ── [7] Gemini (direct REST API to avoid SDK auth issues) ──
print("[7/7] Gemini (REST API)...", end=" ")
t0=time.time()
gem_r=gem_b=None
try:
    api_key = os.environ["GEMINI_API_KEY"]
    model = "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text":
            f"SSQ lottery prediction. Recent draws:\n{recent_text}\n\nOutput ONLY: Red: n,n,n,n,n,n Blue: n"}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 200}
    }

    resp = requests.post(url, json=payload, timeout=120)
    if resp.status_code == 200:
        data = resp.json()
        c = data.get('candidates',[{}])[0].get('content',{}).get('parts',[{}])[0].get('text','')
        rm=re.search(r'Red:\s*([\d,\s]+)',c,re.I); bm=re.search(r'Blue:\s*(\d+)',c,re.I)
        if rm:
            nums=[int(x) for x in re.findall(r'\d+',rm.group(1)) if 1<=int(x)<=33]
            gem_r=sorted(list(set(nums)))[:6]
        if bm:
            b=int(bm.group(1)); gem_b=b if 1<=b<=16 else None
        if gem_r: all_preds['gemini']={'red':gem_r,'blue':gem_b}
        print(f"OK ({time.time()-t0:.1f}s) R:{gem_r}" if gem_r else f"PARSE FAIL: {c[:100]} ({time.time()-t0:.1f}s)")
    else:
        print(f"HTTP {resp.status_code}: {resp.text[:200]} ({time.time()-t0:.1f}s)")
except Exception as e: print(f"FAIL {e} ({time.time()-t0:.1f}s)")

# ═══════════ CONSENSUS ANALYSIS ═══════════
print(f"\n{'='*80}")
print(f"RESULTS: {len(all_preds)}/7 models succeeded")
print(f"{'='*80}")

for name,p in all_preds.items():
    print(f"  {name:<20}: {p['red']}")

nv=Counter()
for name,p in all_preds.items():
    for n in p['red']: nv[n]+=1

print(f"\n{'Num':>5} {'Votes':>5} {'Models'}")
print("-"*70)
for n,v in sorted(nv.items(),key=lambda x:-x[1]):
    ms=[m for m,p in all_preds.items() if n in p['red']]
    tag=""
    if v==len(all_preds): tag=" ★UNANIMOUS"
    elif v>=len(all_preds)*0.6: tag=" STRONG"
    print(f"{n:>5} {v:>5} {','.join(ms)}{tag}")

# Final pick — FIXED BUG
cons_nums = [n for n,v in nv.most_common() if v>=2]
final_red = cons_nums[:6]
while len(final_red)<6:
    for n,v in nv.most_common():
        if n not in final_red:
            final_red.append(n)
        if len(final_red)>=6: break

# Blue ball
blues=[p.get('blue') for p in all_preds.values() if p.get('blue') and isinstance(p['blue'],int)]
final_blue=Counter(blues).most_common(1)[0][0] if blues else Counter([d.blue for d in draws[-20:]]).most_common(1)[0][0]

print(f"\n{'='*80}")
print(f"FINAL RECOMMENDATION Period #{latest.period+1}")
print(f"{'='*80}")
print(f"  Red:   {sorted(final_red)}")
print(f"  Blue:  {final_blue}")

hits=len(set(final_red)&set(latest.reds))
print(f"\n  Verification vs #{latest.period}: {sorted(latest.reds)}")
print(f"  Hits: {hits}/6")
for n in sorted(final_red):
    print(f"    {n} {'✅' if n in latest.reds else ''}")

with open('E:/享中/multi_ai_v19_4.json','w',encoding='utf-8') as f:
    json.dump({'timestamp':datetime.now().isoformat(),'models':len(all_preds),
               'predictions':{k:v['red'] for k,v in all_preds.items()},
               'number_votes':dict(nv),'final':{'red':sorted(final_red),'blue':final_blue},
               'verification':{'period':latest.period,'actual':latest.reds,'hits':hits}},
              f,ensure_ascii=False,indent=2)
print(f"\nSaved to multi_ai_v19_4.json")
