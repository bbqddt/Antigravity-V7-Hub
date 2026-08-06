with open("E:/享中/formula_evolution.py", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

fixed = []
for line in lines:
    # 修复未关闭的logger语句
    stripped = line.rstrip()
    if stripped.startswith("logger.info") or stripped.startswith("logger.warning"):
        # 检查是否有未闭合的引号
        quote_count = stripped.count('"')
        if quote_count % 2 != 0:
            # 移除末尾引号并重新闭合
            if stripped.endswith('"'):
                stripped = stripped[:-1]
            # 确保以")结尾
            if not stripped.endswith('")'):
                stripped = stripped + '")'
    fixed.append(stripped + "\n")

with open("E:/享中/formula_evolution.py", "w", encoding="utf-8") as f:
    f.writelines(fixed)

print("Fixed")
