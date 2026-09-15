# 7×24 持续演化（GitHub Actions 免费接力）

## 它解决什么
你之前要的是「免费、不绑卡/不付费验证、尽量 7×24」。任何临时沙箱/免费 VM 都会过期或要卡；唯一无卡免费、还能持续跑 Python 计算的，是 **GitHub Actions（Public 仓库无限免费分钟）**。本方案把原本常驻的 daemon 改成分片 + 状态持久化，用 Actions 的「单次 job（≤6h）→ 交棒下一轮」接力出"逻辑上的 7×24"。

## 机制
- `cloud_daemon_24x7.py --run-once --max-runtime 19800`：连续跑演化，直到累计约 **5.5 小时**后退出（预留余量给 6h job 上限）。
- 演化进度靠状态文件接力：`formula_evolution.py` 自己读 `formula_evolution_history.json` 续写历史；只要这些文件被 commit 回仓库，**下一轮 Actions run 就能续算**。
- `daemon_state.json` 记录已完成轮数 / 累计时长，跨 run 续接计数。
- `.github/workflows/evolve.yml`：
  - `schedule: "0 */6 * * *"`（UTC）每 6 小时**兜底**触发；
  - job 末尾把状态文件 commit 回仓库，并 `createWorkflowDispatch` **链式触发下一轮**；
  - `concurrency`（同组排队）**防重叠**——旧 run 结束新 run 才开始，无缝接力。

## 启用步骤（需你来做，助手没有 GitHub 凭证）
1. 把本仓库推到 **GitHub Public** 仓库（Private 仅 2000 min/月免费，重型计算不够用）。
2. 仓库 `Settings → Actions → General → Workflow permissions` 保持默认即可（本 workflow 已声明 `permissions: contents: write`）。
3. 首次触发：Actions 页 → `Evolution 7x24` → `Run workflow`（手动跑一次）；之后由链式 + 6h cron 自动持续。
4. 想停：Actions 页 Disable workflow，或删掉 `.github/workflows/evolve.yml`。

## 本地/单机能用的等价命令
```bash
# 本机直接跑一轮接力（依赖 .venv）
python cloud_daemon_24x7.py --run-once --max-runtime 19800
# 或常驻模式（本机/IDE 自启用，见 start_local.ps1）
python cloud_daemon_24x7.py
```

## 注意
- 单次 job 上限 6h，本方案跑 5.5h 交棒；末尾约留 10 分钟收尾，不会被硬杀导致状态损坏。
- **Public 仓库代码完全公开**（含演化算法）。若需保密，改用 Private（额度受限）或本地/付费 VM。
- `daemon_state.json` 与状态 json 由 workflow 自动 commit（commit 带 `[skip ci]`），无需手动管理；本 workflow 不监听 push，故不会自触发递归。
- 旧方案（`sandbox-wake/`、`cnb.yml`、本地 `start_local.ps1`）仍可用于"本机/IDE 自启"，与云端接力互不冲突。
