import streamlit as st
import pandas as pd
import json
import os

# --- 页面配置 ---
st.set_page_config(page_title="Antigravity V7 战位复盘", layout="wide", initial_sidebar_state="collapsed")

# --- 自定义 CSS (Premium 审美) ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .stApp {
        background: radial-gradient(circle at top right, #1a1a2e, #0e1117);
    }
    .draw-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    }
    .ball-red {
        background: radial-gradient(circle at 30% 30%, #ff4b4b, #8b0000);
        color: white;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 8px;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
    }
    .ball-blue {
        background: radial-gradient(circle at 30% 30%, #00aaff, #004488);
        color: white;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 8px;
        box-shadow: 0 4px 15px rgba(0, 170, 255, 0.3);
    }
    .hit {
        border: 2px solid #00ff00 !important;
        box-shadow: 0 0 20px #00ff00 !important;
        transform: scale(1.1);
    }
    .stat-label {
        color: #888;
        font-size: 0.9rem;
    }
    .stat-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #ffd700;
    }
    </style>
""", unsafe_allow_html=True)

# --- 数据引擎 (强化容错) ---
def load_data():
    try:
        history = pd.read_csv("data/ssq_history_full.csv")
        # 强制转换 ID 列为数值，处理可能的字符串碎屑
        history['id'] = pd.to_numeric(history['id'], errors='coerce')
        preds = pd.read_csv("latest_predictions.csv")
        return history, preds
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return pd.DataFrame(), pd.DataFrame()

history, preds = load_data()

# --- UI 渲染 ---
st.title("🛡️ ANTIGRAVITY V7 | 核心指挥看板 (V7.1-Rational)")
st.markdown("---")

# 模式切换
mode = st.sidebar.selectbox("🎯 战位选择", ["036 期 | 实战复盘", "037 期 | 未来推演"])

if history.empty or preds.empty:
    st.warning("⚠️ 等待数据合龙中...")
else:
    if mode == "036 期 | 实战复盘":
        # 锁定 036 期真实结果
        target_id = 2026036
        real_match = history[history['id'] == target_id]
        
        if real_match.empty:
            st.error(f"❌ 系统未在数据库中发现 {target_id} 期的真实开奖信号！请运行爬虫。")
        else:
            real_036 = real_match.iloc[0]
            real_reds = [int(real_036[f'r{i}']) for i in range(1, 7)]
            real_blue = int(real_036['b'])

            # 1. 英雄战区
            st.subheader(f"🏁 {target_id} 期 (昨晚) 真实战场信号")
            cols = st.columns(7)
            for i, r in enumerate(real_reds):
                cols[i].markdown(f'<div class="ball-red">{r:02d}</div>', unsafe_allow_html=True)
            cols[6].markdown(f'<div class="ball-blue">{real_blue:02d}</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 2. 预测表现对比
            st.subheader("⚔️ 十大指纹库对抗表现")

            def render_comparison(pred_row, real_reds, real_blue):
                try:
                    parts = pred_row['numbers'].split('|')
                    p_reds = [int(x) for x in parts[0].strip().replace("[", "").replace("]", "").split(',')]
                    p_blue = int(parts[1].strip())
                    hit_reds = [r for r in p_reds if r in real_reds]
                    hit_blue = (p_blue == real_blue)
                    
                    html = f'<div class="draw-card"><b>[{pred_row["source"]}]</b> 置信度: {pred_row["confidence"]} <br>'
                    for r in p_reds:
                        cls = "ball-red hit" if r in real_reds else "ball-red"
                        html += f'<div class="{cls}">{r:02d}</div>'
                    cls_b = "ball-blue hit" if p_blue == real_blue else "ball-blue"
                    html += f'<div class="{cls_b}">{p_blue:02d}</div><br><br>'
                    html += f'<span class="stat-label">红球击穿: </span><span class="stat-value">{len(hit_reds)}</span>'
                    html += '</div>'
                    return html
                except Exception as e: return f'<div class="draw-card">解析异常: {e}</div>'

            # 仅显示非 037 的预测 (即 036 期)
            p036 = preds[preds['id'] != 2026037]
            col_a, col_b = st.columns(2)
            for i, row in p036.head(10).iterrows():
                target_col = col_a if i % 2 == 0 else col_b
                target_col.markdown(render_comparison(row, real_reds, real_blue), unsafe_allow_html=True)

    else:
        # 037 期预演模式
        st.subheader("🔮 037 期 (下周日) 千万级理智演进推演")
        st.info("💡 **理智判定**：036 为极态偏差，037 锁定**奇数报复性回归 (4:2/5:1)**，重心向 23-33 区间迁移。")
        
        p037 = preds[preds['id'] == 2026037]
        if p037.empty:
            st.warning("⚠️ 037 强化指纹库尚未合龙，请启动 `v7_autonomous_orchestrator.py`。")
        else:
            col_a, col_b = st.columns(2)
            for i, row in p037.iterrows():
                target_col = col_a if i % 2 == 0 else col_b
                parts = row['numbers'].split('|')
                p_reds = [int(x) for x in parts[0].strip().replace("[", "").replace("]", "").split(',')]
                p_blue = int(parts[1].strip())
                
                html = f'<div class="draw-card"><b>[{row["source"]}]</b> 置信度: <span style="color:#00ff00">{row["confidence"]}</span> <br>'
                for r in p_reds:
                    html += f'<div class="ball-red">{r:02d}</div>'
                html += f'<div class="ball-blue">{p_blue:02d}</div>'
                html += '</div>'
                target_col.markdown(html, unsafe_allow_html=True)

st.markdown("---")
st.caption("Antigravity V7.1 | Rational Autonomous Engine | 2026.04.03 Update")
