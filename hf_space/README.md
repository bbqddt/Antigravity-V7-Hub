# Antigravity V17 — 多AI协同进化引擎

> 中国福利彩票双色球预测系统 · 三大支柱架构 · 云端分布式计算

## 架构

**三大支柱整合：**
1. **公式语言** (Formula Language) — 33个数学原语，6大类别（时序/关系/结构/频谱/几何/混沌）
2. **自研策略框架** (Self-Proposing Strategies) — 假设生成→验证→存活/淘汰→进化
3. **LLM驱动创新** (LLM Innovation) — Gemini/OpenRouter/Gemma2 协同提议新原语

## 核心能力

- **多AI协同**: Luckcast V15 + Enhanced Predictor + 33原语共识 + LLM模型
- **公式进化**: 每代生成100+候选公式，精英保留+变异+交叉
- **Walk-Forward验证**: Brier Score评估概率校准质量
- **云端分布式**: GitHub Actions定时进化 + HF Spaces可视化 + 腾讯云守护进程

## 实时状态

点击下方 **"启动进化循环"** 按钮运行一轮进化（10代 × 15候选 = 195公式）。

结果保存在 `evolution_state_v20.json` 和 `top_candidates_export.json`。

## 数据

- 历史开奖: 3,472期 (03001 ~ 26075)
- 规则: 红球6个(1-33) + 蓝球1个(1-16)
- 随机基线 Brier Score: ~0.139

## 部署

```bash
pip install huggingface_hub gradio
python deploy_hf.py --space <username>/Antigravity --token $HF_TOKEN
```
