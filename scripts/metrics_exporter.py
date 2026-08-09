#!/usr/bin/env python3
# Lightweight Prometheus-style metrics exporter for Antigravity
# Serves metrics by reading daemon_state.json and evolution_performance_log.json

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import shutil

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = _PROJECT_ROOT / 'daemon_state.json'
PERF_FILE = _PROJECT_ROOT / 'evolution_performance_log.json'


def _read_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _read_perf():
    try:
        with open(PERF_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _disk_free_gb():
    try:
        total, used, free = shutil.disk_usage(_PROJECT_ROOT)
        return round(free / (1024**3), 2)
    except Exception:
        return -1


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 对所有路径返回指标，确保浏览器与抓取器都能访问
        state = _read_state()
        perf = _read_perf()

        total_runs = int(state.get('total_runs', 0) or 0)
        best_score = perf.get('best_score') or perf.get('best_combined_score') or state.get('best_score') or 0
        try:
            best_score = float(best_score)
        except Exception:
            best_score = 0.0

        last_run = state.get('last_run')
        last_run_ts = 0
        try:
            if last_run:
                # parse ISO
                last_run_ts = int(time.mktime(time.strptime(last_run.split('.')[0], "%Y-%m-%dT%H:%M:%S")))
        except Exception:
            last_run_ts = 0

        last_notify = state.get('last_notify') or {}
        last_notify_time = 0
        if isinstance(last_notify, dict):
            t = last_notify.get('time')
            try:
                if t:
                    last_notify_time = int(time.mktime(time.strptime(t.split('.')[0], "%Y-%m-%dT%H:%M:%S")))
            except Exception:
                last_notify_time = 0

        perf_best = perf.get('best_score') or perf.get('best_combined_score') or 0
        try:
            perf_best = float(perf_best)
        except Exception:
            perf_best = 0.0

        disk_free = _disk_free_gb()

        lines = [
            '# HELP antigravity_total_runs 总运行次数',
            '# TYPE antigravity_total_runs gauge',
            f'antigravity_total_runs {total_runs}',
            '# HELP antigravity_best_score 最近演进的最佳综合评分',
            '# TYPE antigravity_best_score gauge',
            f'antigravity_best_score {best_score}',
            '# HELP antigravity_perf_best_score performance log best score',
            '# TYPE antigravity_perf_best_score gauge',
            f'antigravity_perf_best_score {perf_best}',
            '# HELP antigravity_last_run_timestamp 上次运行时间 (unix)',
            '# TYPE antigravity_last_run_timestamp gauge',
            f'antigravity_last_run_timestamp {last_run_ts}',
            '# HELP antigravity_last_notify_time 上次告警时间 (unix)',
            '# TYPE antigravity_last_notify_time gauge',
            f'antigravity_last_notify_time {last_notify_time}',
            '# HELP antigravity_disk_free_gb 磁盘剩余 (GB)',
            '# TYPE antigravity_disk_free_gb gauge',
            f'antigravity_disk_free_gb {disk_free}',
        ]

        payload = "\n".join(lines) + "\n"
        b = payload.encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, format, *args):
        # suppress default logging
        return


def main():
    parser = argparse.ArgumentParser(description='Metrics exporter for Antigravity')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=9119)
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MetricsHandler)
    print(f"metrics exporter listening on http://{args.host}:{args.port}/metrics")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == '__main__':
    main()
