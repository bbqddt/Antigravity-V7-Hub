# -*- coding: utf-8 -*-
"""
Antigravity 非随机性检测引擎 V1.0 (精简快速版)
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import sys
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter
import warnings
import math
from datetime import datetime
warnings.filterwarnings('ignore')

_PROJECT_ROOT = Path(__file__).resolve().parent


def load_data():
    for c in [_PROJECT_ROOT / "data" / "lottery_history.csv",
              _PROJECT_ROOT / "data" / "ssq_history.csv",
              _PROJECT_ROOT / "ssq_history_full.csv"]:
        if c.exists():
            return pd.read_csv(str(c))
    raise FileNotFoundError("未找到历史数据")


def parse_positions(df):
    """按位置提取红球序列"""
    reds_by_pos = [[] for _ in range(6)]
    blues = []
    for _, row in df.iterrows():
        if 'red' in row:
            nums = [int(x.strip()) for x in str(row['red']).split(',')]
        else:
            nums = [int(row[f'r{i}']) for i in range(1, 7)]
        for i in range(6):
            reds_by_pos[i].append(nums[i])
        if 'blue' in row:
            blues.append(int(row['blue']))
        elif 'b' in row:
            blues.append(int(row['b']))
    return reds_by_pos, blues


# ─── Hurst 指数 ───
def hurst_exponent(series, max_lag=80):
    s = np.asarray(series, dtype=float)
    n = len(s)
    if n < 20:
        return 0.5
    returns = np.diff(s) / (np.abs(s[:-1]) + 1e-10) + 1.0
    returns = np.diff(s)  # 直接用差分

    lags = range(2, min(max_lag, n // 4))
    tau = []
    for lag in lags:
        splits = [returns[i:i + lag] for i in range(0, n - lag + 1, lag)]
        rs = []
        for seg in splits:
            if len(seg) == 0:
                continue
            m = np.mean(seg)
            std = np.std(seg)
            if std < 1e-12:
                continue
            r = np.max(np.cumsum(seg - m)) - np.min(np.cumsum(seg - m))
            rs.append(r / std)
        if rs:
            tau.append(np.log(np.mean(rs)))
    lags_log = np.log(list(lags))
    if len(tau) < 3:
        return 0.5
    coeffs = np.polyfit(lags_log, tau, 1)
    return coeffs[0]


# ─── 游程检验 ───
def runs_test(series):
    s = np.asarray(series, dtype=float)
    median = np.median(s)
    binary = [1 if x > median else 0 for x in s]
    runs = 1
    for i in range(1, len(binary)):
        if binary[i] != binary[i - 1]:
            runs += 1
    n = len(binary)
    n1 = sum(binary)
    n2 = n - n1
    expected = 1 + 2 * n1 * n2 / n if n > 0 else 0
    var = 2 * n1 * n2 * (2 * n1 * n2 - n) / (n * n * (n - 1)) if n > 1 else 1
    z = (runs - expected) / np.sqrt(var) if var > 0 else 0
    return runs, expected, z, abs(z) < 1.96


# ─── 频谱分析 ───
def spectral_peaks(series, n_fft=512):
    s = np.asarray(series, dtype=float)
    n = len(s)
    if n < 4:
        return []
    # 去均值
    s_detrended = s - np.mean(s)
    fft_vals = np.fft.rfft(s_detrended[:n_fft])
    power = np.abs(fft_vals) ** 2
    threshold = np.mean(power) + 3 * np.std(power)
    peaks = []
    for i in range(2, len(power) // 2):
        if power[i] > threshold and power[i] > power[i-1] and power[i] > power[i+1]:
            peaks.append((i, power[i]))
    peaks.sort(key=lambda x: -x[1])
    return peaks[:5]


# ─── 互信息 (快速版) ───
def mutual_information_fast(x, y, bins=6):
    xb = np.digitize(x, np.linspace(x.min()-1e-10, x.max()+1e-10, bins+1)) - 1
    yb = np.digitize(y, np.linspace(y.min()-1e-10, y.max()+1e-10, bins+1)) - 1
    xb = np.clip(xb, 0, bins-1)
    yb = np.clip(yb, 0, bins-1)
    joint = np.zeros((bins, bins))
    np.add.at(joint, (xb, yb), 1)
    joint /= joint.sum()
    px = joint.sum(axis=1)
    py = joint.sum(axis=0)
    mi = 0.0
    for i in range(bins):
        for j in range(bins):
            if joint[i,j] > 0 and px[i] > 0 and py[j] > 0:
                mi += joint[i,j] * np.log2(joint[i,j] / (px[i]*py[j]))
    return mi


# ─── 排列熵 ───
def permutation_entropy(series, order=3):
    s = np.asarray(series, dtype=float)
    n = len(s)
    if n <= order:
        return 0
    patterns = Counter()
    for i in range(n - order):
        perm = tuple(np.argsort(s[i:i+order]))
        patterns[perm] += 1
    total = sum(patterns.values())
    probs = [c/total for c in patterns.values()]
    ent = -sum(p*np.log2(p) for p in probs if p > 0)
    max_ent = math.log2(math.factorial(order)) if order <= 7 else 1
    return ent / max_ent if max_ent > 0 else 0


# ─── LZ 复杂度 ───
def lempel_ziv_complexity_binary(bits):
    n = len(bits)
    if n == 0:
        return 0.5
    i, k = 0, 1
    complexity = 1
    while k <= n:
        sub_len = (k - i) // 2
        if sub_len == 0:
            complexity += 1
            i = k
            k = i + 1
            continue
        if i + sub_len < n and bits[i:i+sub_len+1] == bits[k:k+sub_len+1]:
            k += 1
        else:
            complexity += 1
            i = k - i
            k = i + 1
            if k > n:
                break
    return min(complexity / n * np.log2(n), 1.0) if n > 0 else 0.5


# ─── 主检测 ───
def run_detection():
    print("=" * 70)
    print("  🔬 Antigravity 非随机性检测引擎 V1.0 (快速版)")
    print("  假设: 如果时间不存在, 双色球应有隐藏结构")
    print("=" * 70)
    print()

    df = load_data()
    reds_by_pos, blues = parse_positions(df)
    n = len(df)
    print(f"📊 数据规模: {n} 期")
    print()

    all_signals = []

    # 1. Hurst
    print("━━━ 1. Hurst 指数 (长期记忆) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        h = hurst_exponent(s)
        dev = abs(h - 0.5)
        status = "⚠️ 偏离" if dev > 0.1 else "  随机"
        interp = "持久" if h > 0.55 else ("反持久" if h < 0.45 else "随机")
        print(f"  {status} 红球{pos+1}位: H={h:.4f} ({interp}, 偏离={dev:.4f})")
        all_signals.append(("hurst", pos+1, h, dev))

    s_blue = np.array(blues, dtype=float)
    h_blue = hurst_exponent(s_blue)
    dev_blue = abs(h_blue - 0.5)
    print(f"  {'⚠️ 偏离' if dev_blue > 0.1 else '  随机'} 蓝球: H={h_blue:.4f}")
    all_signals.append(("hurst", "blue", h_blue, dev_blue))

    # 2. 游程检验
    print("\n━━━ 2. 游程检验 ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        runs, exp, z, passed = runs_test(s)
        status = "✅ 通过" if passed else "⚠️ 偏离"
        print(f"  {status} 红球{pos+1}位: runs={runs}, z={z:.3f}")
        all_signals.append(("runs", pos+1, z, abs(z)))

    runs_b, exp_b, z_b, passed_b = runs_test(s_blue)
    status_b = "✅ 通过" if passed_b else "⚠️ 偏离"
    print(f"  {status_b} 蓝球: runs={runs_b}, z={z_b:.3f}")
    all_signals.append(("runs", "blue", z_b, abs(z_b)))

    # 3. 频谱分析
    print("\n━━━ 3. 频谱分析 (隐藏周期) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        peaks = spectral_peaks(s)
        if peaks:
            print(f"  ⚠️ 红球{pos+1}位: {len(peaks)}个峰值")
            for freq, power in peaks[:2]:
                print(f"     周期≈{freq:.0f}期, 功率={power:.0f}")
            all_signals.append(("spectral", pos+1, peaks[0][0], peaks[0][1]))
        else:
            print(f"  ✅ 红球{pos+1}位: 无显著周期")

    peaks_b = spectral_peaks(s_blue)
    if peaks_b:
        print(f"  ⚠️ 蓝球: {len(peaks_b)}个峰值")
    else:
        print(f"  ✅ 蓝球: 无显著周期")

    # 4. 互信息 (只检查滞后1-3)
    print("\n━━━ 4. 互信息 (非线性依赖) ━━━")
    for lag in [1, 2, 3]:
        mi_vals = []
        for pos in range(6):
            s = np.array(reds_by_pos[pos], dtype=float)
            s_shifted = np.roll(s, lag)
            mi = mutual_information_fast(s[:-lag], s_shifted[:-lag])
            mi_vals.append(mi)
        avg_mi = np.mean(mi_vals)
        status = "⚠️" if avg_mi > 0.15 else "  "
        print(f"  {status} 滞后{lag}: MI={avg_mi:.4f}")
        all_signals.append(("mi", lag, avg_mi, avg_mi))

    # 5. 排列熵
    print("\n━━━ 5. 排列熵 (时序复杂度) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        pe = permutation_entropy(s, order=3)
        dev = abs(pe - 1.0)
        status = "⚠️" if dev > 0.15 else "  "
        print(f"  {status} 红球{pos+1}位: PE={pe:.4f} (随机=1.0, 偏离={dev:.4f})")
        all_signals.append(("pe", pos+1, pe, dev))

    pe_b = permutation_entropy(s_blue, order=3)
    dev_b = abs(pe_b - 1.0)
    status_b = "⚠️" if dev_b > 0.15 else "  "
    print(f"  {status_b} 蓝球: PE={pe_b:.4f}")
    all_signals.append(("pe", "blue", pe_b, dev_b))

    # 6. LZ 复杂度
    print("\n━━━ 6. Lempel-Ziv 复杂度 ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        bits = []
        for x in s:
            val = int(x)
            for i in range(6):
                bits.append((val >> i) & 1)
        lz = lempel_ziv_complexity_binary(bits)
        dev = abs(lz - 1.0)
        status = "⚠️" if dev > 0.15 else "  "
        print(f"  {status} 红球{pos+1}位: LZ={lz:.4f} (随机≈1.0, 偏离={dev:.4f})")
        all_signals.append(("lz", pos+1, lz, dev))

    bits_b = []
    for x in s_blue:
        val = int(x)
        for i in range(5):
            bits_b.append((val >> i) & 1)
    lz_b = lempel_ziv_complexity_binary(bits_b)
    dev_b = abs(lz_b - 1.0)
    status_b = "⚠️" if dev_b > 0.15 else "  "
    print(f"  {status_b} 蓝球: LZ={lz_b:.4f}")
    all_signals.append(("lz", "blue", lz_b, dev_b))

    # ─── V2.3 新增检验: 7-20 ───

    # 7. 偏度 (Skewness) — 检测分布不对称性
    print("\n━━━ 7. 偏度检验 (分布不对称性) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        skew = float(pd.Series(s).skew())
        dev = abs(skew)
        status = "⚠️" if dev > 0.5 else "  "
        print(f"  {status} 红球{pos+1}位: 偏度={skew:.4f} (随机≈0)")
        all_signals.append(("skewness", pos+1, skew, dev))

    skew_b = float(pd.Series(blues).skew())
    dev_b = abs(skew_b)
    status_b = "⚠️" if dev_b > 0.5 else "  "
    print(f"  {status_b} 蓝球: 偏度={skew_b:.4f}")
    all_signals.append(("skewness", "blue", skew_b, dev_b))

    # 8. 峰度 (Kurtosis) — 检测尾部厚度
    print("\n━━━ 8. 峰度检验 (尾部厚度) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        kurt = float(pd.Series(s).kurtosis())
        dev = abs(kurt)
        status = "⚠️" if dev > 1.0 else "  "
        print(f"  {status} 红球{pos+1}位: 峰度={kurt:.4f} (随机≈0)")
        all_signals.append(("kurtosis", pos+1, kurt, dev))

    kurt_b = float(pd.Series(blues).kurtosis())
    dev_b = abs(kurt_b)
    status_b = "⚠️" if dev_b > 1.0 else "  "
    print(f"  {status_b} 蓝球: 峰度={kurt_b:.4f}")
    all_signals.append(("kurtosis", "blue", kurt_b, dev_b))

    # 9. 自相关函数 ACF (lag 1-5)
    print("\n━━━ 9. 自相关函数 ACF ━━━")
    for lag in range(1, 6):
        acf_vals = []
        for pos in range(6):
            s = np.array(reds_by_pos[pos], dtype=float)
            n = len(s)
            if n > lag:
                mean = np.mean(s)
                var = np.var(s)
                if var > 1e-10:
                    acf = np.mean((s[:-lag] - mean) * (s[lag:] - mean)) / var
                    acf_vals.append(acf)
        avg_acf = np.mean(acf_vals) if acf_vals else 0
        dev = abs(avg_acf)
        status = "⚠️" if dev > 0.05 else "  "
        print(f"  {status} ACF(lag={lag}): {avg_acf:.6f}")
        all_signals.append(("acf", lag, avg_acf, dev))

    # 10. 偏度-峰度联合检验 (JB 统计量)
    print("\n━━━ 10. Jarque-Bera 统计量 (正态性检验) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        skew = float(pd.Series(s).skew())
        kurt = float(pd.Series(s).kurtosis())
        n = len(s)
        jb = n / 6 * (skew**2 + kurt**2 / 4)
        dev = jb / (n * 0.1)  # 归一化
        status = "⚠️" if jb > 6.0 else "  "
        print(f"  {status} 红球{pos+1}位: JB={jb:.2f} (随机<6)")
        all_signals.append(("jb", pos+1, jb, dev))

    jb_b = n / 6 * (skew_b**2 + kurt_b**2 / 4)
    dev_b = jb_b / (n * 0.1)
    status_b = "⚠️" if jb_b > 6.0 else "  "
    print(f"  {status_b} 蓝球: JB={jb_b:.2f}")
    all_signals.append(("jb", "blue", jb_b, dev_b))

    # 11. 条件熵 (Conditional Entropy) — 给定前一期的信息量
    print("\n━━━ 11. 条件熵 H(Xt|Xt-1) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        if len(s) < 10:
            continue
        # 离散化为 3 个区间
        bins = np.percentile(s, [33, 66])
        disc = np.digitize(s, bins)
        # 联合熵 H(Xt, Xt-1)
        joint = Counter()
        for i in range(1, len(disc)):
            joint[(disc[i], disc[i-1])] += 1
        total = sum(joint.values())
        h_joint = -sum((c/total)*math.log2(c/total) for c in joint.values() if c > 0)
        # 边际熵 H(Xt-1)
        marg = Counter(disc[:-1])
        h_prev = -sum((c/total)*math.log2(c/total) for c in marg.values() if c > 0)
        cond_ent = h_joint - h_prev  # H(Xt|Xt-1) = H(Xt,Xt-1) - H(Xt-1)
        # 如果条件熵 < 边际熵，说明 Xt-1 对 Xt 有信息量
        max_cond = math.log2(3)  # 最大条件熵
        dev = max(0, (max_cond - cond_ent) / max_cond) if max_cond > 0 else 0
        status = "⚠️" if dev > 0.1 else "  "
        print(f"  {status} 红球{pos+1}位: H(Xt|Xt-1)={cond_ent:.4f}, 偏离={dev:.4f}")
        all_signals.append(("cond_entropy", pos+1, cond_ent, dev))

    # 12. 转移熵 (Transfer Entropy) — 信息流向
    print("\n━━━ 12. 转移熵 (信息流向) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        if len(s) < 10:
            continue
        bins = np.percentile(s, [33, 66])
        disc = np.digitize(s, bins)
        # P(Xt | Xt-1, Xt-2) vs P(Xt | Xt-1)
        tri = Counter()
        bi = Counter()
        for i in range(2, len(disc)):
            tri[(disc[i], disc[i-1], disc[i-2])] += 1
            bi[(disc[i], disc[i-1])] += 1
        total = sum(tri.values())
        # 条件互信息 = H(Xt-1|Xt-2) - H(Xt-1|Xt-2,Xt-3)
        te = 0.0
        for x2, x1, x0 in tri:
            p_x0_x1_x2 = tri[(x0, x1, x2)] / total
            p_x0_x1 = bi[(x0, x1)] / total
            p_x0 = sum(bi[(x0, _)] for _ in range(3)) / total
            p_x1 = sum(bi[(_, x1)] for _ in range(3)) / total
            if p_x0_x1_x2 > 0 and p_x0_x1 > 0 and p_x0 > 0 and p_x1 > 0:
                te += p_x0_x1_x2 * math.log2(p_x0_x1_x2 * p_x1 / (p_x0_x1 * p_x0))
        dev = max(0, te)
        status = "⚠️" if dev > 0.01 else "  "
        print(f"  {status} 红球{pos+1}位: TE={te:.6f}")
        all_signals.append(("transfer_entropy", pos+1, te, dev))

    # 13. 自协方差函数 ACF 积分 — 整体序列依赖性
    print("\n━━━ 13. 自协方差积分 (整体依赖性) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        n = len(s)
        mean = np.mean(s)
        var = np.var(s)
        if var < 1e-10:
            continue
        acf_sum = 0
        for lag in range(1, min(20, n // 2)):
            acf = np.mean((s[:-lag] - mean) * (s[lag:] - mean)) / var
            acf_sum += abs(acf)
        dev = acf_sum / 20  # 平均绝对自协方差
        status = "⚠️" if dev > 0.02 else "  "
        print(f"  {status} 红球{pos+1}位: Σ|ACF|={acf_sum:.4f}, 均值={dev:.6f}")
        all_signals.append(("acf_integral", pos+1, acf_sum, dev))

    # 14. 差分序列的 Hurst — 检测一阶差分是否有记忆
    print("\n━━━ 14. 差分 Hurst (一阶差分记忆性) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        diff = np.diff(s)
        h = hurst_exponent(diff)
        dev = abs(h - 0.5)
        status = "⚠️" if dev > 0.1 else "  "
        print(f"  {status} 红球{pos+1}位: ΔHurst={h:.4f} (随机≈0.5)")
        all_signals.append(("hurst_diff", pos+1, h, dev))

    # 15. 跨位置互信息 — 位置之间的相互依赖
    print("\n━━━ 15. 跨位置互信息 (位置间依赖) ━━━")
    for pos_a in range(5):
        for pos_b in range(pos_a + 1, 6):
            s_a = np.array(reds_by_pos[pos_a], dtype=float)
            s_b = np.array(reds_by_pos[pos_b], dtype=float)
            n = min(len(s_a), len(s_b))
            if n < 20:
                continue
            # 离散化
            bins_a = np.percentile(s_a[:n], [25, 50, 75])
            bins_b = np.percentile(s_b[:n], [25, 50, 75])
            disc_a = np.digitize(s_a[:n], bins_a)
            disc_b = np.digitize(s_b[:n], bins_b)
            joint = Counter()
            for i in range(n):
                joint[(disc_a[i], disc_b[i])] += 1
            total = n
            mi = 0.0
            for (a, b), c in joint.items():
                p_ab = c / total
                p_a = sum(v for ka, v in joint.items() if ka[0] == a) / total
                p_b = sum(v for ka, v in joint.items() if ka[1] == b) / total
                if p_ab > 0 and p_a > 0 and p_b > 0:
                    mi += p_ab * math.log2(p_ab / (p_a * p_b))
            dev = max(0, mi)
            status = "⚠️" if dev > 0.01 else "  "
            print(f"  {status} 位置{pos_a+1}↔{pos_b+1}: MI={mi:.6f}")
            all_signals.append(("cross_mi", f"{pos_a+1}-{pos_b+1}", mi, dev))

    # 16. 滚动均值稳定性 — 检测均值是否在漂移
    print("\n━━━ 16. 滚动均值稳定性 (均值漂移检验) ━━━")
    window = 50
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        if len(s) < window * 3:
            continue
        rolling_means = [np.mean(s[i:i+window]) for i in range(0, len(s)-window, window)]
        overall_mean = np.mean(s)
        drift = np.std(rolling_means)
        dev = drift / max(abs(overall_mean), 1)
        status = "⚠️" if dev > 0.05 else "  "
        print(f"  {status} 红球{pos+1}位: 滚动均值漂移={drift:.4f}, 相对={dev:.6f}")
        all_signals.append(("rolling_drift", pos+1, drift, dev))

    # 17. 间隔分布检验 (Inter-arrival) — 号码出现间隔的分布
    print("\n━━━ 17. 间隔分布 (号码出现间隔) ━━━")
    for num in [1, 8, 16, 24, 33]:  # 选几个代表性号码
        intervals = []
        last_appear = -1
        for i, row in df.iterrows():
            if 'red' in row:
                nums = [int(x.strip()) for x in str(row['red']).split(',')]
            else:
                nums = [int(row[f'r{j}']) for j in range(1, 7)]
            if num in nums:
                if last_appear >= 0:
                    intervals.append(i - last_appear)
                last_appear = i
        if len(intervals) < 5:
            continue
        # 指数分布的 KS 检验 (如果随机，间隔应近似指数分布)
        exp_mean = np.mean(intervals)
        ks_stat = 0
        for x in intervals:
            exp_cdf = 1 - math.exp(-x / max(exp_mean, 1))
            uni_cdf = sum(1 for iv in intervals if iv <= x) / len(intervals)
            ks_stat = max(ks_stat, abs(exp_cdf - uni_cdf))
        dev = ks_stat
        status = "⚠️" if dev > 0.1 else "  "
        print(f"  {status} 号码{num:02d}: 间隔均值={exp_mean:.1f}, KS={ks_stat:.4f}")
        all_signals.append(("interval_ks", num, ks_stat, dev))

    # 18. 奇偶比序列的游程检验
    print("\n━━━ 18. 奇偶比序列 (Odd-Even Ratio) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        odd_even = [int(x) % 2 for x in s]
        runs, exp, z, passed = runs_test(odd_even)
        dev = abs(z)
        status = "⚠️" if dev > 1.96 else "  "
        print(f"  {status} 红球{pos+1}位: 奇偶游程 z={z:.3f}")
        all_signals.append(("oe_runs", pos+1, z, dev))

    # 19. 和值序列的非随机性
    print("\n━━━ 19. 和值序列分析 (Sum Sequence) ━━━")
    sums = []
    for _, row in df.iterrows():
        if 'red' in row:
            nums = [int(x.strip()) for x in str(row['red']).split(',')]
        else:
            nums = [int(row[f'r{j}']) for j in range(1, 7)]
        sums.append(sum(nums))
    s_sum = np.array(sums, dtype=float)
    h_sum = hurst_exponent(s_sum)
    dev_sum = abs(h_sum - 0.5)
    status_sum = "⚠️" if dev_sum > 0.1 else "  "
    print(f"  {status_sum} 和值序列: H={h_sum:.4f} (随机≈0.5)")
    all_signals.append(("sum_hurst", "all", h_sum, dev_sum))

    # 和值的自相关
    acf_sum = 0
    n_s = len(s_sum)
    if n_s > 10:
        mean_s = np.mean(s_sum)
        var_s = np.var(s_sum)
        if var_s > 1e-10:
            acf_sum = np.mean((s_sum[:-1] - mean_s) * (s_sum[1:] - mean_s)) / var_s
    dev_acf_sum = abs(acf_sum)
    status_acf_sum = "⚠️" if dev_acf_sum > 0.05 else "  "
    print(f"  {status_acf_sum} 和值 ACF(1): {acf_sum:.6f}")
    all_signals.append(("sum_acf", "all", acf_sum, dev_acf_sum))

    # 20. 蓝球-红球联合分布
    print("\n━━━ 20. 蓝球-红球联合分布 (Cross-distribution) ━━━")
    for blue_val in [1, 8, 16]:
        reds_when_blue = []
        for _, row in df.iterrows():
            if int(row['blue']) == blue_val:
                if 'red' in row:
                    nums = [int(x.strip()) for x in str(row['red']).split(',')]
                else:
                    nums = [int(row[f'r{j}']) for j in range(1, 7)]
                reds_when_blue.extend(nums)
        if len(reds_when_blue) < 10:
            continue
        freq = Counter(reds_when_blue)
        # 与全局频率的差异
        global_freq = Counter()
        for _, row in df.iterrows():
            if 'red' in row:
                nums = [int(x.strip()) for x in str(row['red']).split(',')]
            else:
                nums = [int(row[f'r{j}']) for j in range(1, 7)]
            global_freq.update(nums)
        chi_sq = 0
        for num in range(1, 34):
            observed = freq.get(num, 0)
            expected = len(reds_when_blue) * global_freq.get(num, 0) / sum(global_freq.values())
            if expected > 0:
                chi_sq += (observed - expected)**2 / expected
        dev_chi = chi_sq / 33
        status_chi = "⚠️" if dev_chi > 0.5 else "  "
        print(f"  {status_chi} 蓝球={blue_val:02d}: χ²/33={dev_chi:.4f}")
        all_signals.append(("chi_square", blue_val, dev_chi, dev_chi))

    # 21. 号码对的自相关 (Pair Autocorrelation)
    print("\n━━━ 21. 号码对自相关 (Pair Autocorrelation) ━━━")
    pairs = [(1, 2), (16, 17), (32, 33), (1, 33)]  # 测试几种配对
    for a, b in pairs:
        corr_vals = []
        for lag in [1, 2, 3]:
            for pos in range(6):
                s = np.array(reds_by_pos[pos], dtype=float)
                if len(s) > lag:
                    n = len(s)
                    mean = np.mean(s)
                    var = np.var(s)
                    if var > 1e-10:
                        acf = np.mean((s[:-lag] - mean) * (s[lag:] - mean)) / var
                        corr_vals.append(acf)
        avg_corr = np.mean(corr_vals) if corr_vals else 0
        dev = abs(avg_corr)
        status = "⚠️" if dev > 0.05 else "  "
        print(f"  {status} 号码对({a:02d},{b:02d}): 平均ACF={avg_corr:.6f}")
        all_signals.append(("pair_acf", f"{a}-{b}", avg_corr, dev))

    # 22. 时间反演对称性检验 (Time Reversal Symmetry)
    print("\n━━━ 22. 时间反演对称性 (Time Reversal Symmetry) ━━━")
    for pos in range(6):
        s = np.array(reds_by_pos[pos], dtype=float)
        if len(s) < 20:
            continue
        # 正向差分分布 vs 反向差分分布
        fwd_diff = np.diff(s)
        rev_diff = np.diff(s[::-1])
        # KS 检验两个分布是否相同
        ks_stat = 0
        n_fwd = len(fwd_diff)
        n_rev = len(rev_diff)
        for x in np.concatenate([fwd_diff, rev_diff]):
            fwd_cdf = sum(1 for d in fwd_diff if d <= x) / n_fwd
            rev_cdf = sum(1 for d in rev_diff if d <= x) / n_rev
            ks_stat = max(ks_stat, abs(fwd_cdf - rev_cdf))
        dev = ks_stat
        status = "⚠️" if dev > 0.1 else "  "
        print(f"  {status} 红球{pos+1}位: KS(正向vs反向)={ks_stat:.4f}")
        all_signals.append(("time_reversal", pos+1, ks_stat, dev))

    # ─── 综合 ───
    print("\n" + "=" * 70)
    print("  📋 综合分析")
    print("=" * 70)

    deviations = [(t, name, val, dev) for t, name, val, dev in all_signals if dev > 0.1]

    if deviations:
        print(f"\n⚠️ 检测到 {len(deviations)} 个偏离随机模型的信号:")
        for t, name, val, dev in deviations:
            print(f"   - {t}({name}): 偏离={dev:.4f}")

        print(f"\n🔍 解读:")
        print(f"   这些偏离可能意味着:")
        print(f"   ① 摇奖过程存在确定性混沌结构")
        print(f"   ② 数据中存在非随机的隐藏模式")
        print(f"   ③ 也可能是统计涨落 (3469 期数据量不小)")

        # 进一步分析：这些偏离是一致的还是偶然的？
        types = set(d[0] for d in deviations)
        if len(types) >= 3:
            print(f"\n   ✅ 多个独立检测方法都检测到偏离 → 可能是真实信号")
        else:
            print(f"\n   ⚠️ 偏离集中在少数方法 → 可能是假阳性")
    else:
        print("\n✅ 所有检测均通过随机性检验")
        print("   在当前精度下，数据表现为纯随机序列")

    # 保存结果
    import json
    summary = {
        "total_periods": n,
        "signals_found": len(deviations),
        "deviations": [{"type": t, "name": str(name), "value": round(val, 4), "deviation": round(dev, 4)} for t, name, val, dev in deviations],
        "timestamp": datetime.now().isoformat() if 'datetime' in dir() else "",
    }
    with open(str(_PROJECT_ROOT / "nonrandomness_results.json"), "w", encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n📄 结果已保存: nonrandomness_results.json")

    # 新增: 同时写入共享先验文件，供预测引擎读取
    prior = {
        "signals_found": len(deviations),
        "deviation_types": list(set(d[0] for d in deviations)),
        "has_structure": len(deviations) >= 3,  # 多个独立方法检测到→认为有结构
    }
    with open(str(_PROJECT_ROOT / "analysis_prior.json"), "w", encoding='utf-8') as f:
        json.dump(prior, f, ensure_ascii=False, indent=2)
    print(f"📄 共享先验已保存: analysis_prior.json")

    # V2.2 新增: 输出结构化位置先验 (position_prior.json)
    # 将 all_signals 重组为按位置组织的结构化数据
    position_deviations = {}
    for test_type, name, val, dev in all_signals:
        pos_key = str(name)
        if pos_key not in position_deviations:
            position_deviations[pos_key] = {}
        # 根据测试类型映射到字段名
        field_map = {
            "hurst": "hurst_dev",
            "runs": "runs_z",
            "spectral": "spectral_peaks",
            "mi": "mi_lag1",
            "pe": "pe_dev",
            "lz": "lz_dev",
            "skewness": "skew",
            "kurtosis": "kurt",
            "jb": "jb_stat",
            "cond_entropy": "cond_ent",
            "transfer_entropy": "te",
            "acf_integral": "acf_int",
            "hurst_diff": "hurst_delta",
            "cross_mi": "cross_mi",
            "rolling_drift": "roll_drift",
            "interval_ks": "interval_ks",
            "oe_runs": "oe_z",
            "sum_hurst": "sum_hurst",
            "sum_acf": "sum_acf",
            "chi_square": "chi2",
            "pair_acf": "pair_acf",
            "time_reversal": "ts_ks",
            "acf": "acf_val",
        }
        field_name = field_map.get(test_type, f"{test_type}_{val}")
        position_deviations[pos_key][field_name] = round(float(val), 4)

    # 找出最强信号
    strongest_signals = []
    for t, name, val, dev in sorted(all_signals, key=lambda x: -x[3]):
        if dev > 0.1:
            interpretation = "persistent" if t == "hurst" and val > 0.5 else \
                             "anti-persistent" if t == "hurst" and val < 0.5 else \
                             "significant_dependency" if t == "mi" else \
                             "structured" if t == "pe" and val < 0.85 else \
                             "algorithmic_pattern" if t == "lz" else "unknown"
            strongest_signals.append({
                "position": name,
                "test": t,
                "deviation": round(dev, 4),
                "interpretation": interpretation,
            })
        if len(strongest_signals) >= 10:
            break

    # 测试一致性
    test_agreement = {}
    for test_type in ["hurst", "runs", "pe", "lz"]:
        devs = [d for t, n, v, d in all_signals if t == test_type]
        test_agreement[f"{test_type}_consistent"] = len([d for d in devs if d > 0.1]) >= 2

    position_prior = {
        "position_deviations": position_deviations,
        "test_agreement": test_agreement,
        "strongest_signals": strongest_signals,
    }
    with open(str(_PROJECT_ROOT / "position_prior.json"), "w", encoding='utf-8') as f:
        json.dump(position_prior, f, ensure_ascii=False, indent=2)
    print(f"📄 结构化位置先验已保存: position_prior.json")


if __name__ == "__main__":
    run_detection()
