import os
import logging
from pathlib import Path

# 使用最新推荐的 SDK 包
from google import genai

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

class LLMStrategyEvolver:
    """使用 Gemini 分析日志并重写过滤策略的自主演进器"""
    
    def __init__(self, log_path="execution.log", strategy_dir="strategies", model_name="gemini-2.5-pro"):
        self.log_path = Path(log_path)
        self.strategy_file = Path(strategy_dir) / "default_filter.py"
        self.model_name = model_name
        
        # 1. 初始化 Google AI 客户端
        # 注意: 需先安装官方库 pip install google-genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("未找到 GEMINI_API_KEY 环境变量！请在终端执行: set GEMINI_API_KEY=your_api_key_here")
            raise ValueError("Missing GEMINI_API_KEY")
            
        self.client = genai.Client(api_key=api_key)
        
    def read_context(self):
        """读取最近的回测结果、报错与当前策略代码"""
        context = ""
        
        # 读取日志最后 50 行以获取环境反馈
        if self.log_path.exists():
            with open(self.log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_logs = "".join(lines[-50:])
                context += "=== 最近的系统运行日志与回测结果 ===\n" + recent_logs + "\n\n"
        
        # 读取当前代码作为修改基座
        if self.strategy_file.exists():
            with open(self.strategy_file, 'r', encoding='utf-8') as f:
                code = f.read()
                context += "=== 当前策略代码 (strategies/default_filter.py) ===\n" + code + "\n"
                
        return context

    def generate_new_strategy(self, context: str):
        """请求 Gemini 阅读上下文并生成更优的核心代码"""
        prompt = f"""
        你是一个精通生成式 AI 与统计算法的系统重构代理。
        以下是系统的回测日志/报错信息和当前的过滤策略代码。
        
        任务限制与目标：
        1. 仔细分析日志中的准确度得分或报错 Traceback。
        2. 据此优化或修复 `filter_logic(results)` 函数，使其具备更强的过滤泛化性。
        3. 请直接输出符合 Python 语法的完整重构代码文本，包含注释。
        4. 你的输出将被写入生产环境文件，绝对不要包含 Markdown 格式的 ```python 或 ``` 标记，绝对不要包含额外说明，只允许输出单纯的 Python 源码内容。
        
        {context}
        """
        
        logger.info(f"请求 {self.model_name} 审阅日志并进行策略演进计算...")
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        
        # 极简清洗，防止大模型偷偷加上 markdown 标记
        new_code = response.text
        if new_code.startswith("```python"):
            new_code = new_code[9:]
        if new_code.startswith("```"):
            new_code = new_code[3:]
        if new_code.endswith("```"):
            new_code = new_code[:-3]
            
        return new_code.strip()

    def apply_new_strategy(self, new_code: str):
        """将新生成的代码写入 strategies/ 目录完成闭环"""
        if not new_code or "def filter_logic" not in new_code:
            logger.error("生成的代码格式不满足安全要求 (缺乏目标函数)，已拒绝覆写。")
            return False
            
        logger.warning("正在强制覆写策略代码 strategies/default_filter.py ...")
        with open(self.strategy_file, 'w', encoding='utf-8') as f:
            f.write(new_code + "\n")
        logger.info("代码重写完成！系统自我进化闭环已生效。")
        return True

    def run_evolution(self):
        try:
            context = self.read_context()
            if not context:
                logger.warning("未找到有效上下文(代码或日志)，中断演进。")
                return
                
            new_code = self.generate_new_strategy(context)
            self.apply_new_strategy(new_code)
            
        except Exception as e:
            logger.error(f"演进过程发生异常: {e}")

if __name__ == "__main__":
    evolver = LLMStrategyEvolver()
    evolver.run_evolution()
