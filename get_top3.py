import asyncio
from core.cloud_sync import CloudRelay
from core.inference import StrategyEngine
from core.causal_reasoning import CausalAnalyzer
from models.gan_adversary import GANAdversary
import torch

async def get_top_3():
    relay = CloudRelay()
    feature_tensor = await relay.prepare_tensors()
    weights = await relay.download_model_weights()
    engine = StrategyEngine(weights)
    analyzer = CausalAnalyzer()
    adversary = GANAdversary()
    
    # 模拟外部环境感知到了极寒天气 (-8.5度)
    simulated_temp = -8.5
    print(f"### 当前物理环境输入: 极寒天气 (entropy_temp = {simulated_temp}) ###\n")
    
    candidates = []
    
    # 执行多次张量采样寻优
    for _ in range(50):
        # 每次抽取10万次，总计500万次
        recs = engine.monte_carlo_filter(iterations=100000)
        red_str = recs.split(' B:')[0].replace('R:', '')
        blue_str = recs.split(' B:')[1]
        
        causal_report = analyzer.evaluate_causality(red_str, blue_str, entropy_temp=simulated_temp)
        causal_mult = causal_report.get("confidence_multiplier", 0.5)
        
        reds = [int(x.strip()) for x in red_str.replace("[", "").replace("]", "").split(',')]
        blue = int(blue_str)
        
        if feature_tensor.shape[0] > 0:
            mock_tensor = feature_tensor[0:1].clone()
        else:
            mock_tensor = torch.randn(1, 9)
            
        mock_tensor[0, :7] = torch.tensor(reds + [blue], dtype=torch.float32)
        
        gan_score = adversary.evaluate(mock_tensor)
        
        if causal_report["status"] == "passed":
            current_score = gan_score * 0.8 + 0.2 * causal_mult
            if gan_score > 0.8:
                current_score += 0.1
        else:
            current_score = gan_score * causal_mult
            
        current_score = min(float(current_score), 0.998)
        candidates.append((current_score, recs, causal_report))
        
    # 排序取前 3
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    print("=== 高置信度闭环推演 Top 3 (极寒效应激活) ===")
    for i, (score, recs, report) in enumerate(candidates[:3]):
        print(f"[{i+1}] 置信度得分: {score:.4f}")
        print(f"    组合: {recs}")
        print(f"    因果状态: {report['status']}")
        if report['warnings']:
            print(f"    警告: {report['warnings']}")
        print(f"    微观指标: {report['metrics']}\n")

if __name__ == "__main__":
    asyncio.run(get_top_3())
