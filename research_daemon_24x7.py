#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 7x24 公式研究与精进引擎
======================================
集成 LLM 分析、自动优化、异常恢复、持续演化
"""
import os
import sys
import time
import json
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

import logging
log_file = LOG_DIR / f"research_daemon_{datetime.now().strftime('%Y%m%d')}.log"

# 移除所有现有 handler，显式构建 UTF-8 handlers
root_logger = logging.getLogger()
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

# UTF-8 StreamHandler
stream_handler = logging.StreamHandler(sys.stdout)
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
stream_handler.setFormatter(formatter)

# UTF-8 FileHandler
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)

root_logger.setLevel(logging.INFO)
root_logger.addHandler(stream_handler)
root_logger.addHandler(file_handler)

logger = logging.getLogger("ResearchDaemon")


class FormulaResearchDaemon:
    """7x24 公式研究与精进守护进程"""
    
    def __init__(self):
        self.running = True
        self.config = self.load_config()
        self.cycle_count = 0
        self.research_count = 0
        self.start_time = datetime.now()
        self.last_best_score = -1
        self.consecutive_failures = 0
        
    def load_config(self) -> dict:
        config_file = PROJECT_ROOT / "research_daemon_config.json"
        default = {
            "evolution_cycle_hours": 6,
            "research_cycle_hours": 12,
            "health_check_minutes": 30,
            "backup_hours": 12,
            "evolution_generations": 20,
            "evolution_population": 30,
            "research_depth": "deep",  # quick/normal/deep
            "auto_apply_llm_suggestions": True,
            "max_consecutive_failures": 3,
            "target_score_improvement": 0.01,
            "min_improvement_cycles": 3
        }
        config_file = PROJECT_ROOT / "research_daemon_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return {**default, **json.load(f)}
            except:
                pass
        return default
    
    def save_state(self, state: dict):
        state_file = PROJECT_ROOT / "research_daemon_state.json"
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    
    def load_state(self) -> dict:
        state_file = PROJECT_ROOT / "research_daemon_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def run_evolution_cycle(self) -> dict:
        """运行演化周期"""
        logger.info(f"[ROCKET] 演化周期开始 (代数: {self.config['evolution_generations']}, 种群: {self.config['evolution_population']})")
        
        try:
            result = subprocess.run([
                sys.executable, "formula_evolution.py",
                "--run", "--generations", str(self.config['evolution_generations']),
                "--population", str(self.config['evolution_population'])
            ], capture_output=True, text=True, timeout=7200, cwd=PROJECT_ROOT, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                return {"success": True, "output": result.stdout[-2000:]}
            else:
                return {"success": False, "error": result.stderr[-1000:]}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_llm_research(self) -> dict:
        """运行 LLM 深度研究"""
        logger.info(f"[BRAIN] LLM 深度研究开始 (模式: {self.config['research_depth']})")
        
        try:
            from llm_formula_loop import run_llm_formula_loop
            from data_layer import load_history
            
            draws = load_history()
            generations = 5 if self.config['research_depth'] == 'quick' else 10
            interval = 2 if self.config['research_depth'] == 'quick' else 3
            
            result = run_llm_formula_loop(draws, generations=generations, analysis_interval=interval)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_and_apply_suggestions(self) -> dict:
        """检查并应用 LLM 建议"""
        logger.info("[LIST] 检查 LLM 建议并应用...")
        
        state = self.load_state()
        suggestions = state.get("pending_suggestions", [])
        
        if not suggestions:
            return {"applied": 0, "message": "无待应用建议"}
        
        applied = 0
        for suggestion in suggestions:
            if suggestion.get("type") == "new_primitive":
                # 这里可以集成到 primitive 创建流程
                logger.info(f"📝 发现新原语建议: {suggestion.get('name')}")
                applied += 1
        
        if applied > 0:
            state["pending_suggestions"] = []
            self.save_state(state)
        
        return {"applied": applied}
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 检查关键文件
            for f in ["formula_evolution.py", "data/lottery_history.csv"]:
                if not Path(f).exists():
                    logger.error(f"关键文件丢失: {f}")
                    return False
            
            # 检查磁盘
            import shutil
            free_gb = shutil.disk_usage(".").free / (1024**3)
            if free_gb < 1:
                logger.warning(f"磁盘空间不足: {free_gb:.1f}GB")
                return False
            
            # 检查核心模块
            from formula_evolution import FormulaEvolutionEngine
            from data_layer import load_history
            engine = FormulaEvolutionEngine(load_history())
            engine.initialize_population(2)
            
            return True
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
    
    def backup_state(self):
        """备份状态"""
        backup_dir = PROJECT_ROOT / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for f in PROJECT_ROOT.glob("*.json"):
            try:
                import shutil
                shutil.copy2(f, backup_dir / f.name)
            except:
                pass
        
        # 清理旧备份
        self.cleanup_old_backups()
    
    def cleanup_old_backups(self):
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
                except:
                    pass
    
    def report_progress(self):
        """进度报告"""
        uptime = datetime.now() - datetime.fromisoformat(self.start_time.isoformat()) if isinstance(self.start_time, datetime) else timedelta(0)
        logger.info("=" * 50)
        logger.info(f"[REPORT] 进度报告")
        logger.info(f"   运行时长: {uptime}")
        logger.info(f"   演化周期: {self.config['evolution_cycle_hours']}h")
        logger.info(f"   研究周期: {self.config['research_cycle_hours']}h")
        logger.info(f"   连续失败: {self.consecutive_failures}")
        logger.info("=" * 50)
    
    def run(self):
        """主循环"""
        logger.info("=" * 60)
        logger.info("[BRAIN] Antigravity 7x24 公式研究守护进程启动")
        logger.info(f"   演化周期: {self.config['evolution_cycle_hours']}h")
        logger.info(f"   研究周期: {self.config['research_cycle_hours']}h")
        logger.info(f"   研究深度: {self.config['research_depth']}")
        logger.info("=" * 60)
        
        # 初始化
        self.backup_state()
        
        next_evolution = time.time()
        next_research = time.time() + self.config['research_cycle_hours'] * 3600
        next_backup = time.time() + self.config['backup_hours'] * 3600
        next_health = time.time() + self.config['health_check_minutes'] * 60
        next_report = time.time() + 3600  # 1小时报告一次
        
        while self.running:
            now = time.time()
            
            # 1. 定时演化
            if now >= next_evolution:
                logger.info(f"[CYCLE] 触发演化周期")
                result = self.run_evolution_cycle()
                if result.get("success"):
                    self.consecutive_failures = 0
                    # 检查是否有分数提升
                    # 这里可以解析 result["output"] 获取最新分数
                else:
                    self.consecutive_failures += 1
                    logger.warning(f"[WARN] 演化失败，连续失败: {self.consecutive_failures}")
                    
                    if self.consecutive_failures >= self.config['max_consecutive_failures']:
                        self.attempt_recovery()
                
                next_evolution = now + self.config['evolution_cycle_hours'] * 3600
            
            # 2. 定时 LLM 研究
            if now >= next_research:
                logger.info(f"[BRAIN] 触发 LLM 深度研究")
                result = self.run_llm_research()
                if result.get("success") and self.config['auto_apply_llm_suggestions']:
                    self.check_and_apply_suggestions()
                next_research = now + self.config['research_cycle_hours'] * 3600
            
            # 3. 定时备份
            if now >= next_backup:
                self.backup_state()
                next_backup = now + self.config['backup_hours'] * 3600
            
            # 4. 健康检查
            if now >= next_health:
                if not self.health_check():
                    logger.error("健康检查失败，尝试恢复")
                    self.attempt_recovery()
                next_health = now + self.config['health_check_minutes'] * 60
            
            # 5. 进度报告
            if now >= next_report:
                self.report_progress()
                next_report = now + 3600
            
            time.sleep(60)  # 每分钟检查
    
    def attempt_recovery(self):
        """自动恢复"""
        logger.info("[FIX] 尝试自动恢复...")
        try:
            # 重新验证核心模块
            from data_layer import load_history
            draws = load_history()
            logger.info(f"数据重载: {len(draws)} 期")
            
            from formula_evolution import FormulaEvolutionEngine
            engine = FormulaEvolutionEngine(draws)
            engine.initialize_population(3)
            logger.info("核心模块验证通过")
            
            self.consecutive_failures = 0
            logger.info("[OK] 自动恢复成功")
        except Exception as e:
            logger.error(f"恢复失败: {e}")
    
    def stop(self):
        self.running = False
        logger.info("[STOP] 收到停止信号")


def main():
    # 信号处理
    daemon = FormulaResearchDaemon()
    
    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}")
        daemon.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # PID 文件
    pid_file = LOG_DIR / "research_daemon.pid"
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))
    
    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("收到键盘中断")
    except Exception as e:
        logger.error(f"守护进程异常: {e}")
    finally:
        if pid_file.exists():
            pid_file.unlink()
        logger.info("研究守护进程已停止")


if __name__ == "__main__":
    main()