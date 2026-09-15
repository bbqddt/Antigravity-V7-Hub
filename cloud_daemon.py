# -*- coding: utf-8 -*-
"""
Antigravity 云端守护进程 V1.0 — 7×24 持续演进

功能：
1. 定期检查新开奖数据，有新数据时触发演进
2. 每6小时自动运行一轮轻量演进（5代×20公式）
3. 将最佳公式推送到HF Space / GitHub
4. 监控演进健康状态，异常时告警

用法：
    python cloud_daemon.py --daemon          # 守护模式（持续运行）
    python cloud_daemon.py --run             # 单次运行
    python cloud_daemon.py --status          # 查看守护状态
"""
import sys
import os
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
from logging.handlers import RotatingFileHandler
import glob
import os
import math

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

# alert notifier (optional)
try:
    from scripts.alert_notifier import send_telegram, send_email
except Exception:
    def send_telegram(msg: str) -> bool:
        print('[alert_notifier] send_telegram not available')
        return False

    def send_email(subject: str, body: str) -> bool:
        print('[alert_notifier] send_email not available')
        return False

def _configure_logger() -> logging.Logger:
    log_dir = _PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("CloudDaemon")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Rotating file handler: 5 MB per file, keep 7 backups
    try:
        file_handler = RotatingFileHandler(str(log_dir / "cloud_daemon.log"), maxBytes=5 * 1024 * 1024, backupCount=7, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:
        logger.warning(f"日志文件初始化失败，继续使用控制台输出: {exc}")

    return logger


logger = _configure_logger()


def _clean_old_logs(days: int = 30):
    # 删除 logs 目录中早于 days 的日志文件（按修改时间）。
    try:
        log_dir = _PROJECT_ROOT / 'logs'
        if not log_dir.exists():
            return
        cutoff = datetime.now().timestamp() - days * 24 * 3600
        for p in log_dir.glob('*'):
            try:
                if p.is_file():
                    mtime = p.stat().st_mtime
                    if mtime < cutoff:
                        p.unlink()
                        logger.info(f"已清理过期日志: {p.name}")
            except Exception:
                logger.debug(f"跳过无法删除的日志文件: {p}")
    except Exception as e:
        logger.warning(f"清理旧日志出错: {e}")


class CloudDaemon:
    """云端守护进程"""

    def __init__(self):
        self.state_file = _PROJECT_ROOT / "daemon_state.json"
        self.performance_log = _PROJECT_ROOT / "evolution_performance_log.json"
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError('state is not a dict')
                data.setdefault('last_run', None)
                data.setdefault('total_runs', 0)
                data.setdefault('best_formula', None)
                data.setdefault('best_score', 0)
                data.setdefault('health', 'unknown')
                data.setdefault('errors', [])
                data.setdefault('last_notify', None)
                return data
        except Exception:
            return {
                'last_run': None,
                'total_runs': 0,
                'best_formula': None,
                'best_score': 0,
                'health': 'unknown',
                'errors': [],
                'last_notify': None,
            }

    def _save_state(self):
        # 确保必要字段存在，避免 KeyError
        self.state.setdefault('total_runs', 0)
        self.state.setdefault('errors', [])
        self.state['last_run'] = datetime.now().isoformat()
        self.state['total_runs'] = int(self.state.get('total_runs', 0)) + 1
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def check_data_update(self) -> bool:
        """检查是否有新开奖数据"""
        csv_path = _PROJECT_ROOT / 'data' / 'lottery_history.csv'
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                last_issue = lines[-1].split(',')[0] if len(lines) > 1 else ''
                current_time = datetime.fromtimestamp(csv_path.stat().st_mtime)

                # 如果上次运行距今超过24小时，且CSV有更新，则触发演进
                if not self.state.get('last_run'):
                    return True  # 首次运行

                last_run = datetime.fromisoformat(self.state['last_run'])
                hours_since_last = (datetime.now() - last_run).total_seconds() / 3600

                if hours_since_last >= 6:  # 每6小时检查一次
                    return True
        except Exception as e:
            logger.error(f"检查数据失败: {e}")
        return False

    def run_evolution(self, generations: int = 5, population_size: int = 20) -> Dict:
        """运行一轮演进"""
        logger.info(f"\n{'='*60}")
        logger.info(f"  云端守护进程 — 启动演进 ({generations}代 × {population_size}公式)")
        logger.info(f"{'='*60}")

        start = time.time()

        try:
            # 运行公式演进引擎
            result = subprocess.run(
                [
                    sys.executable,
                    str(_PROJECT_ROOT / 'formula_evolution.py'),
                    '--run',
                    '--generations', str(generations),
                    '--population', str(population_size),
                ],
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3600,
                cwd=str(_PROJECT_ROOT),
            )

            elapsed = time.time() - start

            # 读取性能日志
            perf = {}
            if self.performance_log.exists():
                try:
                    with open(self.performance_log, 'r', encoding='utf-8') as f:
                        perf = json.load(f)
                except Exception:
                    logger.exception('读取性能日志失败')

            # 保护性处理 stdout/stderr，避免 None 或编码问题
            stdout_text = result.stdout if (hasattr(result, 'stdout') and result.stdout) else ''
            stderr_text = result.stderr if (hasattr(result, 'stderr') and result.stderr) else ''
            try:
                stdout_lines = str(stdout_text).splitlines()[-20:]
            except Exception:
                stdout_lines = []

            status = {
                'success': result.returncode == 0,
                'elapsed_seconds': round(elapsed, 2),
                'stdout_lines': stdout_lines,
                'stderr': stderr_text.strip(),
                'best_formula': perf.get('best_formula'),
                'best_score': perf.get('best_combined_score'),
                'best_hits': perf.get('best_avg_hits'),
                'best_brier': perf.get('best_avg_brier'),
                'beats_random': perf.get('beats_random'),
                'total_generations': perf.get('total_generations'),
                'time_per_generation': perf.get('time_per_generation'),
            }

            if status['success']:
                logger.info(f"✅ 演进完成: {elapsed:.1f}s")
                logger.info(f"   最佳公式: {status['best_formula']}")
                try:
                    logger.info(f"   综合评分: {status['best_score']:.4f}")
                except Exception:
                    pass
                try:
                    logger.info(f"   平均命中: {status['best_hits']:.3f}")
                except Exception:
                    pass
                self.state['best_formula'] = status.get('best_formula')
                self.state['best_score'] = status.get('best_score')
                self.state['health'] = 'healthy'
            else:
                logger.error(f"❌ 演进失败: {status['stderr'][:200]}")
                self.state['health'] = 'error'
                self.state.setdefault('errors', [])
                self.state['errors'].append({
                    'time': datetime.now().isoformat(),
                    'error': status['stderr'][:500],
                })
                # 只保留最近10个错误
                self.state['errors'] = self.state['errors'][-10:]

                try:
                    subject = 'Antigravity 守护 — 演进失败'
                    message = f"演进失败: elapsed={status['elapsed_seconds']}s\nstderr={status['stderr'][:1000]}\nstdout_lines={status['stdout_lines'][-5:]}"
                    notified = self._notify(subject, message)
                    logger.info(f"[通知] 演进失败告警发送结果: {notified}")
                except Exception:
                    logger.exception('告警发送过程中出错')

            self._save_state()
            return status

        except subprocess.TimeoutExpired:
            logger.error("演进超时（>3600s）")
            self.state['health'] = 'timeout'
            try:
                subject = 'Antigravity 守护 — 演进超时'
                message = f"演进超时: generations={generations}, population={population_size}"
                self._notify(subject, message)
            except Exception:
                logger.exception('超时告警发送失败')
            self._save_state()
            return {'success': False, 'error': 'timeout'}
        except Exception as e:
            logger.error(f"演进异常: {e}")
            self.state['health'] = 'error'
            try:
                subject = 'Antigravity 守护 — 演进异常'
                message = f"演进异常: {str(e)}"
                self._notify(subject, message)
            except Exception:
                logger.exception('异常告警发送失败')
            self._save_state()
            return {'success': False, 'error': str(e)}

    def push_to_github(self) -> bool:
        """推送最新结果到GitHub（如果有git仓库）"""
        git_dir = _PROJECT_ROOT / '.git'
        if not git_dir.exists():
            return False

        try:
            result = subprocess.run(
                ['git', 'add', '.'],
                capture_output=True, text=True, timeout=30,
                cwd=str(_PROJECT_ROOT),
            )
            if result.returncode != 0:
                return False

            result = subprocess.run(
                ['git', 'commit', '-m', f'auto-update: evolution gen{datetime.now().strftime("%Y%m%d-%H%M")}'],
                capture_output=True, text=True, timeout=30,
                cwd=str(_PROJECT_ROOT),
            )
            # 尝试push（可能没有远程仓库）
            subprocess.run(
                ['git', 'push'],
                capture_output=True, text=True, timeout=30,
                cwd=str(_PROJECT_ROOT),
            )
            return True
        except:
            return False

    def _notify(self, subject: str, message: str) -> bool:
        """尝试发送告警，优先 Telegram，其次 Email。"""
        ok = False
        try:
            ok = send_telegram(message)
            if ok:
                logger.info("通知: Telegram 发送成功")
                self.state['last_notify'] = {
                    'method': 'telegram',
                    'subject': subject,
                    'message': message[:200],
                    'time': datetime.now().isoformat(),
                }
                return True
            logger.warning('通知: Telegram 未成功发送，尝试 Email')
        except Exception as e:
            logger.warning(f"通知: Telegram 调用失败: {e}")

        try:
            ok = send_email(subject, message)
            if ok:
                logger.info("通知: Email 发送成功")
                self.state['last_notify'] = {
                    'method': 'email',
                    'subject': subject,
                    'message': message[:200],
                    'time': datetime.now().isoformat(),
                }
                return True
            logger.warning('通知: Email 未成功发送')
        except Exception as e:
            logger.warning(f"通知: Email 调用失败: {e}")

        self.state['last_notify'] = {
            'method': 'none',
            'subject': subject,
            'message': message[:200],
            'time': datetime.now().isoformat(),
        }
        return False

    def health_check(self) -> Dict:
        """系统健康检查"""
        checks = {}

        # 1. 数据文件
        csv_path = _PROJECT_ROOT / 'data' / 'lottery_history.csv'
        checks['data_file'] = csv_path.exists()
        if csv_path.exists():
            size_kb = csv_path.stat().st_size / 1024
            checks['data_size_kb'] = round(size_kb, 1)

        # 2. 评估器
        try:
            from formula_lang.evaluator_v3 import FormulaEvaluatorV3
            ev = FormulaEvaluatorV3()
            checks['evaluator_v3'] = True
            checks['baseline_brier'] = ev.RED_BRIER_BASELINE
        except:
            checks['evaluator_v3'] = False

        # 3. 原语数量
        try:
            from formula_lang.primitive import get_default_primitives
            prims = get_default_primitives()
            checks['primitive_count'] = len(prims)
        except:
            checks['primitive_count'] = 0

        # 4. 一致性检查
        try:
            from consistency_checker import ConsistencyChecker
            checker = ConsistencyChecker()
            ok = checker.check_all()
            checks['consistency'] = ok
        except:
            checks['consistency'] = False

        # 5. 磁盘空间
        try:
            import shutil
            total, used, free = shutil.disk_usage(_PROJECT_ROOT.parent)
            checks['disk_free_gb'] = round(free / (1024**3), 1)
        except:
            checks['disk_free_gb'] = -1

        # 6. 上次演进时间
        checks['last_run'] = self.state.get('last_run')
        checks['total_runs'] = self.state.get('total_runs', 0)

        # 7. 最近告警时间
        last_notify = self.state.get('last_notify')
        if last_notify and isinstance(last_notify, dict):
            checks['last_notify_time'] = last_notify.get('time')
            checks['last_notify_method'] = last_notify.get('method')
        else:
            checks['last_notify_time'] = None
            checks['last_notify_method'] = None

        # 总体健康
        checks['overall_healthy'] = all([
            checks['data_file'],
            checks['evaluator_v3'],
            checks['consistency'],
            checks['primitive_count'] >= 36,
        ])

        return checks

    def show_status(self):
        """显示守护进程状态"""
        health = self.health_check()
        print("\n" + "=" * 60)
        print("  云端守护进程状态")
        print("=" * 60)
        print(f"  总体健康: {'✅ OK' if health['overall_healthy'] else '❌ FAIL'}")
        print(f"  数据文件: {'✅' if health['data_file'] else '❌'} ({health.get('data_size_kb', '?')} KB)")
        print(f"  评估器V3.2: {'✅' if health['evaluator_v3'] else '❌'}")
        print(f"  基线Brier: {health.get('baseline_brier', '?'):.6f}")
        print(f"  原语数量: {health['primitive_count']}")
        print(f"  一致性: {'✅' if health['consistency'] else '❌'}")
        print(f"  磁盘剩余: {health.get('disk_free_gb', '?')} GB")
        print(f"  总运行次数: {health['total_runs']}")
        print(f"  上次运行: {health['last_run'] or '从未'}")
        print(f"  历史最佳: {self.state.get('best_formula', '无')} (score={self.state.get('best_score', 0):.4f})")
        errors = self.state.get('errors', [])
        if errors:
            print(f"  最近错误:")
            for e in errors[-3:]:
                print(f"    - {e.get('time', '')}: {e.get('error', '')[:80]}")
        print("=" * 60)

    def run_once(self):
        """单次运行"""
        logger.info("云端守护进程 — 单次运行模式")
        status = self.run_evolution(generations=5, population_size=20)
        self.push_to_github()
        self.show_status()

    def run_daemon(self):
        """守护模式 — 持续运行

        改进点：加入启动时的旧日志清理，以及异常时的指数退避重试（上限10分钟）。
        """
        logger.info("云端守护进程 — 守护模式启动")
        logger.info("  检查间隔: 每6小时")
        logger.info("  演进参数: 5代 × 20公式")
        logger.info("  按 Ctrl+C 停止\n")

        # 每次启动先清理旧日志（保留最近30天）
        _clean_old_logs(days=30)

        backoff = 60  # 初始异常等待 60s
        while True:
            try:
                # 检查是否需要演进
                if self.check_data_update():
                    logger.info("触发演进...")
                    status = self.run_evolution(generations=5, population_size=20)
                    self.push_to_github()
                else:
                    logger.info("无需演进（距上次运行<6小时）")

                # 成功一次后重置 backoff
                backoff = 60

                # 等待6小时（分段睡眠以便响应中断）
                total_seconds = 6 * 3600
                interval = 30
                for _ in range(int(total_seconds / interval)):
                    time.sleep(interval)
                    logger.info("  [heartbeat] 守护进程运行中...")

            except KeyboardInterrupt:
                logger.info("\n守护进程停止")
                break
            except Exception as e:
                logger.exception(f"守护进程异常: {e}")
                # 指数退避，最大 600s
                wait = min(backoff, 600)
                logger.info(f"异常后等待 {wait}s 后重试（退避）")
                time.sleep(wait)
                backoff = min(int(backoff * 2), 600)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity 云端守护进程 V1.0")
    parser.add_argument('--daemon', action='store_true', help='守护模式（持续运行）')
    parser.add_argument('--run', '--once', action='store_true', help='单次运行（等同于 --once）')
    parser.add_argument('--status', action='store_true', help='显示状态')
    args = parser.parse_args()

    daemon = CloudDaemon()

    if args.status:
        daemon.show_status()
    elif args.daemon:
        daemon.run_daemon()
    elif args.run:
        daemon.run_once()
    else:
        # 默认：守护模式
        daemon.run_daemon()
