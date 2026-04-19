# 帮我写一个反重力系统的平衡控制逻辑
import math
from typing import List, Dict

class AntiGravityPIDBalancer:
    """
    反重力系统 PID 平衡控制逻辑 (Antigravity PID Equilibrium Controller)
    基于多模型输出的“引力坍缩”现象，引入 PID 控制机制对系统的模型偏移进行闭环调节。
    """
    
    def __init__(self, target_equilibrium: float = 8.57, kp: float = 0.618, ki: float = 0.1, kd: float = 0.2):
        self.target_equilibrium = target_equilibrium
        self.kp = kp  # 比例系数，提供向目标收敛的主要“反重力引力”
        self.ki = ki  # 积分系数，消除长期离散导致的稳态偏差
        self.kd = kd  # 微分系数，在预测大幅度剧烈震荡时提供“阻尼”缓和
        self.prev_error = 0.0
        self.integral = 0.0

    def calculate_collapse_force(self, predictions: List[float]) -> float:
        """
        计算多模型集群预估间的方差和离散度，量化系统的“引力坍缩力度”。
        """
        if not predictions:
            return 0.0
        
        mean_pred = sum(predictions) / len(predictions)
        variance = sum((p - mean_pred) ** 2 for p in predictions) / len(predictions)
        return math.sqrt(variance)

    def apply_pid_balance_correction(self, base_state: float, force: float) -> float:
        """
        进行反重力场 PID 内核计算，得到向 8.57 平衡态补偿纠偏后的推力。
        """
        error = self.target_equilibrium - base_state
        
        self.integral += error
        derivative = error - self.prev_error
        
        # PID 三项合力计算；引入离散扰动力 (force) 作为额外的系统摩擦或偏差参考
        pid_compensation = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative) - (force * 0.1)
        
        self.prev_error = error
        
        return base_state + pid_compensation

    def aggregate_system_state(self, model_outputs: Dict[str, float]) -> float:
        """
        执行系统闭环计算：汇流所有模块数据，通过 PID 平衡环得出最终的基位。
        """
        if not model_outputs:
            return 0.0
            
        preds = list(model_outputs.values())
        collapse_force = self.calculate_collapse_force(preds)
        
        base_state = sum(preds) / len(preds)
        
        # 将原始预测态推入 PID 控制器约束下进行收敛计算
        equilibrium_prediction = self.apply_pid_balance_correction(base_state, collapse_force)
        
        return equilibrium_prediction


class AntiGravityCoreEngine:
    """
    反重力控制系统核心算法 (Antigravity Core Engine)
    结合 PID 平衡器，利用引力坍缩原理，在混沌矩阵（例如多模型的原始预测数据）中寻找稳定“奇点”（Singularity）。
    """

    def __init__(self, dimensions: int = 6):
        self.dimensions = dimensions  # 目标维度（如双色球的 6 个红球域）
        self.balancer = AntiGravityPIDBalancer(target_equilibrium=8.57)

    def compute_quantum_repulsion(self, val_a: float, val_b: float) -> float:
        """
        计算数值间的“排斥力”（反重力势能）。
        当模型预测结果极端趋同时（过拟合征兆），反推产生强烈的斥力，保持动态寻找。
        """
        distance = abs(val_a - val_b)
        if distance < 1e-4:
            return 100.0  # 防止除 0，且产生强排斥力
        return 1.0 / (distance ** 2)

    def search_singularity(self, data_matrix: List[List[float]]) -> List[float]:
        """
        核心反重力推演逻辑：解析多维度特征数据矩阵，计算并输出系统的最终“奇点”（最佳预测态）。
        :param data_matrix: 多模型的给出的序列预测，形如 [[1.1, 2.3...], [1.2, 2.1...]]
        """
        final_coordinates = []
        
        # 逐维度进行高维塌陷计算
        for dim in range(self.dimensions):
            # 将该维度的各个模型预测抽取为一个集群
            dim_predictions = [row[dim] for row in data_matrix if len(row) > dim]
            
            if not dim_predictions:
                final_coordinates.append(0.0)
                continue
                
            # 1. 估量集群内部的发散与趋同情况，计算群体排斥偏压
            repulsion_field = 0.0
            n_models = len(dim_predictions)
            for i in range(n_models):
                for j in range(i + 1, n_models):
                    repulsion_field += self.compute_quantum_repulsion(dim_predictions[i], dim_predictions[j])
            
            # 2. 借由上方构建好的反重力 PID 环稳定预测基位
            model_outputs = {f"model_{i}": p for i, p in enumerate(dim_predictions)}
            equilibrium_node = self.balancer.aggregate_system_state(model_outputs)
            
            # 3. 产生奇点：利用排斥场形成的张力（经过对数降噪后的力场）微调最终汇聚点
            # 偏置量与 PID 基值结合，成为当前维度的唯一预测“奇点”
            damped_bias = math.log1p(repulsion_field) * 0.005
            singularity_point = equilibrium_node + damped_bias
            
            final_coordinates.append(round(singularity_point, 4))
            
        return final_coordinates

if __name__ == "__main__":
    # 模拟 3 个预测模型给出的红球预测矩阵 (假设只预测 6 个红球)
    # 每个子数组代表一个模型给出的预测序列
    mock_matrix = [
        [1.1, 5.2, 12.0, 15.3, 22.1, 33.0],  # 模型 1
        [1.3, 5.0, 11.8, 16.0, 22.0, 32.5],  # 模型 2
        [1.1, 5.1, 12.1, 15.5, 23.0, 33.1],  # 模型 3（与前两者有轻微发散和重合）
    ]
    
    print("[Status] Antigravity Core Engine: 初始化完成")
    engine = AntiGravityCoreEngine(dimensions=6)
    
    print("[Action] 正在注入预测矩阵数据，触发高维塌陷与反重力场域...")
    result_singularity = engine.search_singularity(mock_matrix)
    
    print("====================================")
    print("-> 寻获的高维预测奇点 (Singularity):")
    print(result_singularity)
    print("====================================")

import urllib.request
import json
import time

class OmniProxyClient:
    """
    无限 API 中转站通信客户端核心
    负责对接本地无限 API 池 (http://127.0.0.1:3000)，解决 400 Bad Request 和超时崩溃问题。
    带有指数退避重试和标准的自适应 Payload 构建。
    """
    def __init__(self, endpoint: str = "http://127.0.0.1:3000/v1/chat/completions"):
        self.endpoint = endpoint

    def request_model_node(self, prompt: str, model_name: str = "gpt-4", max_retries: int = 3) -> str:
        """
        向中转站发出预测指令。
        内置标准的 OpenAI 请求体结构，避免因为缺漏 model 或 messages 字段引发 400 报错。
        """
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a causal prediction node in the Antigravity lottery system."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        data = json.dumps(payload).encode('utf-8')
        
        # 必须带上正确的 header 否则会被 node 端 proxy 误报 400
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'sk-proj-9v4kiuZvZNKz9TMS2FXol995xDYMknQQWP6BxOld_ov0T_esDoFFZXbe8lln2C68NXX41oY6vT3BlbkFJ75zHaylDLGWUclzyfUbA7P8RJ3frbmKlBWZo8cemkl688GVjol_NvdDhLs2oaB4yz4Fea90EA' # 按需修改，如果中转站免鉴权则无关紧要
        }
        
        req = urllib.request.Request(self.endpoint, data=data, headers=headers)
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"[OmniProxy] 发起第 {attempt} 次节点呼叫至 {self.endpoint}...")
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_body = json.loads(response.read().decode('utf-8'))
                    return res_body.get('choices', [{}])[0].get('message', {}).get('content', '')
            except urllib.error.HTTPError as e:
                response_err = e.read().decode('utf-8') if e.fp else str(e)
                print(f"  -> [报错] 节点拒绝 ({e.code}): 中转站返回了 HTTPError: {response_err}")
                if e.code == 400:
                    print("  -> [*警告*] 400 Error 意味着发向中转栈的数据格式不被接受。请确认你的无限中转 API 脚本支持标准的 OpenAI 结构！")
            except Exception as e:
                print(f"  -> [超时/掉线] 网络错误 ({type(e).__name__}): {e}，准备进行切换重试...")
                
            time.sleep(1.5 * attempt) # 指数延迟退避
            
        return "ERROR: PROXY_EXHAUSTED_OR_FAILED"

# 下面是结合使用示范
# if __name__ == "__main__":
#     client = OmniProxyClient()
#     print(client.request_model_node("请输出一句简单的系统上线确认语。"))