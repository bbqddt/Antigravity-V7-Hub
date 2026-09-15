# Antigravity 会话状态 — 2026-07-21

## 今日完成

### 1. 金库校准 ✓
- 全量重新评估 29 个公式（walk-forward, n_windows=20, window_size=400, step=40）
- 21/29 个公式偏差 > 0.05，需要校准
- 7 个 active 公式被降为 bench（校准后 avg < 1.09）：
  - cascade_multi_scal_dynamic_co_cascade: 1.2267 → 1.0700
  - resonance_trend_mome_spectral_c_resonance: 1.2000 → 1.0500
  - hybrid_resonance_dynamic_co_pair_orbit_resonance: 1.2267 → 1.0900
  - tri_res_dynamic__multi_sc_resonance: 1.1867 → 1.0900
  - tri_res_multi_sc_spectral_resonance: 1.1533 → 1.0700
  - tri_res_spectral_mutual_e_resonance: 1.1400 → 1.0850
  - resonance_dynamic_co_trend_mome_resonance: 1.1267 → 1.0700
- v4tri_modular 系列：test_avg == avg_hits，存在数据泄露/过拟合

### 2. 重复公式清理 ✓
- 移除 `tri_res_multi_sc_dynamic__resonance`（与 `tri_res_dynamic__multi_sc_resonance` 原语集完全相同）
- 金库从 30 → 29 个

### 3. 守护进程卡死根因定位 ✓
- **根因**：`cross_validate()` 调用 V2 评估器 `evaluate_comprehensive()`（含 NDCG/KL散度/排名分布），每轮极慢
- 20 个公式 × 每公式多轮 = 超时崩溃
- **修复**：
  - `validate_formula()` 改用 V1 快速评估器
  - `__init__()` 自动从已有 cycle 文件恢复 cycle_count，避免覆盖

### 4. 手动测试一轮完整周期 ✓
- 修复后成功跑通：开发 439 公式 (682s) + 交叉验证 + 对战 + 保存金库 + 写 cycle 文件
- 总耗时 809 秒（~13.5 分钟）

### 5. 创建会话状态加载器 ✓
- `antigravity_state_loader.py` — 一键查看金库/演进/守护进程状态

---

## 当前金库状态
- 总公式：29
- Active: 6 | Bench: 12 | Eliminated: 11
- 最佳公式：`tri_res_dynamic__mutual_e_resonance` (test=1.3667)
- 演进轮次：9（最后产出 2026-07-14T21:20:10，已停滞 6 天）
- 数据：3475 期 (#3001~#26078)

---

## 待办事项（明天继续）

### P0 - 启动修复后的守护进程并确认产出新轮次
- 代码已修复，但守护进程多次重启失败（taskkill 杀不死某些进程）
- **明天操作**：
  ```bash
  cd D:/cdx/antigravity_cloud
  python continuous_evolution_daemon_v4.py --daemon --interval 30
  # 等 15 分钟后检查是否有新 cycle 文件
  ls evolution_cycle_*.json
  ```

### P1 - 考虑引入 V2 评估器做全面重评
- 当前 `evaluator.py` 是 V1，只有 avg_hits/std/p_value
- V2 评估器在公式开发引擎中可用，但守护进程的 `cross_validate` 里禁用以避免超时
- 可以考虑：守护进程用 V1 快速评估，定期用 V2 做精细校准

### P2 - 分析为什么 V4 公式全部被 eliminated
- 10 个 v4tri 公式都是 `test_avg == avg_hits`
- 说明开发引擎保存时直接复制了 avg_hits 到 test_avg，没有独立测试集
- 这是 `advanced_formula_developer_v3.py` 的保存逻辑问题

### P3 - 更新 MEMORY.md 索引
- 把今天的 session-state 加入记忆索引（已完成）

---

## 关键文件
- `formula_vault.json` — 已校准更新（version=4.0_calibrated）
- `continuous_evolution_daemon_v4.py` — 已修复 validate_formula 和 cycle_count 恢复
- `antigravity_state_loader.py` — 会话状态加载器
- `calibration_report_20260721.json` — 校准报告
