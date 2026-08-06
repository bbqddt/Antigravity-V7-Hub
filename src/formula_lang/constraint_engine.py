# -*- coding: utf-8 -*-
"""
预测结果后处理约束引擎 V1.0

核心问题: 各原语投票选出的Top-6号码可能严重违背双色球物理约束
例如: [2,3,4,5,22,30] — 4个连续个位数，历史上从未出现

解决方案: 在投票聚合后，用硬约束过滤+替换，确保输出符合历史分布
"""

from data_layer import Draw


# 从历史数据统计的分布约束
CONSTRAINTS = {
    'zones': {
        'low':   {'min': 0, 'max': 4, 'mean': 1.67, 'label': '个位(1-9)'},
        'mid':   {'min': 0, 'max': 4, 'mean': 1.83, 'label': '中段(10-19)'},
        'high':  {'min': 0, 'max': 4, 'mean': 1.79, 'label': '大数(20-29)'},
        'top':   {'min': 0, 'max': 3, 'mean': 0.71, 'label': '三十段(30-33)'},
    },
    'odd_even': {'min_odd': 1, 'max_odd': 5},
    'sum_range': {'min': 60, 'max': 150, 'mean': 101},
    'max_consecutive': 3,
}


def classify_zones(numbers):
    """将6个号码按区段分类"""
    return {
        'low':   [n for n in numbers if 1 <= n <= 9],
        'mid':   [n for n in numbers if 10 <= n <= 19],
        'high':  [n for n in numbers if 20 <= n <= 29],
        'top':   [n for n in numbers if 30 <= n <= 33],
    }


def check_consecutive(numbers):
    """检查最大连号长度"""
    sorted_nums = sorted(numbers)
    max_run = 1
    cur_run = 1
    for i in range(1, len(sorted_nums)):
        if sorted_nums[i] == sorted_nums[i-1] + 1:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 1
    return max_run


def validate_prediction(numbers):
    """
    检查一组6个号码是否满足所有约束
    返回 (valid, violations_list)
    """
    violations = []

    if len(numbers) != 6:
        return False, ['号码数量不是6个']

    # 去重
    if len(set(numbers)) != 6:
        return False, ['存在重复号码']

    sorted_nums = sorted(numbers)

    # 范围检查
    if sorted_nums[0] < 1 or sorted_nums[-1] > 33:
        return False, ['号码超出1-33范围']

    zones = classify_zones(sorted_nums)

    # 1. 区段约束
    if len(zones['low']) > 4:
        violations.append(f'个位区过多({len(zones["low"])}个, 最多4个)')
    if len(zones['top']) > 3:
        violations.append(f'三十段过多({len(zones["top"])}个, 最多3个)')

    # 2. 奇偶约束
    odd_count = sum(1 for n in sorted_nums if n % 2 == 1)
    if odd_count < 1 or odd_count > 5:
        violations.append(f'奇偶比失衡({odd_count}奇{6-odd_count}偶)')

    # 3. 和值约束
    total = sum(sorted_nums)
    if total < 60 or total > 150:
        violations.append(f'和值异常({total}, 正常范围60-150)')

    # 4. 连号约束
    max_run = check_consecutive(sorted_nums)
    if max_run >= 4:
        violations.append(f'连号过长({max_run}连, 极少出现)')

    # 5. 拥挤约束: 不允许3个以上号码挤在跨度<=4的范围内
    for i in range(len(sorted_nums) - 2):
        span = sorted_nums[i+2] - sorted_nums[i]
        if span <= 4:
            violations.append(f'号码过于拥挤({sorted_nums[i]}-{sorted_nums[i+2]}, 跨度仅{span})')
            break

    return len(violations) == 0, violations


def quick_validate(numbers):
    """快速验证（用于大量候选时）"""
    if len(numbers) != 6:
        return False
    sorted_nums = sorted(set(numbers))
    if len(sorted_nums) != 6:
        return False
    if sorted_nums[0] < 1 or sorted_nums[-1] > 33:
        return False

    # 和值
    s = sum(sorted_nums)
    if s < 60 or s > 150:
        return False

    # 奇偶
    odd = sum(1 for n in sorted_nums if n % 2 == 1)
    if odd < 1 or odd > 5:
        return False

    # 不能全部是个位数或全部是大数
    low = sum(1 for n in sorted_nums if n <= 9)
    high = sum(1 for n in sorted_nums if n >= 25)
    if low >= 4 or high >= 4:
        return False

    # 最大连号不超过3
    max_run = check_consecutive(sorted_nums)
    if max_run >= 4:
        return False

    return True


def enforce_constraints(predicted, candidate_pool, draws=None):
    """
    从候选池中构建合规的6个号码

    策略: 贪心选择 — 按综合得分从高到低选，但每选一个都检查约束可行性
    """
    # 如果原始结果已经合规，直接返回
    valid, _ = validate_prediction(predicted)
    if valid:
        return sorted(set(predicted))[:6]

    # 计算每个号码的综合得分（11原语平均）
    if draws is not None and candidate_pool is None:
        # 如果没有提供候选池，用原语重新打分
        from formula_lang.primitive import (
            ScaleTransition, PeriodicGap, SumRangeTracker,
            BayesianBiasEstimator, HierarchicalBayesianEstimator, EmpiricalBayesShrinkage,
            GapPatternAnalyzer, DigitPairFrequency, LagCorrelation,
            HarmonicPhaseLock, LatticeConvexHull,
        )
        elite_prims = [
            ScaleTransition(), PeriodicGap(), SumRangeTracker(),
            BayesianBiasEstimator(), HierarchicalBayesianEstimator(), EmpiricalBayesShrinkage(),
            GapPatternAnalyzer(), DigitPairFrequency(), LagCorrelation(),
            HarmonicPhaseLock(), LatticeConvexHull(),
        ]
        total_scores = {n: 0.0 for n in range(1, 34)}
        for prim in elite_prims:
            scores = prim.score_all(draws)
            for n in range(1, 34):
                total_scores[n] += scores.get(n, 0)
        candidate_pool = total_scores

    # 按得分排序
    sorted_candidates = sorted(candidate_pool.items(), key=lambda x: -x[1])

    # 贪心构建: 每次选一个号码，确保后续还能凑够6个且合规
    selected = []
    used = set()

    for num, score in sorted_candidates:
        if len(selected) == 6:
            break
        if num in used:
            continue

        test = sorted(selected + [num])
        remaining = 6 - len(test)

        # 提前剪枝检查
        zones = classify_zones(test)

        # 区段上限: 不能再选了
        if len(zones['low']) > 4 or len(zones['top']) > 3:
            continue

        # 剩余名额不够填补最低要求
        # 个位最少0个，但如果已经选了4个就不能再选个位了
        if len(zones['low']) >= 4 and num <= 9:
            continue
        if len(zones['top']) >= 3 and num >= 30:
            continue

        # 奇偶可行性: 最多5奇或5偶
        odd_in_test = sum(1 for n in test if n % 2 == 1)
        even_in_test = len(test) - odd_in_test
        if odd_in_test > 5 or even_in_test > 5:
            continue

        # 和值可行性
        current_sum = sum(test)
        min_possible = current_sum + remaining * 1   # 全选1
        max_possible = current_sum + remaining * 33  # 全选33
        if min_possible > 150 or max_possible < 60:
            continue

        # 连号可行性: 不能已有>=4连号
        max_run = check_consecutive(test)
        if max_run >= 4:
            continue

        # 拥挤检查: 不能有3个号码跨度<=4
        for i in range(len(test) - 2):
            if test[i+2] - test[i] <= 4:
                break
        else:
            # 通过所有检查，加入
            selected.append(num)
            used.add(num)
            continue

        # 如果拥挤检查失败，跳过这个号码
        continue

    # 如果没凑够6个，放宽约束补齐
    while len(selected) < 6:
        for num, score in sorted_candidates:
            if len(selected) == 6:
                break
            if num not in used:
                selected.append(num)
                used.add(num)

    final = sorted(selected)[:6]
    return final
