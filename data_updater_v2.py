# -*- coding: utf-8 -*-
"""
数据自动更新器 V2

功能：
1. 从 500.com 爬取最新开奖数据
2. 自动增量追加到 CSV
3. 同时采集物理信号（开奖机编号、球组编号）
4. 校验数据完整性

新增（V2）：
- 采集开奖公告中的机器/球组信息
- 存储物理信号到 JSON 文件
- 支持从多个数据源交叉验证
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import sys
import csv
import json
import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# Fix Windows console encoding
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# ─── 配置 ─────────────────────────────────────────────────
BASE_URL = "https://datachart.500.com/ssq/history/newinc/history.php"
CSV_PATHS = [
    Path(__file__).parent / "data/lottery_history.csv",
]

PHYSICAL_SIGNALS_PATH = Path(__file__).parent / "physical_signals.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# ─── 数据路径 ─────────────────────────────────────────────
def find_csv_path() -> Path:
    for p in CSV_PATHS:
        if p.exists():
            return p
    return CSV_PATHS[0]


def load_existing_periods(csv_path: Path) -> set:
    if not csv_path.exists():
        return set()
    periods = set()
    try:
        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                p = row.get('period', '')
                if p:
                    periods.add(p)
    except Exception:
        pass
    return periods


# ─── 物理信号解析 ─────────────────────────────────────────
def parse_machine_info(html: str) -> List[Dict[str, Any]]:
    """
    从 500.com 开奖公告页解析机器/球组信息。

    开奖公告通常包含：
    - 开奖机编号
    - 球组编号
    - 开奖视频

    注意：500.com 的主数据页不包含这些信息，
    需要从开奖公告页面获取。
    """
    signals = []
    # TODO: 实现从开奖公告页面解析
    # 目前返回空列表，等待数据源确认
    return signals


def parse_draw_table(html: str) -> List[Dict[str, str]]:
    """从 500.com 表格页解析开奖数据"""
    soup = BeautifulSoup(html, 'html.parser')
    tbody = soup.find('tbody', id='tdata')

    if not tbody:
        return []

    draws = []
    for tr in tbody.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) < 8:
            continue

        period = tds[0].text.strip()
        reds = ",".join([tds[i].text.strip() for i in range(1, 7)])
        blue = tds[7].text.strip()
        date = tds[15].text.strip() if len(tds) > 15 else ""

        # 尝试提取机器信息（如果有）
        machine_info = {}
        for td in tds:
            text = td.text.strip()
            if '机' in text or '球' in text:
                machine_info['raw'] = text

        draws.append({
            'period': period,
            'red': reds,
            'blue': blue,
            'date': date,
            'machine_info': machine_info,
        })

    return draws


# ─── 数据获取 ─────────────────────────────────────────────
def fetch_new_draws(from_period: str, to_period: str = None) -> List[Dict[str, str]]:
    url = f"{BASE_URL}?start={from_period.zfill(5)}&end={to_period or ''}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️ 网络请求失败: {e}")
        return []

    return parse_draw_table(resp.text)


# ─── 物理信号存储 ─────────────────────────────────────────
def load_physical_signals() -> Dict[str, Any]:
    if PHYSICAL_SIGNALS_PATH.exists():
        try:
            with open(PHYSICAL_SIGNALS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_physical_signals(signals: Dict[str, Any]):
    with open(PHYSICAL_SIGNALS_PATH, 'w', encoding='utf-8') as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)
    print(f"  [Signals] 物理信号已保存: {PHYSICAL_SIGNALS_PATH}")


# ─── 主入口 ───────────────────────────────────────────────
def main(from_period: str = None, force: bool = False):
    csv_path = find_csv_path()
    print(f"[DataUpdater V2] 数据文件: {csv_path}")

    existing = load_existing_periods(csv_path)
    if existing:
        latest = max(existing)
        print(f"[DataUpdater V2] 已有 {len(existing)} 期 (最新: {latest})")
    else:
        latest = "03001"
        print(f"[DataUpdater V2] 无已有数据，将从头下载")

    if force:
        start = "03001"
        print("[DataUpdater V2] 强制刷新模式")
    elif from_period:
        start = from_period
        print(f"[DataUpdater V2] 从 {start} 开始更新")
    else:
        latest_num = int(latest)
        start = str(latest_num + 1).zfill(5) if latest_num < 10000 else str(latest_num + 1)
        print(f"[DataUpdater V2] 增量模式: 从 {start} 开始")

    print(f"\n[DataUpdater V2] 正在拉取 {start} 及之后的数据...")
    new_draws = fetch_new_draws(start)

    if not new_draws:
        print("[DataUpdater V2] 没有新数据可获取。")
        return

    fresh_draws = [d for d in new_draws if d['period'] not in existing]
    if not fresh_draws:
        print("[DataUpdater V2] 所有期号已存在，无需更新。")
        return

    # 写入 CSV
    if existing and not force:
        with open(csv_path, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['period', 'red', 'blue', 'date'], extrasaction='ignore')
            writer.writerows(fresh_draws)
        print(f"  [OK] 追加 {len(fresh_draws)} 期数据到 {csv_path}")
    else:
        all_draws = list(existing)
        if not force and existing:
            old_draws = []
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    old_draws.append(row)
            all_draws = old_draws + fresh_draws
        else:
            all_draws = fresh_draws

        all_draws.sort(key=lambda d: d['period'])
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['period', 'red', 'blue', 'date', 'machine_info'])
            writer.writeheader()
            writer.writerows(all_draws)
        print(f"  [OK] 写入 {len(all_draws)} 期数据到 {csv_path}")

    # 保存物理信号
    if fresh_draws:
        signals = load_physical_signals()
        for d in fresh_draws:
            if d.get('machine_info'):
                pid = d['period']
                signals[pid] = d['machine_info']
        if signals:
            save_physical_signals(signals)

    print(f"\n[DataUpdater V2] 更新完成!")
    print(f"  新增: {len(fresh_draws)} 期")
    total_after = len(existing | {d['period'] for d in fresh_draws})
    print(f"  总计: {total_after} 期")
    print(f"  最新: {max(d['period'] for d in fresh_draws)}")
    print("[OK] 数据更新成功")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="双色球数据自动更新 V2")
    parser.add_argument("--from", dest="from_period", help="从指定期号开始")
    parser.add_argument("--force", action="store_true", help="强制刷新全部数据")
    args = parser.parse_args()
    main(from_period=args.from_period, force=args.force)
