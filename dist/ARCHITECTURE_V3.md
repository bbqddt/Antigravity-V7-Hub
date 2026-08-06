# Antigravity 分布式架构 V3.0

## 三节点架构

```
┌─────────────────────────────────────────────────────────────┐
│                     三节点计算集群                              │
├──────────────────┬──────────────────┬───────────────────────┤
│  Node 1: 本地     │  Node 2: 云端     │  Node 3: QwenPaw       │
│  Claude Code     │  腾讯云 CVM       │  AgentScope 前端       │
│                  │  Ubuntu 26.04     │  (浏览器)              │
│  · 预测引擎开发   │  · 32核 Xeon      │  · 定时任务执行        │
│  · 公式语言设计   │  · 123GB 内存     │  · 心跳监控            │
│  · 架构决策      │  · 持续运行        │  · 数据搬运            │
│  · LLM推理      │  · 大规模回测      │                      │
│  · 结果分析      │                  │                      │
└──────────────────┴──────────────────┴───────────────────────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                       共享文件 (dist/)
                       JSON 任务协议
```

## 各节点职责

### Node 1: 本地 (Claude Code) — 大脑
- 预测引擎开发与调优
- 公式语言 & 策略生成
- 架构设计与决策
- 结果分析与策略调整
- 任务分发与协调

### Node 2: 腾讯云 CVM — 肌肉
- 32核并行回测计算
- 123GB 内存大规模数据训练
- 持续运行守护进程
- 数据采集（直连500.com）
- 公式进化批量评估

### Node 3: QwenPaw — 哨兵
- 定时任务触发
- 心跳监控与告警
- 数据搬运（文件同步）
- 日常值守

## 通信协议

### 任务发布 (Claude → 云端/QwenPaw)
```
dist/tasks/{task_id}.json
{
  "task_id": "abc123",
  "task_type": "backtest|data_collection|nonrandomness|formula_evolution",
  "params": {...},
  "created_at": "2026-07-08T...",
  "assigned_to": "cloud|qwenpaw",
  "priority": "normal|high"
}
```

### 结果回报
```
dist/results/{task_id}.json
{
  "task_id": "abc123",
  "status": "success|error",
  "completed_at": "...",
  "output_files": [...],
  "message": "..."
}
```

## 部署文件清单

| 文件 | 用途 | 部署位置 |
|------|------|---------|
| `cloud_quick_deploy.py` | 本地部署脚本 | 本地 |
| `cloud_runner_v2.py` | 云端守护进程 | 云端+CVM |
| `init_cloud.sh` | 云端初始化脚本 | 云端 |
| `distributed_bridge.py` | 分布式桥接器 | 本地+云端 |
| `cloud_info.py` | 云端信息收集 | 云端 |
| `run.sh` | 轻量 Runner | 云端 |

## 待完成

- [ ] 获取腾讯云公网 IP
- [ ] 运行 `cloud_quick_deploy.py --setup` 完成首次部署
- [ ] 启动云端守护进程
- [ ] 配置 QwenPaw 运行 executor
- [ ] 验证三节点通信
