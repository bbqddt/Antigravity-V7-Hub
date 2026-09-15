# 沙箱唤醒方案（策略 A + 策略 B）

> ⚠️ **已弃用**：原 CloudStudio 沙箱 `https://webview.e2b.gz2.sandbox.cloudstudio.club` 已销毁（返回 12806 工作空间没有找到），本套"唤醒"脚本不再需要。
> 请改用仓库根目录的**本地无沙箱运行方案**：`start_local.ps1`（开机/开 IDE 自动拉起 `cloud_daemon_24x7.py` + `monitor_dashboard.py`）；公网暴露用 `.\cloudflared.exe tunnel --url http://localhost:8080`。

## 核心架构前提（务必先理解）
沙箱休眠时里面**什么都不运行**，所以"沙箱自己唤醒自己"是死循环。
能唤醒沙箱的只能是沙箱之外的东西：本地机器 / IDE / 外部定时服务。
它们的共同动作是——**向沙箱的 webview 地址发一个请求**，CloudStudio 代理收到后发现空间在休眠，就把它拉起来；拉起后 supervisord 已配好，会自动把 3000 服务带起来。

因此唤醒脚本**必须跑在沙箱外**。

---

## 策略 A：唤醒式（本地 / IDE 触发）
文件：`wake_sandbox.sh`（bash，跨平台，Windows 用 Git Bash / WSL）或 `wake_sandbox.ps1`（原生 PowerShell，配 Windows 任务计划用）。

逻辑：打一下沙箱地址触发唤醒 → 轮询 `/health` 直到 3000 服务就绪。

### 沙箱地址（已内置默认，可跳过）
脚本已内置你的沙箱地址 `https://webview.e2b.gz2.sandbox.cloudstudio.club`，直接 `./wake_sandbox.sh` 即可。
如需覆盖，任选一种：
```bash
./wake_sandbox.sh "https://webview.e2b.gz2.sandbox.cloudstudio.club"
SANDBOX_URL="https://webview.e2b.gz2.sandbox.cloudstudio.club" ./wake_sandbox.sh
```

### 怎么跟 IDE 关联
| 你的场景 | 怎么挂 |
|---|---|
| CloudStudio 自带 Web IDE | 不用脚本——打开 IDE 本身就唤醒沙箱，supervisord 已自动拉起服务，打开即用 |
| 本地 VS Code 连这个远程沙箱 | 把脚本放本地，挂到「文件夹打开时自动跑」或开机启动（macOS launchd / Linux systemd-user / Windows 任务计划） |
| JetBrains 系 | Settings → Tools → Startup Tasks，或外部工具里配一条 `bash wake_sandbox.sh` |
| Windows 任务计划 | 触发器选"登录时/开机时"，操作调用 `powershell -File 路径\wake_sandbox.ps1` |

---

## 落地：把唤醒接进「开机 / IDE」（直接可用的代码）

下面两个文件让唤醒**自动发生**，不用你手动跑脚本：

### 1) VS Code 集成（与 IDE 联接）— `.vscode/tasks.json`
已配置 `runOn: "folderOpen"`。用 VS Code 打开本文件夹时，会**自动**执行 `wake_sandbox.ps1` 唤醒沙箱。
- 前提：VS Code 打开的是包含 `wake_sandbox.ps1` 的这个文件夹。
- 无需任何扩展，原生 tasks 支持。

### 2) Windows 登录自启（开机即唤醒）— `install_task.ps1`
双击或在 PowerShell 里运行：
```powershell
powershell -ExecutionPolicy Bypass -File install_task.ps1
```
它会注册一个 `WakeCloudStudioSandbox` 计划任务，触发器为 **AtLogOn（登录时）**，隐藏窗口运行。
即"电脑开机/登录后"自动把沙箱拉起来，跟 IDE 是否打开无关。
- 立即测试：`powershell -Command "Start-ScheduledTask -TaskName 'WakeCloudStudioSandbox'"`
- 卸载：`powershell -ExecutionPolicy Bypass -File uninstall_task.ps1`

> 注：脚本已内置默认沙箱地址，计划任务 / VS Code 现在**无需**再单独设 `SANDBOX_URL` 也能跑。
> 若以后地址变了，可在「系统 → 高级系统设置 → 环境变量」设用户变量 `SANDBOX_URL=新地址` 覆盖，或显式传 `-SandboxUrl '...'`。

### JetBrains 系（补充）
Settings → Tools → Startup Tasks 添加一条，或在 Tools → External Tools 配：
`Program: powershell`，`Arguments: -ExecutionPolicy Bypass -File 路径\wake_sandbox.ps1`

---

## 策略 B：GitHub Actions 定时 ping（⚠️ 对你这个 CloudStudio 沙箱很可能无效，先读风险）

> ### 🚨 重要前提风险（务必先验证再依赖）
> 我用裸 `curl` 实测你的沙箱地址时，`/` 和 `/health` 都返回 **404**——而你在浏览器（带 webview 会话）里 `/health` 是 **200**。
> 这说明 CloudStudio 的唤醒/路由**绑定在 webview 会话上**：没有浏览器会话的"裸请求"不会触发唤醒，也拿不到 200。
> **GitHub Actions 发出的就是这种会话外的裸请求**，所以它大概率只会收到 404，**无法**让你的沙箱永久保活。
> 结论：**策略 B 对 CloudStudio 很可能不成立**，不要把它当"真 24×7"来依赖。真正可靠的"开机/开 IDE 就唤醒"是下面的策略 A。
> 唯一例外：若 CloudStudio 官方明确支持"任意外部 HTTP 请求即唤醒"（部分套餐有），那 B 才可能生效——但这需要你用一次真 GitHub Action 跑出来验证，而不是直接假设。

### ✅ 更靠谱的"常驻"方案（推荐先看这个，可能就不用策略 B 了）
CloudStudio 官方已支持 **「永不休眠」**：
- **IDE 内设置**：「长时间不操作之后」的策略可选 5 / 10 / 20 分钟切断，**或直接选"永不休眠"**；
- **工作空间配置**（如 `cnb.yml`）还能设 `保活时间`（例 `3600000ms` = 1 小时）让空间后台保持。
这从平台层面让空间不睡，比"GitHub Actions 裸请求赌代理唤醒"可靠得多。
- **代价**：永不休眠会持续消耗算力包（可能需专属/付费套餐），比"用时才开"贵。
- 若你的目标是"随时能连、不休眠"，**直接在 IDE 里启用「永不休眠」即可，可跳过策略 B**。

文件：`.github/workflows/keepalive.yml`

每 15 分钟（UTC）ping 一次沙箱地址（仅在上面风险排除后才值得启用）：
- 若生效：沙箱永远不睡、不依赖本机开机、免费。
- 若按实测不成立：GitHub Action 日志里会一直看到非 200，沙箱照样休眠。

### 落地步骤（你自推）
1. 把这个 `.github/workflows/keepalive.yml` 放进**你自己的 GitHub 仓库**对应路径。
2. 仓库 → Settings → Secrets and variables → Actions → New repository secret：
   - Name：`SANDBOX_URL`
   - Value：你的沙箱 webview 地址（即 `https://webview.e2b.gz2.sandbox.cloudstudio.club`）
3. Actions 页面启用该 workflow；可点 `Run workflow` 手动触发一次验证。

> 安全提示：地址走 secret，**不要**把真实地址硬编码进仓库。GitHub 会在日志里自动脱敏 secret。

### 注意事项
- cron 时间用的是 **UTC**，注意和你的时区差。
- 免费额度：公开仓库 scheduled workflows 免费；私有仓库消耗免费额度。
- 仓库若长期无任何活动，GitHub 可能在 60 天后禁用 scheduled workflow（fork 更明显）——保持仓库有一点活动即可。
- 前提是你的 CloudStudio 套餐确实支持"收到 web 请求即唤醒/保活"，首次务必手动跑一次验证。

---

## 验证清单
- [ ] 沙箱地址正确（CloudStudio 预览地址，对应 3000 端口）
- [ ] 3000 服务确实暴露了 `/health` 且返回 200
- [ ] 策略 A：本地手动跑一次，能看到 `✅ 服务已就绪`
- [ ] 策略 B（可选/待验证）：先确认"裸请求能否唤醒"——用本机 `curl 沙箱地址/health`（浏览器关掉、无会话）看是否仍能 200；能，才值得推 GitHub Actions。否则跳过。
- [ ] 策略 B（若启用）：手动 `Run workflow` 一次，Actions 日志显示 health 200；并确认 secret `SANDBOX_URL` 已配置
