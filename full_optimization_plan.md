# 全面智能优化方案 V1.0 — 速度+云端+迭代+备案

## 当前瓶颈分析

### 1. 计算速度瓶颈
| 操作 | 耗时 | 说明 |
|------|------|------|
| 单次公式评估(15窗口) | 0.21s | 本地单机 |
| 一代演进(15公式×15窗口) | 0.8s | 串行逐个评估 |
| 200代×50公式 | ~35min | 本地完成 |
| 全量原语评估(36个) | ~7.5s | 串行 |

**问题**：
- 所有评估都是串行的，CPU利用率低
- 没有缓存机制，每次重新计算
- 没有增量更新，窗口滑动时重复计算

### 2. 云端部署状态
- HF Space: 只有Gradio UI，没有实际运行能力（cpu硬件太弱）
- 无腾讯云/阿里云长期运行实例
- 无GitHub Actions定时触发器
- **结论：云端部署等于没有部署**

### 3. 公式研发投喂迭代
- 公式演进引擎已对接V3.2评估器 ✅
- 但每次手动运行，无自动调度
- 新原语需要人工添加到系统
- LLM生成的假设没有反馈到公式引擎

### 4. 备案缺失
- 无回滚机制（改了evaluator_v3.py后如果出bug无法恢复）
- 无测试套件（改了primitive.py不知道有没有破坏其他模块）
- 无性能监控（不知道演进速度在变慢还是变快）

---

## 完整方案

### A. 加速策略（本地）

#### A1. 并行评估
```python
from concurrent.futures import ThreadPoolExecutor

def evaluate_batch_parallel(formulas, draws, ev, max_workers=8):
    """并行评估多个公式"""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(ev.evaluate, f, draws, ...): name 
                   for name, f in formulas.items()}
        for future in as_completed(futures):
            name = futures[future]
            results[name] = future.result()
    return results
```
预期提速：5-8倍（8核CPU）

#### A2. 结果缓存
```python
# 缓存key: formula_name + train_end + test_end + hash(primitives_params)
# 缓存到 evolution_cache.json
# 如果训练集没变，直接读缓存
```
预期提速：后续代次提速50%+（大部分公式是变异体，训练集相同）

#### A3. 增量评估
```python
# 窗口滑动时，只计算新增的10期，不重新算前面的
# 维护一个滑动窗口状态的增量Brier
```

### B. 云端7×24部署

#### B1. 最小可用云端环境
**选择：HuggingFace Spaces (Free tier)**
- 不需要GPU（纯Python计算，CPU够用）
- 免费额度足够跑公式演进
- 配置：定期触发器（每6小时跑一轮演进）

**文件结构：**
```
hf_space/
├── app.py              # Gradio Web UI（已有，保留）
├── evolution_worker.py  # 云端演进工作进程（新建）
├── requirements.txt     # 依赖
└── README.md           # 使用说明
```

**evolution_worker.py：**
```python
# 从HF Space的定期触发器调用
# 功能：运行5代演进 → 保存结果 → 推送到GitHub
import subprocess
subprocess.run(["python", "evolution_worker.py"])
# 结果写入 evolution_state.json
# 通过Git push更新最新公式
```

#### B2. 备用：GitHub Actions
- 每天凌晨自动触发
- 运行轻量版演进（5代×20公式）
- 结果存到仓库的 `evolution_result.json`
- 免费，不需要自己的服务器

### C. 公式研发投喂迭代闭环

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  LLM生成假设 │────▶│  公式生成    │────▶│  V3.2评估   │
│  Gemini/Claude│     │  新原语     │     │  combined_  │
│  分析历史数据 │     │  组合公式   │     │  score      │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │  金库入库    │◀────│  优胜劣汰    │
                    │ best_formula │     │  beats_random│
                    └─────────────┘     └─────────────┘
```

**具体实现：**
1. 每次演进完成后，将top-5公式写入 `formula_vault.json`
2. 从金库中读取最佳原语组合，作为下轮进化的种子
3. LLM分析金库中公式的特征，提出新原语建议
4. 人工/AI确认后加入primitive.py
5. 重新跑一致性检查 → 演进 → 金库更新

### D. 备案体系

#### D1. Git版本控制
- 每次重大变更提交到Git
- 标签标记：`v3.0`, `v3.1`, `v3.2`
- 可随时 `git checkout v3.1` 回滚

#### D2. 测试套件
```python
# formula_lang/tests/
# test_primitive_count.py     # 原语数量检查
# test_evaluator_v3.py        # 评估器正确性
# test_consistency.py         # 一致性检查
# test_evolution_basic.py     # 演进基本功能
```

#### D3. 性能监控
```python
# performance_log.json
{
    "timestamp": "2026-07-25T04:34:49",
    "generations": 3,
    "population": 15,
    "total_time_seconds": 2.5,
    "time_per_generation": 0.83,
    "best_combined_score": 0.4537,
    "best_hits": 1.100
}
```
每次演进自动追加，监控趋势。

---

## 执行计划

### Phase 1: 立即执行（本次会话）
- [x] 公式演进引擎对接V3.2
- [x] 一致性守卫集成到演进流程
- [ ] 并行评估实现
- [ ] 性能监控日志

### Phase 2: 本周内
- [ ] HF Space云端部署
- [ ] GitHub Actions定时触发
- [ ] 测试套件编写

### Phase 3: 本月内
- [ ] 公式金库系统
- [ ] LLM→公式投喂闭环
- [ ] 增量评估优化
