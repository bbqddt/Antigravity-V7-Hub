# -*- coding: utf-8 -*-
"""
Kaggle Heavy Strike — LSTM 深度学习推演内核

修复：
1. 路径改为相对项目根目录
2. 期号动态计算
3. TensorFlow 缺失时优雅降级
"""
import numpy as np
import pandas as pd
import json
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build_and_strike(target_period=None):
    # 1. 加载历史数据
    csv_path = _PROJECT_ROOT / "data" / "lottery_history.csv"
    if not csv_path.exists():
        print("❌ 未找到历史数据文件")
        return None

    df = pd.read_csv(str(csv_path))
    reds = np.array([list(map(int, r.split(','))) for r in df['red']])

    if len(reds) < 20:
        print("❌ 数据量不足（需要至少 20 期）")
        return None

    # 2. 时序数据预处理
    look_back = 10
    X, y = [], []
    for i in range(len(reds) - look_back - 1):
        X.append(reds[i:(i + look_back)])
        y.append(reds[i + look_back])
    X, y = np.array(X), np.array(y)

    # 3. 构建双向 LSTM 模型
    try:
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional

        model = Sequential([
            Bidirectional(LSTM(256, return_sequences=True), input_shape=(look_back, 6)),
            Dropout(0.2),
            Bidirectional(LSTM(128)),
            Dense(64, activation='relu'),
            Dense(6, activation='linear')
        ])

        model.compile(optimizer='adam', loss='mse')

        print("🚀 [LSTM] 点火启动！正在训练 500 期引力轨迹...")
        model.fit(X, y, epochs=500, batch_size=32, verbose=0)

        last_10 = reds[-look_back:].reshape(1, look_back, 6)
        prediction = model.predict(last_10, verbose=0)
        final_numbers = sorted([int(round(x)) for x in prediction[0]])
    except ImportError:
        print("⚠️ TensorFlow 未安装，使用频率统计降级方案...")
        # 降级：基于最近 look_back 期的频率
        recent = reds[-look_back:]
        freq = {}
        for r in recent:
            for n in r:
                freq[n] = freq.get(n, 0) + 1
        final_numbers = sorted([n for n, _ in sorted(freq.items(), key=lambda x: -x[1])[:6]])
        while len(final_numbers) < 6:
            final_numbers.append(len(final_numbers) + 1)
        final_numbers = sorted(set(final_numbers))[:6]

    # 4. 处理重复与溢出
    strike_res = []
    for n in final_numbers:
        n = max(1, min(33, n))
        while n in strike_res:
            n = (n % 33) + 1
        strike_res.append(n)

    # 动态期号
    if target_period is None:
        target_period = int(df['period'].iloc[0]) + 1

    print(f"🔱 [RESULT] Period {target_period} LSTM Prediction: {sorted(strike_res)}")
    return sorted(strike_res)


if __name__ == "__main__":
    build_and_strike()
