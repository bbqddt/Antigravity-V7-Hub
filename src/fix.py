import re
p = r'E:\享中\formula_evolution.py'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if '初始化种群' in line and '个公式' in line and not line.strip().endswith('\")'):
        lines[i] = line.replace('个公式', '个公式\")')
        print('Fixed line', i+1)
with open(p, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done')
