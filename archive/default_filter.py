# 自主演进生成的进阶策略
def filter_logic(results):
    # 进阶逻辑：过滤掉奇偶比极端的情况 [0:6, 6:0]
    filtered = []
    for r in results:
        reds = [int(x) for x in r.split(',')]
        odds = len([x for x in reds if x % 2 != 0])
        if 1 <= odds <= 5:
            filtered.append(r)
    return filtered
