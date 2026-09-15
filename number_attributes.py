# -*- coding: utf-8 -*-
"""
Antigravity 号码多维属性分析 V1.0

对每个号码(1-33)计算数十个数学/物理属性，
构建一个高维特征空间，从中寻找与开奖结果相关的结构。

核心假设: 如果时间不存在，那么每个号码的属性不是"随机的"，
而是由其在场的结构位置决定的。这些结构位置可以通过
数学属性（二进制、数位、模类、质因数等）来探测。
"""
import numpy as np
import pandas as pd
import json
import math
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

_PROJECT_ROOT = Path(__file__).resolve().parent


# ─── 基础属性 ───

def digit_sum(n):
    """数位和"""
    return sum(int(d) for d in str(n))


def digit_product(n):
    """数位积"""
    p = 1
    for d in str(n):
        p *= int(d)
    return p


def is_prime(n):
    """是否为质数"""
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True


def binary_representation(n):
    """二进制表示"""
    return bin(n)[2:]


def binary_weight(n):
    """二进制权重（1的个数）"""
    return bin(n).count('1')


def golden_ratio_distance(n):
    """与黄金比例的"距离"—— n * phi mod 1"""
    phi = (1 + math.sqrt(5)) / 2
    return abs((n * phi) % 1 - 0.5)


def fibonacci_membership(n):
    """是否属于斐波那契数列"""
    fibs = {1, 2, 3, 5, 8, 13, 21, 34}
    return n in fibs


def perfect_square(n):
    """是否为完全平方数"""
    s = int(math.sqrt(n))
    return s * s == n


def perfect_number(n):
    """是否为完全数"""
    return n in {6, 28}


def triangular_number(n):
    """是否为三角形数"""
    k = int(math.sqrt(2 * n))
    return k * (k + 1) // 2 == n


def modulo_classes(n):
    """模类特征"""
    return {m: n % m for m in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 33]}


def prime_factors(n):
    """质因数分解"""
    factors = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


def fermat_remainder(n):
    """费马小定理余数——对每个质数p，计算 n^(p-1) mod p"""
    result = {}
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]:
        if p != n:
            result[p] = pow(n, p - 1, p)
    return result


def digital_root(n):
    """数字根（反复求和直到个位数）"""
    while n >= 10:
        n = sum(int(d) for d in str(n))
    return n


def chinese_zodiac(n):
    """生肖对应（1-12循环）"""
    return n % 12


def four_seasons(n):
    """四季对应"""
    if n <= 8:
        return "spring"
    elif n <= 16:
        return "summer"
    elif n <= 24:
        return "autumn"
    else:
        return "winter"


def yin_yang(n):
    """阴阳"""
    return "yang" if n % 2 == 1 else "yin"


def compass_direction(n):
    """八卦方位（12宫）"""
    return n % 12


# ─── 全局属性计算 ───

def compute_number_attributes():
    """为每个号码(1-33)计算所有属性"""
    attrs = {}
    for n in range(1, 34):
        attrs[n] = {
            "digit_sum": digit_sum(n),
            "digit_product": digit_product(n),
            "is_prime": is_prime(n),
            "binary": binary_representation(n),
            "binary_weight": binary_weight(n),
            "golden_distance": round(golden_ratio_distance(n), 4),
            "is_fibonacci": fibonacci_membership(n),
            "is_square": perfect_square(n),
            "is_perfect": perfect_number(n),
            "is_triangular": triangular_number(n),
            "digital_root": digital_root(n),
            "mod_classes": modulo_classes(n),
            "prime_factors": prime_factors(n),
            "fermat_remainders": fermat_remainder(n),
            "yinyang": yin_yang(n),
            "season": four_seasons(n),
            "zodiac": chinese_zodiac(n),
            "compass": compass_direction(n),
        }
    return attrs


# ─── 历史属性频率 ───

def compute_attribute_frequencies(draws, attrs):
    """
    对每个号码的属性，计算其在历史开奖中的表现。

    例如: 号码7（质数、二进制权重2、数位和7）
    在历史中出现时，这些属性是否比随机预期更常见？
    """
    # 按属性分组统计
    prop_stats = defaultdict(lambda: {"total": 0, "hit": 0})

    for draw in draws:
        reds = draw.reds if hasattr(draw, 'reds') else sorted(list(draw.red))
        for n in range(1, 34):
            a = attrs[n]
            # 二进制权重
            prop_stats[("binary_weight", a["binary_weight"])]["total"] += 1
            if n in reds:
                prop_stats[("binary_weight", a["binary_weight"])]["hit"] += 1

            # 质数
            prop_stats[("is_prime", a["is_prime"])]["total"] += 1
            if n in reds:
                prop_stats[("is_prime", a["is_prime"])]["hit"] += 1

            # 数位和范围
            ds = a["digit_sum"]
            bucket = ds // 5 * 5
            prop_stats[("digit_sum_bucket", bucket)]["total"] += 1
            if n in reds:
                prop_stats[("digit_sum_bucket", bucket)]["hit"] += 1

            # 阴阳
            prop_stats[("yinyang", a["yinyang"])]["total"] += 1
            if n in reds:
                prop_stats[("yinyang", a["yinyang"])]["hit"] += 1

            # 四季
            prop_stats[("season", a["season"])]["total"] += 1
            if n in reds:
                prop_stats[("season", a["season"])]["hit"] += 1

    # 计算每个属性的命中率 vs 预期命中率
    results = {}
    for (prop_name, prop_val), stats in prop_stats.items():
        if stats["total"] > 0:
            hit_rate = stats["hit"] / stats["total"]
            expected = 6 / 33  # 随机预期
            deviation = hit_rate - expected
            results[f"{prop_name}_{prop_val}"] = {
                "hit_rate": round(hit_rate, 4),
                "expected": round(expected, 4),
                "deviation": round(deviation, 4),
                "sample_size": stats["total"],
            }

    return results


# ─── 号码属性画像 ───

def generate_number_profiles(attrs):
    """为每个号码生成属性画像"""
    profiles = {}
    for n in range(1, 34):
        a = attrs[n]
        profile = {
            "number": n,
            "binary": a["binary"],
            "binary_weight": a["binary_weight"],
            "prime": a["is_prime"],
            "fibonacci": a["is_fibonacci"],
            "square": a["is_square"],
            "perfect": a["is_perfect"],
            "triangular": a["is_triangular"],
            "digit_sum": a["digit_sum"],
            "digital_root": a["digital_root"],
            "golden_distance": a["golden_distance"],
            "yinyang": a["yinyang"],
            "season": a["season"],
            "zodiac": a["zodiac"],
            "compass": a["compass"],
            "prime_factors": {str(k): v for k, v in a["prime_factors"].items()},
            "fermat": {str(k): v for k, v in a["fermat_remainders"].items()},
            "mod": {str(k): v for k, v in a["mod_classes"].items()},
        }
        profiles[str(n)] = profile
    return profiles


# ─── 主函数 ───

def run_analysis():
    print("=" * 70)
    print("  🔬 号码多维属性分析 V1.0")
    print("  假设: 如果时间不存在，号码的属性由其结构位置决定")
    print("=" * 70)
    print()

    # 1. 计算所有属性
    print("📐 计算号码属性...")
    attrs = compute_number_attributes()
    print(f"  已计算 33 个号码的属性")

    # 2. 生成画像
    profiles = generate_number_profiles(attrs)

    # 3. 输出样例
    print("\n📋 属性画像示例:")
    for n in [1, 7, 13, 21, 33]:
        p = profiles[str(n)]
        print(f"\n  号码 {n:02d}:")
        print(f"    二进制: {p['binary']} (权重: {p['binary_weight']})")
        print(f"    质数: {p['prime']}, 斐波那契: {p['fibonacci']}")
        print(f"    平方: {p['square']}, 完全数: {p['perfect']}, 三角数: {p['triangular']}")
        print(f"    数位和: {p['digit_sum']}, 数字根: {p['digital_root']}")
        print(f"    黄金距离: {p['golden_distance']:.4f}")
        print(f"    阴阳: {p['yinyang']}, 四季: {p['season']}")
        print(f"    质因数: {p['prime_factors']}")
        print(f"    模类: {p['mod']}")

    # 4. 保存属性画像
    output_path = _PROJECT_ROOT / "number_profiles.json"
    with open(str(output_path), "w", encoding='utf-8') as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
    print(f"\n📄 属性画像已保存: number_profiles.json")

    # 5. 加载历史数据计算属性频率
    print("\n📊 计算属性频率...")
    try:
        from data_layer import load_history
        draws = load_history()
        freq = compute_attribute_frequencies(draws, attrs)

        # 找出偏差最大的属性
        sorted_freq = sorted(freq.items(), key=lambda x: -abs(x[1]["deviation"]))

        print(f"\n  偏差最大的属性 (Top 10):")
        for name, stats in sorted_freq[:10]:
            direction = "+" if stats["deviation"] > 0 else ""
            print(f"    {name}: 命中率={stats['hit_rate']:.4f} 预期={stats['expected']:.4f} 偏差={direction}{stats['deviation']:.4f} (样本={stats['sample_size']})")

        # 保存属性频率
        freq_path = _PROJECT_ROOT / "attribute_frequencies.json"
        with open(str(freq_path), "w", encoding='utf-8') as f:
            json.dump(dict(sorted_freq), f, ensure_ascii=False, indent=2)
        print(f"\n📄 属性频率已保存: attribute_frequencies.json")

    except Exception as e:
        print(f"  [WARN] 属性频率计算失败: {e}")

    print("\n✅ 号码多维属性分析完成")


if __name__ == "__main__":
    run_analysis()
