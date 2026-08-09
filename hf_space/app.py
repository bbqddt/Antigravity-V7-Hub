# -*- coding: utf-8 -*-
"""
Antigravity HF Space — Gradio Web界面
=====================================
展示多AI协同进化引擎的实时状态和预测结果。

用法:
    python app.py
    # 或 HF Spaces 自动运行
"""
import os
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

try:
    import gradio as gr
except ImportError:
    print("[WARN] gradio未安装，跳过Web界面")
    gr = None

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_json_safe(path: str) -> Optional[Dict]:
    """安全读取JSON文件"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_latest_state() -> Dict[str, Any]:
    """获取最新进化状态"""
    state_file = _PROJECT_ROOT / "evolution_state_v20.json"
    best_file = _PROJECT_ROOT / "best_formulas_v19.json"
    top_file = _PROJECT_ROOT / "top_candidates_export.json"

    result = {
        "timestamp": datetime.now().isoformat(),
        "state": load_json_safe(state_file),
        "best_formulas": load_json_safe(best_file),
        "top_candidates": load_json_safe(top_file),
    }
    return result


def format_state_summary(state: Dict) -> str:
    """格式化状态摘要"""
    if not state:
        return "暂无进化数据"

    lines = [
        f"**最后更新**: {state.get('last_updated', '未知')}",
        f"**总周期数**: {state.get('cycle_count', 0)}",
        f"**已生成假设**: {state.get('total_hypotheses_generated', 0)}",
        f"**存活**: {state.get('survived_count', 0)} | 淘汰: {state.get('eliminated_count', 0)}",
        f"**原语数量**: {state.get('n_primitives', 0)}",
    ]
    return "\n".join(lines)


def format_best_formula(best: Dict) -> str:
    """格式化最佳公式信息"""
    if not best or not best.get("best_formula"):
        return "暂无最佳公式"

    bf = best["best_formula"]
    lines = [
        f"**名称**: {bf.get('name', 'N/A')}",
        f"**来源**: {bf.get('source', 'N/A')}",
        f"**Brier Score**: {bf.get('brier_score', bf.get('fitness_score', 'N/A'))}",
        f"**平均命中**: {bf.get('avg_hits', 0):.2f} ± {bf.get('std_hits', 0):.2f}",
        f"**P值**: {bf.get('p_value', 0):.4f}",
        f"**原语**: {', '.join(bf.get('primitive_names', []))}",
        f"**组合方式**: {bf.get('operators', [])[-1] if bf.get('operators') else 'N/A'}",
    ]
    return "\n".join(lines)


def format_survival_pool(pool: list) -> str:
    """格式化存活公式池"""
    if not pool:
        return "暂无存活公式"

    lines = ["| 排名 | 公式名 | Brier Score | 平均命中 | 原语 |",
             "|------|--------|-------------|----------|------|"]

    for i, formula in enumerate(pool[:10], 1):
        name = formula.get("name", "N/A")[:15]
        brier = formula.get("brier_score", formula.get("fitness_score", "N/A"))
        hits = formula.get("avg_hits", 0)
        prims = ", ".join(formula.get("primitives", [])[:3])
        lines.append(f"| {i} | {name} | {brier} | {hits:.2f} | {prims} |")

    return "\n".join(lines)


def format_evolution_history(history: list) -> str:
    """格式化进化历史"""
    if not history:
        return "暂无历史记录"

    lines = ["| 代数 | 最佳Brier | 平均命中 | 时间 |",
             "|------|-----------|----------|------|"]

    for h in history[-10:]:  # 最近10代
        gen = h.get("generation", "?")
        fit = h.get("best_fitness", h.get("best_brier", "?"))
        hits = h.get("best_avg_hits", "?")
        ts = h.get("timestamp", "")[:19]
        lines.append(f"| {gen} | {fit:.4f} | {hits:.2f} | {ts} |")

    return "\n".join(lines)


def run_evolution() -> str:
    """触发进化循环（简化版）"""
    engine_path = _PROJECT_ROOT / "multi_ai_evolution_engine.py"

    if not engine_path.exists():
        return "❌ 进化引擎文件不存在: multi_ai_evolution_engine.py"

    return f"""✅ 进化引擎就绪: {engine_path}

运行命令:
```bash
cd {_PROJECT_ROOT}
python multi_ai_evolution_engine.py --generations 10 --candidates 15
```

或在HF Spaces中配置定时触发器自动运行。

**当前状态**:
- 本地引擎: ✅ 代码就绪
- GitHub Actions: ⏳ 等待推送工作流
- HF Spaces: ✅ 本页面
- 腾讯云: ⏳ 等待公网IP
"""


def create_ui() -> gr.Blocks:
    """创建Gradio界面"""
    if gr is None:
        return None

    with gr.Blocks(title="Antigravity V17 - 多AI协同进化引擎") as demo:
        gr.Markdown("""
        # 🚀 Antigravity V17 — 多AI协同进化引擎

        **三大支柱架构 · 云端分布式计算 · 实时可视化**

        ---
        """)

        with gr.Tabs():
            # Tab 1: 实时状态
            with gr.Tab("📊 实时状态"):
                with gr.Row():
                    with gr.Column():
                        state_btn = gr.Button("刷新状态", variant="primary")
                        state_md = gr.Markdown(value="点击按钮加载最新状态...")

                    with gr.Column():
                        best_btn = gr.Button("查看最佳公式", variant="secondary")
                        best_md = gr.Markdown(value=format_best_formula(load_json_safe(str(_PROJECT_ROOT / "best_formulas_v19.json"))))

                with gr.Row():
                    pool_btn = gr.Button("存活公式池", variant="secondary")
                    pool_md = gr.Markdown(value=format_survival_pool(
                        load_json_safe(str(_PROJECT_ROOT / "evolution_state_v20.json"))
                        .get("survival_pool", [])
                        if load_json_safe(str(_PROJECT_ROOT / "evolution_state_v20.json"))
                        else []
                    ))

                state_btn.click(get_latest_state, outputs=[state_md])
                pool_btn.click(lambda s: format_survival_pool(s.get("survival_pool", [])),
                              inputs=[state_md], outputs=[pool_md])

            # Tab 2: 进化历史
            with gr.Tab("📈 进化历史"):
                history_btn = gr.Button("加载进化历史")
                history_md = gr.Markdown(value=format_evolution_history([]))

                def load_history():
                    state = load_json_safe(str(_PROJECT_ROOT / "evolution_state_v20.json"))
                    history = state.get("evolution_history", []) if state else []
                    return format_evolution_history(history)

                history_btn.click(load_history, outputs=[history_md])

            # Tab 3: 预测结果
            with gr.Tab("🎯 最新预测"):
                pred_btn = gr.Button("查看预测")
                pred_md = gr.Markdown(value="""
                ### 当前预测引擎输出

                来自 `best_formulas_v19.json` 中的数学引擎预测：
                """)

                def show_predictions():
                    best = load_json_safe(str(_PROJECT_ROOT / "best_formulas_v19.json"))
                    if not best:
                        return "暂无预测数据"

                    math_preds = best.get("math_engine_predictions", {})
                    lines = []
                    for engine, preds in math_preds.items():
                        reds = preds.get("red", [])
                        blue = preds.get("blue", [])
                        lines.append(f"**{engine}**: 红球 {reds} + 蓝球 {blue}")

                    return "\n".join(lines) if lines else "暂无预测"

                pred_btn.click(show_predictions, outputs=[pred_md])

            # Tab 4: 启动进化
            with gr.Tab("🔥 启动进化"):
                ev_btn = gr.Button("启动进化循环", variant="primary")
                ev_md = gr.Markdown(value="点击下方按钮触发进化循环...")
                ev_btn.click(run_evolution, outputs=[ev_md])

            # Tab 5: 系统信息
            with gr.Tab("ℹ️ 系统信息"):
                gr.Markdown("""
                ### 项目架构

                | 组件 | 状态 | 说明 |
                |------|------|------|
                | 公式语言 Pillar 1 | ✅ 完整 | 33个原语，6大类别 |
                | 策略框架 Pillar 2 | ✅ 完整 | 假设生成→验证→进化 |
                | LLM创新 Pillar 3 | ✅ 完整 | Gemini/OpenRouter/Gemma2 |
                | Multi-AI引擎 V19 | ✅ 完成 | 10代×15候选=195公式 |
                | GitHub Actions | ⏳ 待推送 | 定时触发进化 |
                | HF Spaces | ✅ 本页面 | Web可视化 |
                | 腾讯云 CVM | ⏳ 等IP | 长期守护进程 |

                ### 关键指标

                - 随机基线 Brier Score: ~0.139
                - 当前最佳: 0.1723 (比随机差24%)
                - 核心瓶颈: 所有原语在频率统计空间内搜索
                - 下一步方向: 卡方物理偏差检测 / 贝叶斯先验更新 / 新信号源探索
                """)

    return demo


if __name__ == "__main__":
    demo = create_ui()
    if demo:
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True,
        )
    else:
        print("Gradio未安装，请运行: pip install gradio")
