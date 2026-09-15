# Antigravity - 双色球预测系统 — 工作手册

## ⚠️ 启动必读

### 当前状态 (2026-07-25 V3.2 + 全面优化)
- **评估器**: V3.2 双指标体系（avg_hits主 + avg_brier辅）
- **原语库**: 36个（含3个信息论新原语）
- **最佳公式**: gen3_new_6 hits=1.153, combined_score=0.4537, beats_random=True
- **并行加速**: 10公式×15窗口=0.02s（提速100倍）
- **守护进程**: cloud_daemon.py — 每6小时自动演进
- **一致性守卫**: 每次演进前强制检查，有ERROR中止
- **不再改变评估体系**。后续所有改进基于 V3.2 双指标。

### 关键基线
| 指标 | 值 |
|------|-----|
| 随机期望命中 | 1.09 |
| RED_BRIER_BASELINE | 0.148760 |
| combined_score范围 | [0, 1]，越高越好 |
| 单次评估耗时(15窗口) | ~0.02s（并行） |

---

## 开发协议（铁律 — 违反即停）

**任何代码修改前，必须完成PLAN：**
```
## 目标: 量化指标
## 流程: 步骤1→2→3
## 验收标准: Go/No-Go条件
## 迭代上限: 不超过N轮
```
详见记忆: `antigravity-workflow-protocol.md`

---

## 运行命令速查

```bash
cd <project_root>

# ─── 日常必跑 ───
python formula_evolution.py --run --generations 5 --population 30   # 公式演进
python cloud_daemon.py --status                                      # 守护状态
python consistency_checker.py --enforce                              # 一致性检查

# ─── 数据 ───
python data_updater_v2.py                                            # 更新开奖数据

# ─── 回测 ───
python walkforward_backtest_v2.py --engine compare                   # 引擎对比

# ─── 多模型协同 ───
python smart_evolution.py --quick                                    # 快速模式
python smart_evolution.py --rounds 3                                 # 完整模式

# ─── 预测 ───
python orchestrator.py                                               # 统一编排
python predictor_verifier.py                                         # 预测验收

# ─── 诊断 ───
python consistency_checker.py                                        # 完整检查
python cloud_daemon.py --status                                      # 守护状态
cat evolution_performance_log.json                                   # 性能监控
```

---

## 核心架构

```
┌─────────────────────────────────────────────────────┐
│                  Antigravity V3.2                    │
│                                                      │
│  数据层                                              │
│  data_layer.py ← lottery_history.csv (3481期)        │
│       │                                              │
│       ├─▶ 预测引擎群                                  │
│       │    luckcast_antigravity_v1.py (旗舰V15)      │
│       │    enhanced_predictor.py (主力V2.0)          │
│       │    formula_lang/ (36原语+V3.2评估)           │
│       │                                              │
│       ├─▶ 多AI协同                                   │
│       │    smart_evolution.py (Gemma4+Gemini+...)    │
│       │                                              │
│       ├─▶ 因果验证                                   │
│       │    core/causal_reasoning.py                  │
│       │    nonrandomness_detector.py                 │
│       │                                              │
│       ▼                                              │
│  公式演进引擎 (formula_evolution.py)                  │
│  ┌─────────────────────────────────┐                 │
│  │ 生成 → V3.2并行评估 → 选择变异   │                 │
│  │         ↑                       │                 │
│  │    consistency_checker.py       │                 │
│  │    (启动前强制检查)              │                 │
│  └─────────────────────────────────┘                 │
│       │                                              │
│       ▼                                              │
│  输出                                                │
│  formula_evolution_history.json                      │
│  evolution_performance_log.json                      │
│  latest_prediction.json                              │
│                                                      │
│  ┌─────────────────────────────────┐                 │
│  │  cloud_daemon.py (7×24守护)     │                 │
│  │  每6小时自动演进 → Git推送       │                 │
│  └─────────────────────────────────┘                 │
└─────────────────────────────────────────────────────┘
```

---

## 公式语言系统 V3.2

### 评估器 (`formula_lang/evaluator_v3.py`)
- **双指标**: avg_hits (主) + avg_brier (辅)
- **综合评分**: combined_score = 0.6*brier_norm + 0.4*hits_norm
- **击败随机**: beats_random = hits>1.09 OR brier<0.1413
- **并行评估**: evaluate_batch_parallel() — ThreadPoolExecutor
- **缓存机制**: CacheManager — 相同参数直接读缓存

### 原语库 (36个)
| 类别 | 原语 |
|------|------|
| 时序 | PeriodicEcho, RecencyGradient, SeasonalResonance |
| 关系 | CooccurrenceAffinity, MutualExclusionScore, PairOrbit |
| 结构 | BinaryTopology, DigitManifold, PositionSignature |
| 频谱 | SpectralPower, WaveletCoherence |
| 几何 | SphereProjection, DistanceCluster |
| 混沌 | AttractorDistance, LyapunovSignal |
| 序列模式 | SumRangeTracker, GapPatternAnalyzer, TrendReversalDetector |
| 组合特征 | ModuloClassDistribution, DigitPairFrequency, AdjacentNumberBias |
| 高阶统计 | SkewnessSignal, KurtosisSignal, TailRiskSignal |
| 跨期记忆 | LagCorrelation, PeriodicGap, RecurrenceWindow |
| 多尺度分析 | MultiScaleFrequency, ScaleTransition |
| 环境感知 | EnvironmentAware, PhaseDetector, RegimeSwitch |
| 统计 | PhysicalBiasDetector |
| **信息论** | **MutualInformationPair, ResidualSignal, ConditionalProbabilityMatrix** |

### 组合算子 (`grammar.py`)
- weighted_sum: 线性加权
- resonance: 共振（加权乘积）
- cascade: 级联（筛选→精炼）
- phase_align: 相位对齐（加权平均）

### 变异器 (`mutator.py`)
- 参数级变异: 高斯扰动 + 边界内随机重置
- 逻辑级变异: 温和调整窗口/阈值
- 退火策略: 变异幅度随代数递减

---

## 守护与监控

### 一致性守卫 (`consistency_checker.py`)
- 每次演进启动前自动运行
- 检查项：原语数量、导出列表、评估器版本、工厂方法完整性
- 有ERROR则中止演进（exit 1）

### 性能监控 (`evolution_performance_log.json`)
- 每次演进后自动记录
- 字段：timestamp, total_time, time_per_generation, best_formula, best_score, best_hits, best_brier, beats_random
- 趋势监控：速度是否变慢，质量是否下降

### 云端守护 (`cloud_daemon.py`)
- 每6小时自动运行轻量演进（5代×20公式）
- 检查新开奖数据
- 健康检查：数据文件/评估器/原语/一致性/磁盘空间
- 错误记录（保留最近10条）
- 自动Git推送

---

## 上次完成的工作 (2026-07-25)

### V3.2 + 全面优化
1. **evaluator_v3.py** — 并行评估 + CacheManager
   - evaluate_batch_parallel(): 10公式×15窗口=0.02s
   - CacheManager: MD5哈希缓存，24h有效期
2. **formula_evolution.py** — 对接V3.2 + 并行 + 性能监控
   - 使用evaluate_batch_parallel()并行评估
   - 每次演进后写入performance_log.json
   - 启动前强制consistency_checker --enforce
3. **cloud_daemon.py** — 新建，7×24守护
   - 每6小时自动演进
   - 健康检查 + 错误告警 + Git推送
4. **consistency_checker.py** — 新建，一致性守卫
   - 5项检查覆盖全部模块接口
5. **__init__.py** — 导出36个原语（含3个信息论新原语）
6. **registry.py** — 对接V3.2评估器
7. **CLAUDE.md** — 完整工作手册（本次）

---

## 下一步方向
- [ ] HF Spaces部署（需要HF_TOKEN + Space ID）
- [ ] GitHub Actions定时触发（需要创建新仓库）
- [ ] LLM→公式投喂闭环（Gemini分析金库→提出新原语建议）
- [ ] 增量评估优化（滑动窗口只计算新增部分）
