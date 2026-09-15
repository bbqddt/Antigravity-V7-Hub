import torch
import logging
import time

logger = logging.getLogger(__name__)

class StrategyEngine:
    """本地策略引擎：极速张量化蒙特卡洛过滤"""
    
    def __init__(self, weights: torch.Tensor):
        # 扩展权重以接受环境维度（如气压、温度，此处演示对齐长度）
        # 如果从云端拉取的权重是 [7, 1]，我们需要根据输入调整
        self.weights = weights.flatten()
        # 将张量移动到可用设备 (GPU/CPU)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.weights = self.weights.to(self.device)

    def monte_carlo_filter(self, iterations: int = 10000000):
        """
        千万级张量化蒙特卡洛引擎
        完全摒弃 Python 循环，通过大规模张量运算实现极致算力
        """
        logger.info(f"Starting Vectorized Monte Carlo filter with {iterations} iterations on {self.device}...")
        start_time = time.time()
        
        # 为了避免内存溢出，我们将一千万次分割为 10 个 batch
        batch_size = 1000000
        num_batches = max(1, iterations // batch_size)
        
        global_best_score = -float('inf')
        global_best_pick = None

        for _ in range(num_batches):
            # 1. 批量生成蓝球 (1-16)
            blues = torch.randint(1, 17, (batch_size, 1), device=self.device, dtype=torch.float32)
            
            # 2. 批量生成红球 (1-33，不能重复)
            # PyTorch 没有直接的高效无放回多行采样，我们可以给一个大随机矩阵 argsort
            rand_matrix = torch.rand((batch_size, 33), device=self.device)
            # argsort 会得到 0-32 的索引，加上 1 得到 1-33 的号码
            reds_indices = torch.argsort(rand_matrix, dim=1)[:, :6] + 1
            # 对红球排序，保持统一格式
            reds, _ = torch.sort(reds_indices, dim=1)
            
            # 3. 拼接红蓝球组成基础特征矩阵 (batch_size, 7)
            picks = torch.cat([reds.to(torch.float32), blues], dim=1)
            
            # (如果张量需要和更宽的权重对齐，例如加上环境因子的伪权重预测)
            if self.weights.size(0) > 7:
                mock_entropy = torch.randn((batch_size, self.weights.size(0) - 7), device=self.device)
                picks = torch.cat([picks, mock_entropy], dim=1)
            
            # 4. 张量化评分矩阵全量相乘
            # picks: (batch_size, N), weights: (N,) -> dot product
            scores = torch.matmul(picks, self.weights)
            
            # 5. 寻找本批次最高分
            max_score, max_idx = torch.max(scores, dim=0)
            
            if max_score.item() > global_best_score:
                global_best_score = max_score.item()
                global_best_pick = picks[max_idx][:7]  # 仅提取号码部分
                
        elapsed = time.time() - start_time
        logger.info(f"Tensorized Monte Carlo Finished in {elapsed:.4f}s. Performance: {iterations/elapsed:.0f} iters/sec.")
        logger.info(f"Max score achieved: {global_best_score:.4f}")
        
        best_reds = [int(x) for x in global_best_pick[:6].tolist()]
        best_blue = int(global_best_pick[6].item())
        
        return f"R:{best_reds} B:{best_blue}"
