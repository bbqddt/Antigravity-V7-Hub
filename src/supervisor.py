#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Antigravity 每日自检与自动演进监管系统 V1.0

职责:
1. 守护进程健康检查 — 自动重启
2. 金库公式验证 — 校准偏差
3. 死代码检测 — 清理冗余
4. 数据完整性检查 — 确保历史数据最新
5. API密钥有效性检测 — 失效时告警
6. 演进日志分析 — 跟踪趋势
7. 自动生成日报

运行方式:
    python supervisor.py              # 单次自检
    python supervisor.py --daemon     # 守护模式（每6小时自检）
    python supervisor.py --full       # 完整自检+演进
"""
import json
import os
import sys
import time
import signal
import subprocess
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 立即刷新stdout
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_DIR = Path(os.environ.get('USERPROFILE', '')) / '.claude' / 'projects' / 'D--cdx-claude-win32-x64' / 'memory'

# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════

def ts() -> str:
    return datetime.now().strftime('%H:%M:%S')

def log(msg: str, level: str = "INFO"):
    print(f"[{ts()}] [{level}] {msg}", flush=True)

def write_memory_file(name: str, content: str):
    """写入记忆文件"""
    path = MEMORY_DIR / f"antigravity-{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    log(f"Memory updated: {path.name}")

def read_json(path: str) -> dict:
    """安全读取JSON文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def write_json(path: str, data: dict):
    """安全写入JSON文件"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ═══════════════════════════════════════════════════════════
# 1. 守护进程健康检查
# ═══════════════════════════════════════════════════════════

class DaemonHealthChecker:
    """守护进程健康检查与自动重启"""

    def __init__(self):
        self.daemon_script = PROJECT_ROOT / "continuous_evolution_daemon_v4.py"
        self.vault_path = PROJECT_ROOT / "formula_vault.json"
        self.cycle_dir = PROJECT_ROOT.glob("evolution_cycle_*.json")

    def is_running(self) -> bool:
        """检查守护进程是否在运行"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'continuous_evolution_daemon' in cmdline and 'python' in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    def get_process_info(self) -> Optional[dict]:
        """获取守护进程信息"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'continuous_evolution_daemon' in cmdline and 'python' in cmdline:
                    return {
                        'pid': proc.info['pid'],
                        'cpu': proc.info['cpu_percent'],
                        'mem_mb': proc.info['memory_info'].rss / 1024 / 1024 if proc.info['memory_info'] else 0,
                        'uptime_hours': (time.time() - proc.info['create_time']) / 3600,
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return None

    def restart_daemon(self) -> bool:
        """重启守护进程"""
        # 先杀掉旧进程
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'continuous_evolution_daemon' in cmdline and 'python' in cmdline:
                    log(f"Killing old daemon PID {proc.info['pid']}")
                    proc.kill()
                    time.sleep(2)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # 启动新进程
        log("Starting new daemon...")
        proc = subprocess.Popen(
            [sys.executable, '-u', str(self.daemon_script), '--daemon', '--interval', '30'],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        time.sleep(5)  # 等待启动

        if proc.poll() is None:
            log(f"Daemon started successfully (PID {proc.pid})")
            return True
        else:
            log(f"Daemon failed to start! Exit code: {proc.returncode}", "ERROR")
            return False

    def check(self) -> dict:
        """执行健康检查"""
        result = {
            'running': self.is_running(),
            'process': self.get_process_info(),
            'last_cycle_update': None,
            'cycle_count': 0,
            'action_taken': None,
        }

        # 检查最新的cycle文件
        cycles = sorted(self.cycle_dir, key=lambda p: p.name)
        result['cycle_count'] = len(cycles)
        if cycles:
            latest = read_json(str(cycles[-1]))
            result['last_cycle_update'] = latest.get('timestamp')

        # 如果守护进程没在运行，自动重启
        if not result['running']:
            log("Daemon NOT running! Attempting restart...")
            if self.restart_daemon():
                result['action_taken'] = 'daemon_restarted'
            else:
                result['action_taken'] = 'restart_failed'
        else:
            result['action_taken'] = 'healthy'

        return result

# ═══════════════════════════════════════════════════════════
# 2. 金库公式验证与校准
# ═══════════════════════════════════════════════════════════

class VaultValidator:
    """金库公式验证与校准"""

    def __init__(self):
        self.vault_path = PROJECT_ROOT / "formula_vault.json"
        self.evaluator = None  # lazy load
        self.draws = None  # lazy load

    def _lazy_load(self):
        if self.draws is None:
            from data_layer import load_history
            self.draws = load_history()
        if self.evaluator is None:
            from formula_lang.evaluator import FormulaEvaluator
            self.evaluator = FormulaEvaluator(random_baseline = 1.09)

    def verify_all(self) -> dict:
        """验证所有公式"""
        self._lazy_load()
        vault = read_json(str(self.vault_path))
        formulas = vault.get('formulas', {})

        if not formulas:
            return {'status': 'empty_vault', 'issues': ['No formulas in vault']}

        issues = []
        recalibrated = 0
        duplicates_found = []

        # 检查重复公式 — 只检查active和bench的公式（排除已eliminated的）
        by_primitives = {}
        for name, fdata in formulas.items():
            status = fdata.get('status', 'active')
            if status == 'eliminated':
                continue
            key = tuple(sorted(fdata.get('primitives', [])))
            if key in by_primitives:
                duplicates_found.append({
                    'primitives': list(key),
                    'formulas': [by_primitives[key], name]
                })
                issues.append(f"Duplicate primitive set: {key}")
            else:
                by_primitives[key] = name

        # 检查每个公式的avg_hits是否在合理范围 — 只检查active和bench
        for name, fdata in formulas.items():
            status = fdata.get('status', 'active')
            if status == 'eliminated':
                continue
            avg = fdata.get('avg_hits', 0)
            test_avg = fdata.get('test_avg', 0)

            if avg < 1.0:
                issues.append(f"{name}: avg_hits={avg:.4f} BELOW RANDOM BASELINE!")
            if test_avg < 1.09:
                issues.append(f"{name}: test_avg={test_avg:.4f} BELOW RANDOM BASELINE!")

            # 检查数值合理性
            if avg > 3.0 or test_avg > 3.0:
                issues.append(f"{name}: suspiciously high avg={avg:.4f} test_avg={test_avg:.4f}")

        # 校准: 重新评估前5个公式验证偏差
        top_formulas = sorted(formulas.items(), key=lambda x: -(x[1].get('test_avg') or x[1].get('avg_hits', 0)))[:5]
        calibrations = []
        for name, fdata in top_formulas:
            stored_avg = fdata.get('avg_hits', 0)
            stored_test = fdata.get('test_avg', 0)

            # 重建公式
            prims = self._reconstruct_primitives(fdata)
            if prims:
                from formula_lang.grammar import FormulaGrammar
                op = fdata.get('operator', '')
                if 'cascade' in op:
                    formula = FormulaGrammar.cascade(prims, name=name)
                elif 'resonance' in op:
                    formula = FormulaGrammar.resonance(prims, name=name)
                elif 'phase' in op:
                    formula = FormulaGrammar.phase_align(prims, name=name)
                else:
                    formula = FormulaGrammar.weighted_sum(prims, name=name)

                result = self.evaluator.evaluate(formula, self.draws, n_windows=20, window_size=400, step=40)
                verified_avg = result.get('avg_hits', 0)
                deviation = abs(verified_avg - stored_avg)

                calibrations.append({
                    'name': name,
                    'stored_avg': stored_avg,
                    'verified_avg': verified_avg,
                    'deviation': deviation,
                    'needs_calibration': deviation > 0.05,
                })

                if deviation > 0.05:
                    issues.append(f"{name}: avg deviation {deviation:.4f} (needs calibration)")
                    recalibrated += 1

        return {
            'total_formulas': len(formulas),
            'issues': issues,
            'duplicate_sets': duplicates_found,
            'calibrations': calibrations,
            'recalibrated_count': recalibrated,
            'status': 'clean' if not issues else 'issues_found',
        }

    def _reconstruct_primitives(self, fdata: dict) -> list:
        """从金库数据重建原语列表"""
        try:
            from formula_lang.primitive import get_default_primitives
            prims = get_default_primitives()
            names = fdata.get('primitives', [])
            return [p for p in prims if p.name in names]
        except:
            return []

# ═══════════════════════════════════════════════════════════
# 3. 数据完整性检查
# ═══════════════════════════════════════════════════════════

class DataIntegrityChecker:
    """数据完整性检查"""

    def check(self) -> dict:
        result = {}

        # 检查历史数据文件
        csv_path = PROJECT_ROOT / "data" / "lottery_history.csv"
        if csv_path.exists():
            size = csv_path.stat().st_size
            mtime = datetime.fromtimestamp(csv_path.stat().st_mtime)
            result['csv_exists'] = True
            result['csv_size_kb'] = size / 1024
            result['csv_modified'] = mtime.isoformat()

            # 检查数据行数
            lines = csv_path.read_text(encoding='utf-8-sig').strip().split('\n')
            result['data_rows'] = len(lines) - 1  # minus header
        else:
            result['csv_exists'] = False
            result['error'] = 'lottery_history.csv not found!'

        # 检查数据层
        try:
            from data_layer import load_history
            draws = load_history()
            result['loaded_periods'] = len(draws)
            result['first_period'] = draws[0].period if draws else None
            result['last_period'] = draws[-1].period if draws else None

            # 检查数据新鲜度
            if draws:
                last_date = draws[-1].date if hasattr(draws[-1], 'date') else '?'
                result['last_date'] = str(last_date)
                days_since_update = (datetime.now() - datetime.strptime(str(last_date), '%Y-%m-%d')).days if isinstance(last_date, str) and last_date != '?' else -1
                result['days_since_last_draw'] = days_since_update

                if days_since_update > 3:
                    result['warning'] = f'Data is {days_since_update} days old! May need updating.'
        except Exception as e:
            result['load_error'] = str(e)

        return result

# ═══════════════════════════════════════════════════════════
# 4. API密钥检查
# ═══════════════════════════════════════════════════════════

class APIKeyChecker:
    """API密钥有效性检测"""

    def check(self) -> dict:
        result = {}
        keys_path = PROJECT_ROOT / "api_keys.json"

        if keys_path.exists():
            keys = read_json(str(keys_path))
            result['keys_found'] = list(keys.keys())

            # 检查是否有空值或无效值
            for name, value in keys.items():
                if not value or value in ['YOUR_API_KEY_HERE', '', 'null']:
                    result[f'{name}_invalid'] = True
                    result['issues'] = result.get('issues', [])
                    result['issues'].append(f'{name} has invalid/empty key')
        else:
            result['keys_file_missing'] = True
            result['issues'] = ['api_keys.json not found']

        return result

# ═══════════════════════════════════════════════════════════
# 5. 演进日志分析
# ═══════════════════════════════════════════════════════════

class EvolutionLogger:
    """演进日志分析"""

    def analyze(self) -> dict:
        result = {}

        # 读取所有cycle文件
        cycles = sorted(PROJECT_ROOT.glob("evolution_cycle_*.json"), key=lambda p: p.name)
        result['total_cycles'] = len(cycles)

        trends = []
        for cycle_file in cycles:
            cycle = read_json(str(cycle_file))
            if 'error' in cycle:
                continue
            trends.append({
                'cycle': cycle.get('cycle'),
                'timestamp': cycle.get('timestamp'),
                'elapsed': cycle.get('elapsed_seconds'),
                'new_formulas': cycle.get('new_formulas'),
                'vault_total': cycle.get('vault_summary', {}).get('total'),
                'vault_active': cycle.get('vault_summary', {}).get('active'),
            })

        result['trends'] = trends

        # 计算趋势
        if len(trends) >= 2:
            first = trends[0]
            last = trends[-1]
            result['vault_growth'] = last['vault_total'] - first['vault_total']
            result['total_formulas_generated'] = sum(t.get('new_formulas', 0) for t in trends)
            result['avg_cycle_time'] = sum(t.get('elapsed', 0) for t in trends) / len(trends)

        return result

# ═══════════════════════════════════════════════════════════
# 6. 死代码检测
# ═══════════════════════════════════════════════════════════

class DeadCodeDetector:
    """死代码检测"""

    def scan(self) -> dict:
        result = {
            'scripts': [],
            'potential_issues': [],
        }

        # 检查所有.py文件
        for py_file in PROJECT_ROOT.glob("*.py"):
            if py_file.name.startswith('.') or py_file.name == 'supervisor.py':
                continue

            content = py_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.count('\n') + 1

            # 检查是否是独立可运行的脚本（有if __name__ == "__main__"）
            has_main = '__main__' in content
            # 检查是否被其他文件import
            imports_count = 0
            for other in PROJECT_ROOT.glob("*.py"):
                if other != py_file and f'from {py_file.stem}' in other.read_text(errors='ignore') or f'import {py_file.stem}' in other.read_text(errors='ignore'):
                    imports_count += 1

            # 检查是否有TODO/FIXME
            has_todo = bool(__import__('re').search(r'TODO|FIXME|BUG|HACK', content))

            result['scripts'].append({
                'file': py_file.name,
                'lines': lines,
                'has_main': has_main,
                'imported_by': imports_count,
                'has_todo': bool(has_todo),
            })

        # 识别潜在死代码
        for s in result['scripts']:
            if s['imported_by'] == 0 and not s['has_main']:
                result['potential_issues'].append(f"{s['file']}: not imported and no main block")
            if s['imported_by'] == 0 and s['has_main']:
                result['potential_issues'].append(f"{s['file']}: standalone script, not integrated into pipeline")

        return result

# ═══════════════════════════════════════════════════════════
# 7. 自动生成日报
# ═══════════════════════════════════════════════════════════

class DailyReporter:
    """自动生成日报"""

    def generate(self, checks: dict) -> str:
        now = datetime.now().isoformat()
        lines = [
            f"## Antigravity 日报 — {now}",
            "",
            f"### 守护进程",
            f"- 状态: {'运行中' if checks.get('daemon', {}).get('running') else '未运行'}",
            f"- 进程: {json.dumps(checks.get('daemon', {}).get('process', {}), ensure_ascii=False)}",
            f"- 演进轮次: {checks.get('daemon', {}).get('cycle_count', 0)}",
            f"- 操作: {checks.get('daemon', {}).get('action_taken', 'none')}",
            "",
            f"### 金库",
            f"- 公式总数: {checks.get('vault', {}).get('total_formulas', 0)}",
            f"- 问题数: {len(checks.get('vault', {}).get('issues', []))}",
            f"- 重复公式集: {len(checks.get('vault', {}).get('duplicate_sets', []))}",
            "",
            f"### 数据",
            f"- 历史期数: {checks.get('data', {}).get('loaded_periods', 'N/A')}",
            f"- 最新期号: #{checks.get('data', {}).get('last_period', 'N/A')}",
            f"- 最后开奖日期: {checks.get('data', {}).get('last_date', 'N/A')}",
            f"- 距今天数: {checks.get('data', {}).get('days_since_last_draw', 'N/A')}天",
            "",
            f"### 演进趋势",
        ]

        trends = checks.get('evolution', {})
        lines.append(f"- 总轮次: {trends.get('total_cycles', 0)}")
        lines.append(f"- 金库增长: {trends.get('vault_growth', 0)}")
        lines.append(f"- 累计开发: {trends.get('total_formulas_generated', 0)}公式")
        lines.append(f"- 平均每轮耗时: {trends.get('avg_cycle_time', 0):.0f}s")

        lines.append("")
        lines.append(f"### 待处理问题")
        all_issues = []
        all_issues.extend(checks.get('vault', {}).get('issues', []))
        all_issues.extend(checks.get('data', {}).get('warning', '').split('; ') if checks.get('data', {}).get('warning') else [])
        if all_issues:
            for issue in all_issues[:10]:
                lines.append(f"- {issue}")
        else:
            lines.append("- 无")

        lines.append("")
        lines.append(f"### 下一步行动")
        if not checks.get('daemon', {}).get('running'):
            lines.append("- [ ] 重启守护进程")
        if checks.get('vault', {}).get('recalibrated_count', 0) > 0:
            lines.append(f"- [ ] 重新校准 {checks['vault']['recalibrated_count']} 个公式")
        if checks.get('data', {}).get('days_since_last_draw', 0) > 2:
            lines.append("- [ ] 更新历史数据")

        return '\n'.join(lines)

# ═══════════════════════════════════════════════════════════
# 主控制器
# ═══════════════════════════════════════════════════════════

class Supervisor:
    """监管主控制器"""

    def __init__(self):
        self.daemon_checker = DaemonHealthChecker()
        self.vault_validator = VaultValidator()
        self.data_checker = DataIntegrityChecker()
        self.api_checker = APIKeyChecker()
        self.evolution_logger = EvolutionLogger()
        self.dead_code_detector = DeadCodeDetector()
        self.daily_reporter = DailyReporter()

    def run_full_check(self) -> dict:
        """执行完整自检"""
        log("=" * 60)
        log("开始每日自检...")
        log("=" * 60)

        checks = {}

        # 1. 守护进程
        log("[1/7] 守护进程健康检查...")
        checks['daemon'] = self.daemon_checker.check()
        log(f"  状态: {'运行中' if checks['daemon']['running'] else '未运行'}")
        log(f"  演进轮次: {checks['daemon']['cycle_count']}")
        if checks['daemon'].get('action_taken'):
            log(f"  操作: {checks['daemon']['action_taken']}")

        # 2. 金库验证
        log("[2/7] 金库公式验证...")
        checks['vault'] = self.vault_validator.verify_all()
        log(f"  公式数: {checks['vault']['total_formulas']}")
        log(f"  问题数: {len(checks['vault']['issues'])}")
        for cal in checks['vault'].get('calibrations', []):
            log(f"  [{cal['name'][:30]}] stored={cal['stored_avg']:.4f} verified={cal['verified_avg']:.4f} dev={cal['deviation']:.4f} calibrate={'YES' if cal['needs_calibration'] else 'no'}")

        # 3. 数据完整性
        log("[3/7] 数据完整性检查...")
        checks['data'] = self.data_checker.check()
        log(f"  期数: {checks['data'].get('loaded_periods', '?')}")
        log(f"  最后: #{checks['data'].get('last_period', '?')}")

        # 4. API密钥
        log("[4/7] API密钥检查...")
        checks['api'] = self.api_checker.check()
        log(f"  密钥: {checks['api'].get('keys_found', [])}")

        # 5. 演进日志
        log("[5/7] 演进日志分析...")
        checks['evolution'] = self.evolution_logger.analyze()
        log(f"  轮次: {checks['evolution']['total_cycles']}")

        # 6. 死代码
        log("[6/7] 死代码检测...")
        checks['dead_code'] = self.dead_code_detector.scan()
        issues = checks['dead_code'].get('potential_issues', [])
        log(f"  潜在问题: {len(issues)}")
        for issue in issues[:5]:
            log(f"    - {issue}")

        # 7. 生成日报
        log("[7/7] 生成日报...")
        report = self.daily_reporter.generate(checks)

        log("=" * 60)
        log("自检完成")
        log("=" * 60)

        # 保存日报
        report_path = PROJECT_ROOT / f"daily_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path.write_text(report, encoding='utf-8')
        log(f"日报已保存: {report_path.name}")

        # 保存检查结果
        summary = {
            'timestamp': datetime.now().isoformat(),
            'daemon_running': checks['daemon']['running'],
            'vault_total': checks['vault']['total_formulas'],
            'vault_issues': len(checks['vault']['issues']),
            'data_periods': checks['data'].get('loaded_periods', 0),
            'evolution_cycles': checks['evolution']['total_cycles'],
            'dead_code_issues': len(issues),
            'report_file': report_path.name,
        }
        with open(PROJECT_ROOT / "supervisor_status.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        return checks

    def run_daemon_mode(self, interval_hours: int = 6):
        """守护模式 — 每6小时自检"""
        log(f"守护模式启动，每{interval_hours}小时自检一次")

        running = True
        def handle_signal(signum, frame):
            nonlocal running
            log(f"收到信号 {signum}，准备退出...")
            running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        cycle = 0
        while running:
            cycle += 1
            log(f"\n{'='*60}")
            log(f"自检周期 #{cycle}")
            log(f"{'='*60}")

            checks = self.run_full_check()

            # 如果有严重问题，记录到memory
            if not checks['daemon']['running']:
                log("CRITICAL: Daemon not running!", "ERROR")

            wait_seconds = interval_hours * 3600
            log(f"下次自检将在 {interval_hours} 小时后...")

            for remaining in range(wait_seconds, 0, -3600):
                if not running:
                    break
                if remaining % 3600 == 0:
                    log(f"  剩余: {remaining // 3600} 小时")
                time.sleep(3600)

        log(f"监管进程已停止。共运行 {cycle} 个自检周期。")

# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity 每日自检与自动演进监管系统 V1.0")
    parser.add_argument("--daemon", action="store_true", help="守护模式（每6小时自检）")
    parser.add_argument("--full", action="store_true", help="完整自检+报告")
    parser.add_argument("--interval", type=int, default=6, help="守护模式间隔（小时）")
    args = parser.parse_args()

    supervisor = Supervisor()

    if args.daemon:
        supervisor.run_daemon_mode(interval_hours=args.interval)
    else:
        supervisor.run_full_check()
        print("\n自检完成。请查看生成的日报和supervisor_status.json。")
