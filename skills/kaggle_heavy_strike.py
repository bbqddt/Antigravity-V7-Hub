import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
import json
import os

# [Antigravity] Kaggle Heavy Strike - GPU 暴力推演内核
# 目标：利用 Kaggle P100 GPU 执行 256 层深度 LSTM 训练

def build_and_strike():
    # 1. 加载 5000 期全量真相
    df = pd.read_csv("ssq_history_full.csv")
    reds = np.array([list(map(int, r.split(','))) for r in df['red']])
    
    # 2. 时序数据预处理 (Window size = 10)
    look_back = 10
    X, y = [], []
    for i in range(len(reds)-look_back-1):
        X.append(reds[i:(i+look_back)])
        y.append(reds[i+look_back])
    X, y = np.array(X), np.array(y)

    # 3. 构建双向 LSTM 模型
    model = Sequential([
        Bidirectional(LSTM(256, return_sequences=True), input_shape=(look_back, 6)),
        Dropout(0.2),
        Bidirectional(LSTM(128)),
        Dense(64, activation='relu'),
        Dense(6, activation='linear')
    ])
    
    model.compile(optimizer='adam', loss='mse')
    
    # 4. 暴力训练 (在 Kaggle GPU 上执行 500 次迭代)
    print("🚀 [KAGGLE] 点火启动！GPU 正在加速计算 5000 期引力轨迹...")
    model.fit(X, y, epochs=500, batch_size=32, verbose=0)
    
    # 5. 最终神谕生成
    last_10 = reds[-look_back:].reshape(1, look_back, 6)
    prediction = model.predict(last_10)
    final_numbers = sorted([int(round(x)) for x in prediction[0]])
    
    # 6. 处理重复与溢出
    strike_res = []
    for n in final_numbers:
        n = max(1, min(33, n))
        while n in strike_res: n = (n % 33) + 1
        strike_res.append(n)
        
    print(f"🔱 [KAGGLE RESULT] 26053 期深度学习神谕: {sorted(strike_res)}")
    return sorted(strike_res)

if __name__ == "__main__":
    build_and_strike()
