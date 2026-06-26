class PIDController:
    """
    PID 控制器：用于动态调整预测模型的算法权重。
    利用比例（Proportional）、积分（Integral）、微分（Derivative）机制，
    基于开奖真实结果与预测结果的误差进行闭环反馈（Self-Evolution）。
    """
    
    def __init__(self, kp: float, ki: float, kd: float):
        self.kp = kp  # 比例系数：对当前误差的响应
        self.ki = ki  # 积分系数：消除系统的稳态误差
        self.kd = kd  # 微分系数：预测误差变化趋势，减少震荡
        self.prev_error = 0.0
        self.integral = 0.0

    def compute(self, target: float, current_val: float) -> float:
        """
        计算权重调整量
        :param target: 目标值（例如：期望命中率或完美预测距离）
        :param current_val: 实际观测值（当前模型回测的准确度）
        :return: 输出调整量，用于更新模型权重
        """
        error = target - current_val
        
        # 积分累积
        self.integral += error
        
        # 微分计算误差变化率
        derivative = error - self.prev_error
        
        # PID 公式
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        
        # 记录本次误差供下次使用
        self.prev_error = error
        
        return output

    def reset(self):
        """重置内部状态，在开启新一轮完整训练周期时调用"""
        self.prev_error = 0.0
        self.integral = 0.0
