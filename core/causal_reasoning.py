import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class CausalAnalyzer:
    """基于先验统计学与物理熵的极度深层因果推理验证器"""
    
    def __init__(self):
        # 极度量化的统计学因果假设字典
        self.rules = {
            "max_sequence": 2,               # 严防多连号，最多2连
            "even_odd_ratio_bounds": [2, 4], # 奇数占比合理区间为 2/6 到 4/6
            "sum_bounds": [90, 130],         # 6个红球的和值通常服从正态分布，截取在 90~130 之间
            "span_bounds": [20, 32],         # 首尾红球跨度 (max - min)
            "prime_count_bounds": [1, 3],    # 质数占比 (通常 1 到 3 个)
            "ac_value_min": 4,               # 复杂度(AC值)通常大于等于4
        }
        self.primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31}

    def _calculate_ac_value(self, reds: List[int]) -> int:
        """计算红球的 AC 值（复杂性指标，衡量随机分散度）"""
        diffs = set()
        for i in range(len(reds)):
            for j in range(i+1, len(reds)):
                diffs.add(abs(reds[i] - reds[j]))
        return len(diffs) - (len(reds) - 1)

    def evaluate_causality(self, reds_str: str, blue_str: str, entropy_temp: float = 0.0) -> dict:
        """
        验证给定组合是否符合极其严格的基础物理概率因果预期
        reds_str: e.g. "1, 10, 11, 12, 15, 33"  (可以是列表字符串表示形式)
        entropy_temp: 外部输入的物理环境温度扰动因子
        """
        try:
            # 清理字符串并解析号码
            reds_clean = reds_str.replace("[", "").replace("]", "")
            reds = [int(x.strip()) for x in reds_clean.split(',')]
            blue = int(blue_str.strip())
        except Exception:
            return {"status": "error", "message": "Failed to parse", "confidence_multiplier": 0.0}

        report_status = "passed"
        warnings_list = []
        violation_weight = 0.0

        # === 核心规则群校验 ===
        
        # 1. 连号检测因果分析
        seq_count = 1
        max_seq = 1
        for i in range(1, len(reds)):
            if reds[i] == reds[i-1] + 1:
                seq_count += 1
                max_seq = max(max_seq, seq_count)
            else:
                seq_count = 1
                
        max_allowed_seq = int(self.rules["max_sequence"]) # type: ignore
        if max_seq > max_allowed_seq:
            report_status = "failed"
            warnings_list.append(f"连号长度({max_seq})激增，产生长尾集聚因果违背。")
            violation_weight += 0.4

        # 2. 奇偶比检测分析
        odds = sum(1 for x in reds if x % 2 != 0)
        bounds_eo = self.rules["even_odd_ratio_bounds"]
        if isinstance(bounds_eo, list) and (odds < bounds_eo[0] or odds > bounds_eo[1]):
            report_status = "marginal" if report_status != "failed" else "failed"
            warnings_list.append(f"奇偶失衡({odds}:{6-odds})落在小概率边缘区间。")
            violation_weight += 0.2

        # 3. 和值区间因果约束 (大数定律范畴)
        total_sum = sum(reds)
        bounds_sum = self.rules["sum_bounds"]
        if isinstance(bounds_sum, list) and (total_sum < bounds_sum[0] or total_sum > bounds_sum[1]):
            report_status = "failed"
            warnings_list.append(f"和值偏离({total_sum})，未遵循中心极限定理置信区间。")
            violation_weight += 0.3

        # 4. 离散跨度因果 (Span)
        span = reds[-1] - reds[0]
        bounds_span = self.rules["span_bounds"]
        if isinstance(bounds_span, list) and (span < bounds_span[0] or span > bounds_span[1]):
            warnings_list.append(f"序列首尾跨度异常({span})。")
            violation_weight += 0.15

        # 5. 质数引力分析
        prime_count = sum(1 for x in reds if x in self.primes)
        bounds_prime = self.rules["prime_count_bounds"]
        if isinstance(bounds_prime, list) and (prime_count < bounds_prime[0] or prime_count > bounds_prime[1]):
            warnings_list.append(f"素数聚集态崩塌(当前质数={prime_count}个)。")
            violation_weight += 0.1

        # 6. 系统熵值(AC值)约束
        ac_val = self._calculate_ac_value(reds)
        ac_min = int(self.rules["ac_value_min"]) # type: ignore
        if ac_val < ac_min:
            report_status = "failed"
            warnings_list.append(f"组合随机游走熵(AC={ac_val})过低，体系结构过于对称。")
            violation_weight += 0.35

        # 7. 极寒收缩效应 (环境因果强约束)
        if entropy_temp < -5.0:
            small_count = sum(1 for x in reds if x <= 16)
            if small_count < 4:
                report_status = "failed"
                warnings_list.append(f"极寒效应当发：当前温度 {entropy_temp:.1f}，预期向小数区(1-16)集聚，但大数过多阻力受困。")
                violation_weight += 0.5

        # 如果毫无瑕疵
        if not warnings_list:
            warnings_list.append("完美匹配物理与大数统计定律预设的所有因果。")

        # 将综合惩罚映射回一个加成因数 (最大1.0, 越严厉惩罚约接近0)
        causal_multiplier = max(0.1, 1.0 - violation_weight)
        if causal_multiplier > 0.95:
            causal_multiplier = 1.0

        return {
            "status": report_status, 
            "warnings": warnings_list,
            "confidence_multiplier": causal_multiplier,
            "metrics": {
                "sum": total_sum,
                "span": span,
                "odds": odds,
                "primes": prime_count,
                "ac": ac_val,
                "max_seq": max_seq
            }
        }
