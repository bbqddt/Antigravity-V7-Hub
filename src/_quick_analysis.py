# -*- coding: utf-8 -*-
"""Quick data quality analysis for SSQ history"""
import csv, math
from collections import Counter

draws = []
with open('data/lottery_history.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        period = int(row['period'])
        reds = [int(x.strip()) for x in row['red'].split(',')]
        blue = int(row['blue'])
        draws.append({'period': period, 'reds': sorted(reds), 'blue': blue})

print(f'Total periods: {len(draws)}')
d0 = draws[0]
print(f'First: #{d0["period"]} reds={d0["reds"]} blue={d0["blue"]}')
d1 = draws[-1]
print(f'Last:  #{d1["period"]} reds={d1["reds"]} blue={d1["blue"]}')

# Frequency
freq = Counter()
for d in draws:
    for r in d['reds']:
        freq[r] += 1
freq_arr = sorted(freq.items(), key=lambda x: -x[1])

print('\n=== Red Ball Frequency Top-10 (hottest) ===')
for n, c in freq_arr[:10]:
    print(f'  {n:02d}: {c} times ({c/len(draws)*100:.1f}%)')

print('\n=== Red Ball Frequency Bottom-10 (coldest) ===')
for n, c in freq_arr[-10:][::-1]:
    print(f'  {n:02d}: {c} times ({c/len(draws)*100:.1f}%)')

# Blue frequency
blue_freq = Counter(d['blue'] for d in draws)
blue_arr = sorted(blue_freq.items(), key=lambda x: -x[1])
print('\n=== Blue Ball Frequency Top-5 ===')
for n, c in blue_arr[:5]:
    print(f'  {n:02d}: {c} times ({c/len(draws)*100:.1f}%)')

# Omission
omissions = {n: 0 for n in range(1, 34)}
max_om = {n: 0 for n in range(1, 34)}
for d in draws:
    for n in range(1, 34):
        if n in d['reds']:
            if omissions[n] > max_om[n]:
                max_om[n] = omissions[n]
            omissions[n] = 0
        else:
            omissions[n] += 1
cur_om = sorted([(n, omissions[n], max_om[n]) for n in range(1, 34)], key=lambda x: -x[1])
print('\n=== Current Omission Top-10 ===')
for n, cur, mx in cur_om[:10]:
    print(f'  {n:02d}: current={cur}, historical_max={mx}')

# Sum distribution
sums = [sum(d['reds']) for d in draws]
mean_s = sum(sums)/len(sums)
std_s = (sum((s-mean_s)**2 for s in sums)/len(sums))**0.5
print(f'\n=== Sum Distribution ===')
print(f'  mean={mean_s:.1f}, std={std_s:.1f}')
print(f'  min={min(sums)}, max={max(sums)}')
sorted_sums = sorted(sums)
print(f'  median={sorted_sums[len(sorted_sums)//2]}')

# Runs test
print(f'\n=== Runs Test ===')
for target in [1, 5, 10, 15, 20, 25, 30]:
    ap = [1 if target in d['reds'] else 0 for d in draws]
    runs = 1
    for i in range(1, len(ap)):
        if ap[i] != ap[i-1]:
            runs += 1
    n1 = sum(ap)
    n0 = len(ap) - n1
    exp_runs = 2*n1*n0/len(ap) + 1
    var_r = 2*n1*n0*(2*n1*n0-len(ap))/(len(ap)**2*(len(ap)-1))
    z = (runs-exp_runs)/(var_r**0.5) if var_r > 0 else 0
    flag = 'NON-RANDOM' if abs(z)>1.96 else 'OK'
    print(f'  {target:02d}: appeared {n1}/{len(ap)}, runs={runs}, Z={z:.2f} [{flag}]')

# Pair co-occurrence
pair_count = {}
for i in range(1, 34):
    for j in range(i+1, 34):
        pair_count[f'{i}-{j}'] = 0
for d in draws:
    rs = d['reds']
    for i in range(6):
        for j in range(i+1, 6):
            pair_count[f'{rs[i]}-{rs[j]}'] += 1
pairs = [(k,v) for k,v in pair_count.items() if v > 0]
pairs.sort(key=lambda x: -x[1])
print(f'\n=== Pair Co-occurrence ===')
print(f'  Total pairs seen: {len(pairs)}')
print(f'  Top-10:')
for p, c in pairs[:10]:
    print(f'    {p}: {c} times ({c/len(draws)*100:.1f}%)')
exp_rate = 15/528
hot = sum(1 for _, c in pairs if c/len(draws) > exp_rate*1.5)
print(f'  Random expectation: {exp_rate*100:.1f}%')
print(f'  Pairs >1.5x random: {hot}')
