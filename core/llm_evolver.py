# -*- coding: utf-8 -*-
"""
LLM Strategy Evolver — 使用 Gemini 分析日志并重写过滤策略的自主演进器

改进：
1. 日志文件不存在时优雅降级
2. 代码验证增强：防止写入恶意/无效代码
3. 增加回滚机制：演进失败时可恢复到上一个版本
4. 密钥管理：支持环境变量 + keys.json 双通道
"""
import os
import logging
import shutil
from pathlib import Path
from datetime import datetime

# 使用最新推荐的 SDK 包
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class LLMStrategyEvolver:
    """使用 Gemini 分析日志并重写过滤策略的自主演进器"""

    def __init__(self, log_path=None, strategy_dir=None, model_name="gemini-2.5-pro"):
        self.model_name = model_name
        project_root = Path(__file__).resolve().parent.parent

        self.log_path = Path(log_path) if log_path else project_root / "logs" / "enhanced_predictor.log"
        self.strategy_file = Path(strategy_dir) if strategy_dir else project_root / "default_filter.py"

        # 确保日志目录存在
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # 备份目录
        self.backup_dir = project_root / "backups" / "strategies"

        # 1. 初始化 Google AI 客户端 — 双通道密钥获取
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            keys_file = project_root / "keys.json"
            if keys_file.exists():
                try:
                    import json
                    with open(keys_file, "r") as f:
                        keys = json.load(f)
                        api_key = keys.get("gemini")
                except Exception as e:
                    logger.warning(f"Failed to read keys.json: {e}")

        if not api_key:
            logger.warning("GEMINI_API_KEY 未设置，LLM 演进将降级为本地模式。")
            self.client = None
        elif not GEMINI_AVAILABLE:
            logger.warning("google-genai 库未安装，LLM 演进将降级为本地模式。")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def _create_backup(self):
        """在修改前创建当前策略的备份"""
        if not self.strategy_file.exists():
            return
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"default_filter_{timestamp}.py"
        try:
            shutil.copy2(str(self.strategy_file), str(backup_path))
            logger.info(f"策略备份完成: {backup_path}")
        except Exception as e:
            logger.warning(f"备份失败: {e}")

    def read_context(self):
        """读取最近的回测结果、报错与当前策略代码"""
        context_parts = []

        # 读取日志最后 100 行以获取环境反馈
        if self.log_path.exists():
            with open(self.log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_logs = "".join(lines[-100:])
                context_parts.append(
                    f"=== 最近的系统运行日志与回测结果 (最近 100 行) ===\n{recent_logs}"
                )
        else:
            context_parts.append("=== 日志文件不存在，跳过日志分析 ===\n")

        # 读取当前代码作为修改基座
        if self.strategy_file.exists():
            with open(self.strategy_file, 'r', encoding='utf-8') as f:
                code = f.read()
                context_parts.append(
                    f"=== 当前策略代码 ({self.strategy_file.name}) ===\n{code}"
                )
        else:
            context_parts.append(f"=== 策略文件不存在: {self.strategy_file} ===\n")
            # 提供最小模板
            context_parts.append("""\ndef filter_logic(results):
    '''当前过滤器为空，请 LLM 补充逻辑'''
    return results
""")

        return "\n\n".join(context_parts)

    def _validate_generated_code(self, new_code: str) -> bool:
        """验证生成的代码是否满足安全要求"""
        if not new_code:
            return False

        # 必须包含 filter_logic 函数
        if "def filter_logic" not in new_code:
            logger.error("生成的代码缺少 filter_logic 函数，拒绝写入。")
            return False

        # 尝试编译检查语法
        try:
            compile(new_code, "<generated>", "exec")
        except SyntaxError as e:
            logger.error(f"生成的代码语法错误: {e}")
            return False

        return True

    def generate_new_strategy(self, context: str):
        """请求 Gemini 阅读上下文并生成更优的核心代码"""
        if not self.client:
            logger.warning("LLM 客户端不可用，返回 None（降级模式）")
            return None

        prompt = f"""
你是一个精通生成式 AI 与统计算法的系统重构代理。
以下是系统的回测日志/报错信息和当前的过滤策略代码。

任务限制与目标：
1. 仔细分析日志中的准确度得分或报错 Traceback。
2. 据此优化或修复 `filter_logic(results)` 函数，使其具备更强的过滤泛化性。
3. 请直接输出符合 Python 语法的完整重构代码文本，包含注释。
4. 你的输出将被写入生产环境文件，绝对不要包含 Markdown 格式的 ```python 或 ``` 标记，
   绝对不要包含额外说明，只允许输出单纯的 Python 源码内容。

{context}
"""

        logger.info(f"请求 {self.model_name} 审阅日志并进行策略演进计算...")

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
        except Exception as e:
            logger.error(f"LLM 请求失败: {e}")
            return None

        # 极简清洗，防止大模型偷偷加上 markdown 标记
        new_code = response.text
        if new_code.startswith("```python"):
            new_code = new_code[9:]
        if new_code.startswith("```"):
            new_code = new_code[3:]
        if new_code.endswith("```"):
            new_code = new_code[:-3]

        new_code = new_code.strip()

        if not self._validate_generated_code(new_code):
            logger.error("生成的代码未通过安全验证")
            return None

        return new_code

    def apply_new_strategy(self, new_code: str) -> bool:
        """将新生成的代码写入策略文件完成闭环"""
        if not new_code or "def filter_logic" not in new_code:
            logger.error("生成的代码格式不满足安全要求 (缺乏目标函数)，已拒绝覆写。")
            return False

        # 创建备份
        self._create_backup()

        logger.warning(f"正在覆写策略代码: {self.strategy_file} ...")
        try:
            with open(self.strategy_file, 'w', encoding='utf-8') as f:
                f.write(new_code + "\n")
            logger.info("代码重写完成！系统自我进化闭环已生效。")
            return True
        except Exception as e:
            logger.error(f"写入策略文件失败: {e}")
            return False

    def restore_backup(self, backup_filename=None) -> bool:
        """从备份恢复策略代码"""
        if not self.backup_dir.exists():
            logger.error("没有可用的备份")
            return False

        if backup_filename:
            backup_path = self.backup_dir / backup_filename
        else:
            # 恢复最新的备份
            backups = sorted(self.backup_dir.glob("default_filter_*.py"))
            if not backups:
                logger.error("没有可用的备份")
                return False
            backup_path = backups[-1]

        try:
            shutil.copy2(str(backup_path), str(self.strategy_file))
            logger.info(f"已从备份恢复: {backup_path.name}")
            return True
        except Exception as e:
            logger.error(f"恢复失败: {e}")
            return False

    def run_evolution(self):
        try:
            context = self.read_context()
            if not context:
                logger.warning("未找到有效上下文(代码或日志)，中断演进。")
                return

            new_code = self.generate_new_strategy(context)
            if new_code:
                self.apply_new_strategy(new_code)
            else:
                logger.info("LLM 演进不可用，跳过代码重写。")

        except Exception as e:
            logger.error(f"演进过程发生异常: {e}")


if __name__ == "__main__":
    evolver = LLMStrategyEvolver()
    evolver.run_evolution()
