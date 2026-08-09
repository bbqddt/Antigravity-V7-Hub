import streamlit as st
import pandas as pd
import json
import os
import re


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
def find_csv(filename):
    """自动搜索CSV文件"""
    candidates = [
        filename,
        os.path.join('data', filename),
        os.path.join('data', 'data', filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def load_data():
    """加载历史数据和预测数据"""
    history_df = pd.DataFrame()
    preds_df = pd.DataFrame()

    # 加载历史数据
    csv_path = find_csv('lottery_history.csv')
    if csv_path:
        try:
            history_df = pd.read_csv(csv_path)
            # 标准化列名
            history_df.columns = history_df.columns.str.strip()
            if 'id' in history_df.columns:
                history_df['id'] = pd.to_numeric(history_df['id'], errors='coerce')
            elif 'period' in history_df.columns:
                history_df['id'] = pd.to_numeric(history_df['period'], errors='coerce')
        except Exception as e:
            st.error(f"历史数据加载失败: {e}")

    # 加载预测数据
    pred_csv_path = find_csv('latest_predictions.csv')
    if pred_csv_path:
        try:
            preds_df = pd.read_csv(pred_csv_path)
        except Exception as e:
            st.error(f"预测数据加载失败: {e}")

    return history_df, preds_df


history, preds = load_data()

# --- UI 渲染 ---
st.title("ANTIGRAVITY V7 | 核心指挥看板 (V7.1-Rational)")
st.markdown("---")

# 动态模式切换
if not history.empty:
    periods = sorted(history['id'].dropna().unique())
    if periods:
        latest_period = int(periods[-1])
        mode_options = [f"{latest_period - 1} 期 | 实战复盘"]
        if len(periods) > 1:
            mode_options.append(f"{latest_period} 期 | 未来推演")
        mode = st.sidebar.selectbox("🎯 战位选择", mode_options)
        target_id = latest_period - 1 if "复盘" in mode else latest_period
    else:
        mode = "最新期 | 实战复盘"
        target_id = int(history['id'].max()) if 'id' in history.columns else 0
else:
    mode = "等待数据"
    target_id = 0

if history.empty or preds.empty:
    st.warning("⚠️ 等待数据合龙中...")
else:
    # 锁定真实结果
    real_match = history[history['id'] == target_id]

    if real_match.empty:
        st.error(f"❌ 系统未在数据库中发现 {target_id} 期的真实开奖信号！请运行爬虫。")
    else:
        real_row = real_match.iloc[0]
        # 兼容多种列名格式
        real_reds = []
        for i in range(1, 7):
            val = real_row.get(f'r{i}')
            if val is not None:
                real_reds.append(int(val))
            else:
                real_reds = [int(real_row.get(f'red_{i}', 0)) for i in range(1, 7)]
                break
        if not real_reds:
            real_red_str = str(real_row.get('red', ''))
            if real_red_str:
                real_reds = [int(x.strip()) for x in real_red_str.split(',')]
        real_blue = int(real_row.get('b', real_row.get('blue', 0)))

        # 1. 英雄战区
        st.subheader(f"🏁 {target_id} 期 真实战场信号")
        cols = st.columns(7)
        for i, r in enumerate(real_reds):
            cols[i].markdown(f'<div class="ball-red">{r:02d}</div>', unsafe_allow_html=True)
        cols[6].markdown(f'<div class="ball-blue">{real_blue:02d}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. 预测表现对比
        st.subheader("⚔️ 指纹库对抗表现")

        def render_comparison(pred_row, real_reds, real_blue):
            try:
                numbers_str = pred_row.get('numbers', pred_row.get('red', ''))
                parts = numbers_str.split('|')
                p_reds = []
                for x in parts[0].strip().replace("[", "").replace("]", "").split(','):
                    try:
                        p_reds.append(int(x.strip()))
                    except ValueError:
                        pass
                p_blue = int(parts[1].strip()) if len(parts) > 1 else 0
                hit_reds = [r for r in p_reds if r in real_reds]
                hit_blue = (p_blue == real_blue)

                source = pred_row.get('source', pred_row.get('agent', 'Unknown'))
                confidence = pred_row.get('confidence', pred_row.get('score', 'N/A'))

                html = f'<div class="draw-card"><b>[{source}]</b> 置信度: {confidence} <br>'
                for r in p_reds:
                    cls = "ball-red hit" if r in real_reds else "ball-red"
                    html += f'<div class="{cls}">{r:02d}</div>'
                cls_b = "ball-blue hit" if p_blue == real_blue else "ball-blue"
                html += f'<div class="{cls_b}">{p_blue:02d}</div><br><br>'
                html += f'<span class="stat-label">红球击穿: </span><span class="stat-value">{len(hit_reds)}</span>'
                html += '</div>'
                return html
            except Exception as e:
                return f'<div class="draw-card">解析异常: {e}</div>'

        # 显示预测
        col_a, col_b = st.columns(2)
        for i, row in preds.head(10).iterrows():
            target_col = col_a if i % 2 == 0 else col_b
            target_col.markdown(render_comparison(row, real_reds, real_blue), unsafe_allow_html=True)

st.markdown("---")
st.caption("Antigravity V7.1 | Rational Autonomous Engine")
