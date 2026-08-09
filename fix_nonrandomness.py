# fix_nonrandomness.py
with open('nonrandomness_detector.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有危险的 split(',') 用法
content = content.replace(
    "[int(x.strip()) for x in str(row['red']).split(',')]",
    "[int(x.strip()) for x in str(row['red']).strip().strip('[] ').split(',') if x.strip()]"
)
content = content.replace(
    "[int(x.strip()) for x in str(row['red']).split(',') if x.strip()]",
    "[int(x.strip()) for x in str(row['red']).strip().strip('[] ').split(',') if x.strip()]"
)

with open('nonrandomness_detector.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')