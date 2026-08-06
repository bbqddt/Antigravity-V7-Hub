---
name: antigravity-cloud-deployment
description: 云端部署架构、待完成任务、7个模型接入方案（Gemma4.2/DS/HF等）、分布式协作协议
metadata:
  node_type: memory
  type: project
  created: 2026-07-11
  originSessionId: current-session
---

# Antigravity 云端部署与模型接入完整规划

## 一、云端部署架构

### 1.1 当前环境状态

| 组件 | 状态 | 位置 |
|------|------|------|
| CloudStudio 沙箱 | ✅ 已连接 | `aican.do@ff7900c0b6e4` |
| Python 3.11.15 | ✅ 已安装 | `/c/Users/Administrator/AppData/Local/hermes/...` |
| uv 包管理器 | ✅ 已安装 | `uv pip` |
| 项目代码 | ✅ 已部署 | `/c/Users/Administrator/antigravity_cloud/` (36个.py) |
| 数据文件 | ✅ 已同步 | `data/lottery_history.csv` (3,475期) |
| 依赖包 | ✅ 已安装 | pandas, scipy, scikit-learn, statsmodels, joblib |

### 1.2 云端部署脚本体系

| 脚本 | 功能 | 状态 |
|------|------|------|
| `cloud_deploy.py` | 腾讯云CVM完整部署(SSH+SCP+守护进程) | 代码就绪，需配置IP |
| `cloud_quick_deploy.py` | 简化版一键部署 | 代码就绪，需设置CLOUD_HOST |
| `cloud_runner.py` | 统一编排入口(V1.0) | ✅ 已运行成功 |
| `cloud_runner_v2.py` | 云端守护进程V2.0(32核/123GB) | 代码就绪 |
| `cloud_hermes.py` | GitHub Actions云端Hermes V8.0 | 代码就绪 |
| `cloud_info.py` | 云端系统信息采集 | ✅ 已运行(8核/101G) |

### 1.3 云端待完成任务清单

#### P0 - 必须完成
1. **配置CloudStudio沙箱持续运行**
   - 将 `cloud_runner_v2.py` 设为守护进程
   - 每30分钟自动运行数据+预测
   - 每6小时运行非随机性检测
   - 每周日运行滚动回测

2. **集成7个外部模型到预测管道**
   - Gemma4 (Ollama localhost:11434)
   - Gemma2 (Ollama localhost:11434)
   - DS (DeepSeek, 需API Key)
   - HF (HuggingFace, 需API Key)
   - 其他3个模型待确认

3. **修复已知Bug**
   - `tg_remote_hub.py` 引用不存在的 `V8_Core`
   - `orchestrate.py` 中 `latest_prediction.json` 读取编码问题

#### P1 - 重要
4. **GPU蒙特卡洛集成** (`core/inference.py`)
   - 当前StrategyEngine需要torch
   - 沙箱需安装PyTorch
   - 千万级张量化过滤待测试

5. **分布式协作协议** (`distributed_bridge.py`)
   - QwenPaw远程计算节点
   - 任务发布/结果轮询机制
   - 需配置共享目录或SSH

6. **Telegram Commander Bot** (`commander_bot.py`)
   - 需配置TG_BOT_TOKEN和TG_CHAT_ID
   - 远程推送预测结果

#### P2 - 优化
7. **公式自主进化** (`autonomous_evolution_v2.py`)
   - 每周自动运行
   - 生成+变异+评估新公式

8. **CloudStudio → 持久化存储**
   - 沙箱可能重置，需定期备份到本地

---

## 二、7个模型接入方案

### 2.1 模型清单

| # | 模型 | 来源 | 接入方式 | 状态 |
|---|------|------|----------|------|
| 1 | **Gemma4** | Ollama本地 | `localhost:11434/api/chat` | 代码已写(`ai_multi_model_collab.py`) |
| 2 | **Gemma2** | Ollama本地 | `localhost:11434/api/chat` | 同上 |
| 3 | **DeepSeek (DS)** | 云端API | HTTP API调用 | 需API Key |
| 4 | **HuggingFace (HF)** | HuggingFace API | HF Inference API | 需API Key |
| 5 | **Luckcast V15** | 内置引擎 | `luckcast_antigravity_v1.py` | ✅ 已集成 |
| 6 | **Enhanced V2.0** | 内置引擎 | `enhanced_predictor.py` | ✅ 已集成 |
| 7 | **Evolution Life** | 内置引擎 | `evolution_life.py` (RF+Spectral) | ✅ 已集成 |

### 2.2 模型协同架构

```
                    ┌─────────────────────┐
                    │   Orchestrator      │
                    │   (统一编排入口)     │
                    └─────────┬───────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────┴─────┐     ┌──────┴──────┐     ┌──────┴──────┐
    │ 本地模型   │     │  内置引擎   │     │  云端模型   │
    └─────┬─────┘     └──────┬──────┘     └──────┬──────┘
          │                   │                   │
    ┌─────┴─────┐     ┌──────┴──────┐     ┌──────┴──────┐
    │ Gemma4    │     │ Luckcast    │     │ DeepSeek    │
    │ Gemma2    │     │ V15         │     │ (DS)        │
    │ Ollama    │     │ Enhanced    │     │ HuggingFace │
    └───────────┘     │ V2.0        │     │ (HF)        │
                      │ Evolution   │     └─────────────┘
                      │ Life        │
                      └─────────────┘
                              │
                    ┌─────────┴──────────┐
                    │  信号融合 + 因果验证│
                    │  Signal Fusion +   │
                    │  Causal Reasoning  │
                    └────────────────────┘
```

### 2.3 模型接入代码位置

| 文件 | 模型 | 说明 |
|------|------|------|
| `ai_multi_model_collab.py` | Gemma4+Gemma2+公式语言 | 5步协同计算 |
| `orchestrate.py` | Luckcast+Enhanced | 统一编排入口 |
| `evolution_life.py` | Evolution Life(RF+Spectral) | 流形演算 |
| `enhanced_predictor.py` | Enhanced V2.0 | 加权集成预测 |
| `luckcast_antigravity_v1.py` | Luckcast V15 | 7维度预测引擎 |
| `core/inference.py` | GPU蒙特卡洛 | PyTorch张量化过滤 |
| `core/causal_reasoning.py` | 因果验证器 | 物理定律验证 |

### 2.4 待实现的模型接入脚本

#### 2.4.1 DeepSeek API接入

```python
# 文件名: models/deepseek_client.py
import requests

class DeepSeekClient:
    BASE_URL = "https://api.deepseek.com/chat"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def predict(self, draws, top_k=5):
        prompt = self._build_prompt(draws)
        resp = requests.post(self.BASE_URL, json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是双色球数据分析专家"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }, headers={"Authorization": f"Bearer {self.api_key}"})
        return resp.json()
```

#### 2.4.2 HuggingFace API接入

```python
# 文件名: models/huggingface_client.py
import requests

class HuggingFaceClient:
    BASE_URL = "https://router.huggingface.co/hf-inference/models/"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def predict(self, model_id: str, draws, top_k=5):
        prompt = self._build_prompt(draws)
        resp = requests.post(
            f"{self.BASE_URL}{model_id}/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return resp.json()
```

#### 2.4.3 统一模型调度器

```python
# 文件名: models/unified_model_scheduler.py
# 将所有7个模型统一到orchestrate.py的调度框架下
# 支持:
#   - 本地模型(Ollama)优先
#   - 云端模型(API)兜底
#   - 结果投票融合
#   - 失败自动降级
```

---

## 三、云端守护进程调度计划

### 3.1 调度表

| 频率 | 任务 | 脚本 | 预计耗时 |
|------|------|------|----------|
| 每30分钟 | 数据采集+预测 | `cloud_runner_v2.py` | ~3s |
| 每6小时 | 非随机性检测 | `nonrandomness_detector.py` | ~30s |
| 每天 | 信号融合 | `signal_fusion.py` | ~1s |
| 每周日 | 滚动回测 | `walkforward_backtest_v2.py` | ~5min |
| 每周 | 公式进化 | `autonomous_evolution_v2.py` | ~30min |

### 3.2 CloudStudio沙箱守护进程配置

```bash
# 在CloudStudio沙箱中运行:
cd /c/Users/Administrator/antigravity_cloud
PYTHONIOENCODING=utf-8 uv run python cloud_runner_v2.py --daemon --interval 30
```

---

## 四、分布式协作协议

### 4.1 架构

```
Claude (本地/沙箱)  = 大脑/指挥官
QwenPaw (AgentScope) = 手臂/工人
GitHub Actions      = 离岸算力节点
CloudStudio沙箱     = 云端持续运行节点
```

### 4.2 通信方式

| 方式 | 协议 | 用途 |
|------|------|------|
| 共享文件 | `dist/tasks/` + `dist/results/` | Claude ↔ QwenPaw |
| SSH+SCP | 腾讯云CVM | 云端部署 |
| Telegram Bot | API长轮询 | 远程控制 |
| HTTP API | Ollama/HF/DS | 模型调用 |

---

## 五、时间不存在假说的验证路径

### 5.1 核心逻辑链

```
时间不存在 → 双色球开奖应有隐藏结构 → 统计检验应检测到偏离随机
       ↓                                    ↓
  因果律统一体                          Hurst<0.3, ACF周期, 跨位置MI
       ↓                                    ↓
  所有位置强反持久                     62个偏离信号确认
       ↓                                    ↓
  均值回归成为可操作信号                  "时间不存在"假说获得实证支持
```

### 5.2 已完成的验证

| 检验项 | 结果 | 意义 |
|--------|------|------|
| Hurst指数 | 0.18-0.26 (全部<0.3) | 强反持久=均值回归 |
| 频谱分析 | 7个隐藏周期 | 非随机结构 |
| 跨位置互信息 | 2↔3(0.50), 3↔4(0.51) | 位置间强相关 |
| 非随机性信号 | 62个偏离 | 统计显著 |
| 回测性能 | EnhancedV2红球2.00 | 接近随机baseline |

### 5.3 待完成的验证

| 项目 | 脚本 | 状态 |
|------|------|------|
| GPU蒙特卡洛 | `core/inference.py` | 需安装torch |
| 时间反演对称性 | `nonrandomness_detector.py`(已含) | ✅ 完成 |
| 转移熵分析 | `nonrandomness_detector.py`(已含) | ✅ 完成 |
| 7模型协同投票 | `ai_multi_model_collab.py`(部分) | 需完善DS/HF |
| 长期追踪验证 | 云端守护进程持续运行 | P0待配置 |

---

## 六、文件索引

### 6.1 核心预测引擎
- `orchestrate.py` - 统一编排入口
- `luckcast_antigravity_v1.py` - Luckcast V15 (7维度)
- `enhanced_predictor.py` - Enhanced V2.0 (加权集成)
- `evolution_life.py` - Evolution Life (RF+Spectral)

### 6.2 数据分析
- `nonrandomness_detector.py` - 22项非随机性检测
- `signal_fusion.py` - 信号融合层
- `walkforward_backtest_v2.py` - 前向滚动回测

### 6.3 云端部署
- `cloud_deploy.py` - 腾讯云CVM部署
- `cloud_quick_deploy.py` - 简化部署
- `cloud_runner.py` - 统一编排入口V1.0
- `cloud_runner_v2.py` - 守护进程V2.0
- `cloud_hermes.py` - GitHub Actions Hermes V8.0
- `cloud_info.py` - 云端信息采集

### 6.4 分布式与远程
- `distributed_bridge.py` - 分布式协作协议
- `commander_bot.py` - Telegram Commander Bot
- `full_scheduler.py` - 全自动调度系统

### 6.5 多模型协同
- `ai_multi_model_collab.py` - Gemma4+Gemma2+公式语言
- `core/inference.py` - GPU蒙特卡洛
- `core/causal_reasoning.py` - 因果推理

### 6.6 数据层
- `data_layer.py` - 数据加载/清洗
- `data_updater_v2.py` - 数据采集更新

### 6.7 公式语言
- `formula_lang/grammar.py` - 语法定义
- `formula_lang/evaluator.py` - 评估器
- `formula_lang/mutator.py` - 变异器
- `formula_lang/primitive.py` - 原语定义

### 6.8 自主进化
- `autonomous_evolution.py` - 自主进化V1
- `autonomous_evolution_v2.py` - 自主进化V2
- `backtest_and_evolve.py` - 回测+进化
- `formula_autonomous_evolution.py` - 公式自主进化
- `formula_autonomous_evolution_v2.py` - 公式自主进化V2

### 6.9 Skills目录
- `skills/sentinel_v2.py` - 哨兵监控V2
- `skills/spectrum_observer.py` - 频谱观测器
- `skills/tg_remote_hub.py` - Telegram远程Hub(有bug)

### 6.10 输出文件
- `latest_prediction.json` - 最新预测结果
- `latest_decision.json` - 最新决策(旧格式)
- `nonrandomness_results.json` - 非随机性检测结果
- `analysis_prior.json` - 分析先验
- `position_prior.json` - 位置先验
- `comparison_backtest_v2.json` - 回测对比
- `cloud_info.json` - 云端信息
- `cloud_runner_state.json` - 守护进程状态

### 6.11 模型文件
- `models/evolution_meta.json` - 进化元数据
- `models/rf_red_model.pkl` - 随机森林红球模型
- `models/rf_blue_model.pkl` - 随机森林蓝球模型
