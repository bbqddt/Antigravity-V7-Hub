#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 云端 7x24 守护进程
================================
持续运行公式演化、自动优化、异常恢复、结果推送
"""
import os
import sys
import time
import json
import signal
import subprocess
import threading
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# 容错解码：中文 Windows 下子进程（tasklist / formula_evolution.py 等）常以 GBK 输出，
# 若按 UTF-8 解码会抛 UnicodeDecodeError（出现在 Popen 的 _readerthread 中，无法被调用方 try 捕获）。
# 这里优先 UTF-8，失败回退 GBK，再失败用 replace 兜底，保证绝不崩溃。
def _safe_decode(data: bytes) -> str:
    if not data:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("gbk")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")


PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 全局状态
running = True
current_cycle = 0
last_evolution = None
last_backup = None
last_health_check = None


def setup_logging():
    """配置日志 - 显式指定 UTF-8 编码，避免 Windows GBK 乱码"""
    import logging
    log_file = LOG_DIR / f"cloud_daemon_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 移除所有现有 handler，避免 basicConfig 重复添加
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    
    # 创建 UTF-8 StreamHandler
    stream_handler = logging.StreamHandler(sys.stdout)
    try:
        stream_handler.setStream(sys.stdout)
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    stream_handler.setFormatter(formatter)
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
    
    return logging.getLogger("CloudDaemon")


logger = setup_logging()


class CloudDaemon:
    def __init__(self):
        self.running = True
        self.cycle_count = 0
        self.consecutive_failures = 0
        self.start_time = datetime.now()
        self.config = self.load_config()
        self.evolution_interval = self.config.get("evolution_interval_hours", 6)
        self.backup_interval = self.config.get("backup_interval_hours", 12)
        self.health_check_interval = self.config.get("health_check_minutes", 30)
        self.max_generations_per_cycle = self.config.get("max_generations", 20)
        self.population_size = self.config.get("population_size", 30)
        # 持久化状态（接力必需）：轮次计数与累计运行时长，从 daemon_state.json 恢复
        self.total_runtime = 0.0
        self.last_evolution = None
        self._load_daemon_state()
        
    def load_config(self) -> dict:
        """加载配置"""
        config_file = PROJECT_ROOT / "cloud_daemon_config.json"
        default_config = {
            "evolution_interval_hours": 6,
            "backup_interval_hours": 12,
            "health_check_minutes": 30,
            "max_generations": 20,
            "population_size": 30,
            "auto_restart_on_failure": True,
            "max_consecutive_failures": 3,
            "push_results_to_remote": True,
            "notify_on_best_update": True
        }
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return {**default_config, **json.load(f)}
            except:
                pass
        return default_config
    
    def save_config(self):
        """保存配置"""
        config_file = PROJECT_ROOT / "cloud_daemon_config.json"
        config = {
            "evolution_interval_hours": self.evolution_interval,
            "backup_interval_hours": self.backup_interval,
            "health_check_minutes": self.health_check_interval,
            "max_generations": self.max_generations_per_cycle,
            "population_size": self.population_size,
            "auto_restart_on_failure": True,
            "max_consecutive_failures": 3,
            "push_results_to_remote": True,
            "notify_on_best_update": True
        }
        with open(PROJECT_ROOT / "cloud_daemon_config.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _load_daemon_state(self):
        """从 daemon_state.json 恢复接力状态（轮次计数、累计运行时长）"""
        state_file = PROJECT_ROOT / "daemon_state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding='utf-8'))
                self.cycle_count = data.get("cycle_count", 0)
                self.total_runtime = data.get("total_runtime", 0.0)
                logger.info(f"[STATE] 恢复接力状态: 已完成 {self.cycle_count} 轮, 累计 {self.total_runtime/3600:.1f}h")
            except Exception as e:
                logger.warning(f"[STATE] 读取 daemon_state.json 失败，从 0 开始: {e}")
                self.cycle_count = 0
        else:
            self.cycle_count = 0

    def _persist_daemon_state(self):
        """将接力状态写入 daemon_state.json（供下一轮 Actions run 续跑）"""
        state_file = PROJECT_ROOT / "daemon_state.json"
        try:
            state = {
                "cycle_count": self.cycle_count,
                "total_runtime": self.total_runtime,
                "last_run_end": datetime.now().isoformat()
            }
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            logger.warning(f"[STATE] 写入 daemon_state.json 失败: {e}")

    def _update_luckcast_learning(self):
        """演化轮次结束后：自动获取最新开奖，更新 Luckcast 学习状态"""
        try:
            from data_layer import load_history, get_latest_period
            from luckcast_antigravity_v1 import LearningState, _DIM_NAMES
            
            draws = load_history()
            latest_period = get_latest_period(draws)
            
            # 获取最新一期实际开奖红球
            latest_draw = draws[0]  # load_history 返回倒序
            actual_red = latest_draw.reds
            actual_blue = latest_draw.blue
            
            logger.info(f"[LEARN] 更新 Luckcast 学习状态 (最新期 #{latest_period})")
            
            # 加载学习状态
            state = LearningState.load()
            
            # 计算每个维度的命中贡献
            round_hits = {}
            # 生成当前池中每个维度的候选（复用 predict_v15 内部逻辑）
            from luckcast_antigravity_v1 import DIMENSIONS
            import random
            
            for dim_cls in DIMENSIONS:
                dim_name = dim_cls.name
                dim_rng = random.Random(999 + hash(dim_name))
                # 生成该维度的小规模候选池用于评估
                pool = dim_cls.generate_pool(draws, pool_size=200, rng=dim_rng)
                # 计算该维度候选中的最佳命中数
                best_hit = max((len(set(r) & set(actual_red)) for r, _ in pool), default=0)
                round_hits[dim_name] = best_hit
            
            # 更新学习状态
            state.update(round_hits, actual_red)
            state.save()
            
            logger.info(f"[LEARN] Luckcast 学习状态已更新: {round_hits}")
            
        except Exception as e:
            logger.warning(f"[LEARN] Luckcast 自动学习更新失败: {e}")
    
    def run_evolution_cycle(self) -> dict:
        """运行一轮演化"""
        self.cycle_count += 1
        logger.info(f"[ROCKET] 第 {self.cycle_count} 轮演化开始 (目标: {self.max_generations_per_cycle} 代, 种群 {self.population_size})")

        start_time = time.time()
        try:
            # 运行演化
            result = subprocess.run([
                sys.executable, "formula_evolution.py",
                "--run", "--generations", str(self.max_generations_per_cycle),
                "--population", str(self.population_size)
            ], capture_output=True, timeout=7200, cwd=PROJECT_ROOT, encoding='utf-8', errors='replace')

            elapsed = time.time() - start_time

            if result.returncode == 0:
                # 解析结果
                self.last_evolution = datetime.now()
                self.total_runtime += elapsed
                logger.info("[OK] 第 {} 轮演化完成 (耗时: {:.1f}s)".format(self.cycle_count, elapsed))

                # 提取关键指标并写入结构化日志
                self._write_metrics(self.cycle_count, elapsed)

                # 【新增】自动学习闭环：获取最新开奖实际红球，更新 Luckcast 学习状态
                self._update_luckcast_learning()

                # 持久化接力状态（供下一轮 Actions run 续跑）
                self._persist_daemon_state()

                # 提取关键指标用于返回
                output = result.stdout[-2000:]
                logger.info(f"结果摘要: {output[-500:]}")

                return {
                    "cycle": self.cycle_count,
                    "success": True,
                    "elapsed": elapsed,
                    "timestamp": datetime.now().isoformat(),
                    "output_tail": output[-500:]
                }
            else:
                # 写入完整错误日志供排查
                error_log = LOG_DIR / f"evolution_error_{self.cycle_count}.log"
                with open(error_log, 'w', encoding='utf-8') as f:
                    f.write(f"=== Cycle {self.cycle_count} FAILED ===\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write(f"Return code: {result.returncode}\n")
                    f.write(f"Elapsed: {elapsed:.1f}s\n")
                    f.write(f"=== STDOUT ===\n{result.stdout}\n")
                    f.write(f"=== STDERR ===\n{result.stderr}\n")
                
                logger.error(f"[FAIL] 第 {self.cycle_count} 轮演化失败 (详见 {error_log}): {result.stderr[-500:]}")
                return {
                    "cycle": self.cycle_count,
                    "success": False,
                    "error": result.stderr[-500:],
                    "timestamp": datetime.now().isoformat()
                }

        except subprocess.TimeoutExpired:
            logger.error(f"[TIMEOUT] 第 {self.cycle_count} 轮演化超时 (>2小时)")
            return {"cycle": self.cycle_count, "success": False, "error": "timeout"}
        except Exception as e:
            logger.error(f"[CRASH] 第 {self.cycle_count} 轮演化异常: {e}")
            return {"cycle": self.cycle_count, "success": False, "error": str(e)}
    
    def _write_metrics(self, cycle: int, elapsed: float):
        """写入结构化指标到 JSONL 文件"""
        try:
            hist_file = PROJECT_ROOT / "formula_evolution_history.json"
            if hist_file.exists():
                with open(hist_file, encoding='utf-8') as f:
                    hist = json.load(f)
                
                history = hist.get('history', [])
                if history is None:
                    history = []
                last_gen = history[-1] if history else {}
                
                metric = {
                    "timestamp": datetime.now().isoformat(),
                    "cycle": cycle,
                    "elapsed_seconds": round(elapsed, 1),
                    "total_generations": hist.get('total_generations', 0),
                    "best_formula": hist.get('best_formula', ''),
                    "best_score": hist.get('best_score', 0),
                    "last_generation": last_gen.get('generation', 0),
                    "last_best_score": last_gen.get('best_score', 0),
                    "population_size": self.population_size,
                    "max_generations_per_cycle": self.max_generations_per_cycle,
                    "disk_free_gb": round(shutil.disk_usage(".").free / (1024**3), 1),
                    "uptime_hours": round((datetime.now() - self.start_time).total_seconds() / 3600, 1)
                }
                
                metrics_file = LOG_DIR / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
                with open(metrics_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(metric, ensure_ascii=False) + '\n')
                    
                logger.debug(f"[METRICS] 写入指标: cycle={cycle}, best_score={metric['best_score']}")
                
        except Exception as e:
            logger.warning(f"[WARN] 写入指标失败: {e}")
    
    def backup_results(self):
        """备份结果文件"""
        global last_backup
        logger.info("[SAVE] 备份结果文件...")
        
        backup_dir = PROJECT_ROOT / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_backup = [
            "formula_evolution_history.json",
            "evolution_performance_log.json",
            "best_formula.json",
            "latest_prediction.json",
            "evolution_state_v2.json",
            "enhanced_state.json",
            "cloud_daemon_config.json"
        ]
        
        copied = 0
        for f in os.listdir("."):
            if f.endswith((".json", ".pkl", ".log")) and not f.startswith("."):
                try:
                    import shutil
                    shutil.copy2(f, backup_dir / f)
                    copied += 1
                except:
                    pass
        
        last_backup = datetime.now()
        logger.info("[OK] 备份完成: {} 个文件 -> {}".format(copied, backup_dir))
        
        # 清理旧备份 (保留最近 7 天)
        self.cleanup_old_backups()
    
    def cleanup_old_backups(self):
        """清理旧备份"""
        backup_root = PROJECT_ROOT / "backups"
        if not backup_root.exists():
            return
        
        cutoff = datetime.now() - timedelta(days=7)
        for item in backup_root.iterdir():
            if item.is_dir():
                try:
                    item_time = datetime.fromtimestamp(item.stat().st_mtime)
                    if item_time < cutoff:
                        import shutil
                        shutil.rmtree(item)
                        logger.info("[OK] 清理旧备份: {}".format(item.name))
                except:
                    pass
    
    def health_check(self) -> bool:
        """健康检查 (跨平台)"""
        global last_health_check
        last_health_check = datetime.now()
        
        try:
            # 1. 检查进程 (跨平台)
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist"], capture_output=True
                )
            else:
                result = subprocess.run(
                    ["ps", "aux"], capture_output=True
                )
            # 字节输出 + 容错解码，避免中文 Windows 下 tasklist(GBK) 按 UTF-8 解码崩溃
            processes = _safe_decode(result.stdout)
            
            # 2. 检查磁盘空间
            import shutil
            total, used, free = shutil.disk_usage(".")
            free_gb = free / (1024**3)
            
            if free_gb < 1:
                logger.warning("[WARN] 磁盘空间不足: {:.1f}GB".format(free_gb))
                return False
            
            # 2. 检查关键文件
            key_files = ["formula_evolution.py", "data/lottery_history.csv"]
            for f in key_files:
                if not Path(f).exists():
                    logger.error("[ERROR] 关键文件丢失: {}".format(f))
                    return False
            
            # 检查依赖文件 (requirements.txt 或 requirements_posit.txt)
            if not (Path("requirements.txt").exists() or Path("requirements_posit.txt").exists()):
                logger.warning("[WARN] 未找到 requirements.txt 或 requirements_posit.txt")
            
            logger.info("[OK] 健康检查通过 (磁盘剩余: {:.1f}GB)".format(free_gb))
            return True
            
        except Exception as e:
            logger.error("[ERROR] 健康检查异常: {}".format(e))
            return False
    
    def push_results(self):
        """推送结果到远程 (可选)"""
        logger.info("[PUSH] 推送结果到远程...")
        # 这里可以集成云存储、Webhook 等
        # 示例: 上传到 S3、Google Drive、Webhook 等
        logger.info("[OK] 结果推送完成 (本地模式)")
    
    def run(self):
        """主循环"""
        logger.info("=" * 60)
        logger.info("[OK] Antigravity 云端 7x24 守护进程启动")
        logger.info(f"   演化间隔: {self.evolution_interval} 小时")
        logger.info(f"   备份间隔: {self.backup_interval} 小时")
        logger.info(f"   健康检查: {self.health_check_interval} 分钟")
        logger.info(f"   单轮代数: {self.max_generations_per_cycle}")
        logger.info(f"   种群大小: {self.population_size}")
        logger.info("=" * 60)
        
        self.consecutive_failures = 0
        next_evolution = time.time()
        next_backup = time.time() + self.backup_interval * 3600
        next_health = time.time() + self.health_check_interval * 60

        # 启动时立即运行一次健康检查
        self.health_check()
        
        while self.running:
            now = time.time()
            
            # 1. 定时演化
            if now >= next_evolution:
                result = self.run_evolution_cycle()
                if result.get("success"):
                    self.consecutive_failures = 0
                    self.push_results()
                else:
                    self.consecutive_failures += 1
                    logger.warning(f"[WARN] 连续失败: {self.consecutive_failures}")

                    if self.consecutive_failures >= 3:
                        logger.error("[CRASH] 连续失败 3 次，尝试自动恢复...")
                        self.attempt_recovery()
                
                next_evolution = time.time() + self.evolution_interval * 3600
            
            # 2. 定时备份
            if now >= next_backup:
                self.backup_results()
                next_backup = time.time() + self.backup_interval * 3600
            
            # 3. 健康检查
            if now >= next_health:
                if not self.health_check():
                    logger.error("[CRASH] 健康检查失败，尝试恢复...")
                    self.attempt_recovery()
                next_health = time.time() + self.health_check_interval * 60
            
            # 状态报告 (每小时)
            if self.cycle_count > 0 and self.cycle_count % max(1, int(self.evolution_interval)) == 0:
                self.report_status()
            
            # 休眠
            time.sleep(60)  # 每分钟检查一次

    def run_once(self, max_runtime: int = 19800):
        """单次运行模式（供 GitHub Actions 接力）：连续跑演化直到接近 job 时长上限，然后退出交棒。

        GitHub Actions 单次 job 上限 6 小时，这里默认跑满 5.5h（19800s）即退出，
        由 workflow 在末尾 commit 状态文件并链式触发下一轮，形成近似 7x24 的持续计算。
        """
        logger.info("=" * 60)
        logger.info("[OK] Antigravity 单次运行模式 (run-once)")
        logger.info(f"   目标运行时长: {max_runtime/3600:.1f}h (job 上限 6h，留余量)")
        logger.info(f"   恢复轮次: {self.cycle_count} (累计 {self.total_runtime/3600:.1f}h)")
        logger.info("=" * 60)

        self.health_check()
        deadline = time.time() + max_runtime
        self.consecutive_failures = 0

        while time.time() < deadline:
            result = self.run_evolution_cycle()
            if result.get("success"):
                self.consecutive_failures = 0
                self.push_results()
            else:
                self.consecutive_failures += 1
                logger.warning(f"[WARN] 连续失败: {self.consecutive_failures}")
                if self.consecutive_failures >= self.config.get("max_consecutive_failures", 3):
                    logger.error("[CRASH] 连续失败 3 次，尝试自动恢复...")
                    self.attempt_recovery()
            # 接近截止时不再开新轮，避免被 job 硬杀导致状态不完整
            if deadline - time.time() < 600:
                logger.info("[RUN-ONCE] 剩余时间不足 10 分钟，停止开新轮")
                break

        logger.info(f"[RUN-ONCE] 达到运行时长，退出以交棒下一轮 workflow (共 {self.cycle_count} 轮, {self.total_runtime/3600:.1f}h)")

    def attempt_recovery(self):
        """自动恢复"""
        logger.info("[FIX] 尝试自动恢复...")
        try:
            # 1. 重启 Python 环境（显式 UTF-8 解码，规避中文 Windows GBK 输出崩溃）
            subprocess.run([sys.executable, "-c", "import sys; print('OK')"],
                           check=True, encoding='utf-8', errors='replace')
            
            # 2. 重新加载数据
            from data_layer import load_history
            draws = load_history()
            logger.info(f"[OK] 数据重载成功: {len(draws)} 期")
            
            # 3. 验证核心模块
            from formula_evolution import FormulaEvolutionEngine
            engine = FormulaEvolutionEngine(load_history())
            engine.initialize_population(5)
            logger.info("[OK] 核心模块验证通过")
            
            logger.info("[OK] 自动恢复成功")
            
        except Exception as e:
            logger.error(f"[CRASH] 自动恢复失败: {e}")
    
    def report_status(self):
        """状态报告（每轮演化后调用，含磁盘/连续失败监控）"""
        try:
            free_gb = shutil.disk_usage(".").free / (1024**3)
            uptime_h = (datetime.now() - self.start_time).total_seconds() / 3600
            logger.info("=" * 50)
            logger.info(f"[REPORT] 状态报告")
            logger.info(f"   第 {self.cycle_count} 轮结束 | 运行时长: {uptime_h:.1f}h | 磁盘剩余: {free_gb:.1f}GB | 连续失败: {self.consecutive_failures}")
            logger.info("=" * 50)
        except Exception as e:
            logger.warning(f"[WARN] 状态报告失败: {e}")
    
    def stop(self):
        self.running = False
        logger.info("[STOP] 收到停止信号，正在优雅关闭...")


def signal_handler(signum, frame):
    logger.info(f"收到信号 {signum}")
    daemon.stop()


def main():
    global daemon

    import argparse
    parser = argparse.ArgumentParser(description="Antigravity 7x24 演化守护进程")
    parser.add_argument("--run-once", action="store_true",
                        help="单次运行模式（供 GitHub Actions 接力）：跑满 --max-runtime 后退出交棒")
    parser.add_argument("--max-runtime", type=int, default=19800,
                        help="run-once 模式下的最大运行时长（秒），默认 19800 (5.5h)")
    args = parser.parse_args()

    # 创建守护进程
    daemon = CloudDaemon()
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建 PID 文件
    import tempfile
    pid_file = Path(tempfile.gettempdir()) / "antigravity-cloud_daemon_24x7.pid"
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))
    
    try:
        if args.run_once:
            daemon.run_once(max_runtime=args.max_runtime)
        else:
            daemon.run()
    except KeyboardInterrupt:
        logger.info("收到键盘中断")
    except Exception as e:
        logger.error(f"守护进程异常退出: {e}")
    finally:
        # 清理 PID 文件
        pid_file = Path(tempfile.gettempdir()) / "antigravity-cloud_daemon_24x7.pid"
        if pid_file.exists():
            pid_file.unlink()
        logger.info("守护进程已停止")


    def _update_luckcast_learning(self):
        """演化轮次结束后：自动获取最新开奖，更新 Luckcast V15 学习状态"""
        try:
            from data_layer import load_history, get_latest_period
            from luckcast_antigravity_v1 import LearningState, _DIM_NAMES
            
            draws = load_history()
            latest_period = get_latest_period(draws)
            
            # 获取最新一期实际开奖红球
            latest_draw = draws[0]  # load_history 返回倒序
            actual_red = latest_draw.reds
            actual_blue = latest_draw.blue
            
            logger.info(f"[LEARN] 更新 Luckcast 学习状态 (最新期 #{latest_period})")
            
            # 加载学习状态
            state = LearningState.load()
            
            # 计算每个维度的命中贡献
            round_hits = {}
            # 生成当前池中每个维度的候选（复用 predict_v15 内部逻辑）
            from luckcast_antigravity_v1 import DIMENSIONS
            import random
            
            for dim_cls in DIMENSIONS:
                dim_name = dim_cls.name
                dim_rng = random.Random(999 + hash(dim_name))
                # 生成该维度的小规模候选池用于评估
                pool = dim_cls.generate_pool(draws, pool_size=200, rng=dim_rng)
                # 计算该维度候选中的最佳命中数
                best_hit = max((len(set(r) & set(actual_red)) for r, _ in pool), default=0)
                round_hits[dim_name] = best_hit
            
            # 更新学习状态
            state.update(round_hits, actual_red)
            state.save()
            
            logger.info(f"[LEARN] Luckcast 学习状态已更新: {round_hits}")
            
        except Exception as e:
            logger.warning(f"[LEARN] Luckcast 自动学习更新失败: {e}")


if __name__ == "__main__":
    main()