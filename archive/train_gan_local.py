import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from pathlib import Path
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# 基础模型结构 (对齐 models/gan_adversary.py)
class Discriminator(nn.Module):
    def __init__(self, input_dim=7):
        super(Discriminator, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.LeakyReLU(0.2),
            nn.Linear(64, 32),
            nn.LeakyReLU(0.2),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    def forward(self, x):
        return self.net(x)

def train_self_healing():
    logger.info("⚡ [HEAL] 启动理智自愈训练流程...")
    
    # 1. 载入历史数据
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    data_path = _PROJECT_ROOT / "data" / "lottery_history.csv"
    if not data_path.exists():
        logger.error(f"❌ 找不到历史库: {data_path}")
        return

    df = pd.read_csv(str(data_path))

    # 兼容多种列名格式
    if 'red' in df.columns and 'blue' in df.columns:
        # 标准格式: period,red,blue,date
        reds_list = []
        blues_list = []
        for _, row in df.iterrows():
            try:
                reds = [int(x.strip()) for x in str(row['red']).split(',')]
                blue = int(row['blue'])
                if len(reds) == 6:
                    reds_list.append(reds)
                    blues_list.append(blue)
            except (ValueError, TypeError):
                continue
        real_data = np.array(reds_list + [blues_list[:len(reds_list)][i:i+1] for i in range(len(reds_list))], dtype=np.float32).reshape(-1, 7) if reds_list else np.zeros((0, 7), dtype=np.float32)
        # 更简洁的方式
        all_rows = []
        for r, b in zip(reds_list, blues_list):
            all_rows.append(r + [b])
        real_data = np.array(all_rows, dtype=np.float32)
    else:
        # 旧格式: r1-r6, b
        core_cols = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'b']
        for c in core_cols:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=core_cols)
        real_data = df[core_cols].values.astype(np.float32)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # 修正：移除可能的极端异常值
    real_data = np.clip(real_data, 1, 33)
    real_tensor = torch.tensor(real_data).to(device)
    num_samples = real_tensor.size(0)
    
    # 2. 初始化判别器
    discriminator = Discriminator(input_dim=7).to(device)
    optimizer = torch.optim.Adam(discriminator.parameters(), lr=0.002)
    criterion = nn.BCELoss()
    
    # 3. 闭环对抗训练
    epochs = 2000
    batch_size = 32
    
    logger.info(f"🧬 [TRAIN] 正在针对 {num_samples} 条实战特征执行 {epochs} 阶拟合...")
    
    for epoch in range(epochs):
        # 批量训练
        idx = torch.randperm(num_samples)[:batch_size]
        real_batch = real_tensor[idx] / 33.0
        
        # 构造伪随机样本 (1-33)
        fake_reds = torch.sort(torch.randint(1, 34, (batch_size, 6)).float(), dim=1)[0]
        fake_blues = torch.randint(1, 17, (batch_size, 1)).float()
        fake_batch = torch.cat([fake_reds, fake_blues], dim=1).to(device) / 33.0
        
        optimizer.zero_grad()
        
        # 真实数据拟合 (增加 NaN 容错)
        real_preds = discriminator(real_batch)
        real_preds = torch.nan_to_num(real_preds, nan=0.5)
        real_preds = torch.clamp(real_preds, 1e-7, 1.0 - 1e-7)
        real_loss = criterion(real_preds, torch.ones_like(real_preds))
        
        # 伪随机数据拟合
        fake_preds = discriminator(fake_batch)
        fake_preds = torch.nan_to_num(fake_preds, nan=0.5)
        fake_preds = torch.clamp(fake_preds, 1e-7, 1.0 - 1e-7)
        fake_loss = criterion(fake_preds, torch.zeros_like(fake_preds))
        
        total_loss = real_loss + fake_loss
        total_loss.backward()
        optimizer.step()
        
        if epoch % 500 == 0:
            logger.info(f"Epoch {epoch}/{epochs} | D-Loss: {total_loss.item():.4f}")
            
    # 4. 固化模型
    model_save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "ssq_model_v985.pt")
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    torch.save(discriminator.state_dict(), model_save_path)
    
    logger.info(f"✅ [HEAL] 0 字节模型已自愈修复！模型固化至: {model_save_path}")

if __name__ == "__main__":
    train_self_healing()
