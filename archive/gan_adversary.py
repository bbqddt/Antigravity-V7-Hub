import torch
import torch.nn as nn
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Discriminator(nn.Module):
    """
    双色球真实分布判别器 (GAN Discriminator)
    目标是区分“历史真实开奖组合”与“蒙特卡洛纯随机生组合”
    """
    def __init__(self, input_dim=7):
        super(Discriminator, self).__init__()
        # 简单的 MLP 模型
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

class GANAdversary:
    """管理对抗策略的接口"""
    def __init__(self, model_dir="models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.discriminator = Discriminator(input_dim=7).to(self.device)
        self.optimizer = torch.optim.Adam(self.discriminator.parameters(), lr=0.001)
        self.criterion = nn.BCELoss()

    def train_step(self, real_data: torch.Tensor, fake_data: torch.Tensor):
        """
        进行一次简易对抗性监督训练:
        - real_data: 从历史库真实抓取的特征矩阵 (带环境因子时可能是9维，此处依然针对核心7维度进行区分)
        - fake_data: 由引擎生成的完全随机组合
        """
        self.optimizer.zero_grad()
        
        # 确保只使用前7维进行号码分布裁决
        real_input = real_data[:, :7].to(self.device)
        fake_input = fake_data[:, :7].to(self.device)

        # 真实数据标签设为 1
        real_labels = torch.ones(real_input.size(0), 1).to(self.device)
        real_loss = self.criterion(self.discriminator(real_input), real_labels)
        
        # 伪随机数据标签设为 0
        fake_labels = torch.zeros(fake_input.size(0), 1).to(self.device)
        fake_loss = self.criterion(self.discriminator(fake_input), fake_labels)
        
        d_loss = real_loss + fake_loss
        d_loss.backward()
        self.optimizer.step()
        
        logger.info(f"Adversarial training step completed. D-Loss: {d_loss.item():.4f}")
        return d_loss.item()
        
    def evaluate(self, candidate_tensor: torch.Tensor):
        """评估生成样本像“真实的”开奖分布的概率"""
        with torch.no_grad():
            candidate_input = candidate_tensor[:, :7].to(self.device)
            score = self.discriminator(candidate_input)
        return score.item()
