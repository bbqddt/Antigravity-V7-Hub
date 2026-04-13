import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from pathlib import Path
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
    
    # 1. 载入 448 期全量历史
    data_path = "e:/享中/data/ssq_history_full.csv"
    if not Path(data_path).exists():
        logger.error(f"❌ 找不到历史库: {data_path}")
        return
    
    # 强制清理：确保只有红球 1-6 和 蓝球列，且移除所有空值或损坏行
    df = pd.read_csv(data_path)
    # 确保列名存在并转为数值
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
    model_save_path = "models/ssq_model_v985.pt"
    torch.save(discriminator.state_dict(), model_save_path)
    
    logger.info(f"✅ [HEAL] 0 字节模型已自愈修复！模型固化至: {model_save_path}")

if __name__ == "__main__":
    train_self_healing()
