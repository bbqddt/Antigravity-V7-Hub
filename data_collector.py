#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 多数据源采集器 V3.0
===============================
- 统一基类 + 3 实现 (500.com, 彩经网, 新浪彩票)
- 自动去重、校验、断点续传
- 物理信号（机器/球组）解析预留
"""

import os
import sys
import csv
import json
import time
import logging
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Iterator, Tuple
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

_PROJECT_ROOT = Path(__file__).resolve().parent
_DATA_DIR = _PROJECT_ROOT / "data"
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "data_collector.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("DataCollector")


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class Draw:
    """单期开奖数据"""
    period: int
    reds: List[int]      # 6 个红球，已排序
    blue: int            # 蓝球
    date: str = ""       # 开奖日期 YYYY-MM-DD
    machine: str = ""    # 开奖机编号
    ball_set: str = ""   # 球组编号

    def to_csv_row(self) -> List[str]:
        return [
            str(self.period),
            ",".join(f"{r:02d}" for r in self.reds),
            f"{self.blue:02d}",
            self.date,
            self.machine,
            self.ball_set,
        ]

    @classmethod
    def from_csv_row(cls, row: List[str]) -> "Draw":
        return cls(
            period=int(row[0]),
            reds=[int(x) for x in row[1].split(",")],
            blue=int(row[2]),
            date=row[3] if len(row) > 3 else "",
            machine=row[4] if len(row) > 4 else "",
            ball_set=row[5] if len(row) > 5 else "",
        )


# ═══════════════════════════════════════════════════════════════
# 基类
# ═══════════════════════════════════════════════════════════════

class DataSource(ABC):
    """数据源抽象基类"""
    
    name: str = "base"
    rate_limit_sec: float = 1.0
    
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
    
    @abstractmethod
    def fetch_latest_period(self) -> int:
        """获取最新一期期号"""
        pass
    
    @abstractmethod
    def fetch_range(self, start: int, end: int) -> Iterator[Draw]:
        """拉取指定区间 [start, end] 的开奖数据（含物理信号）"""
        pass
    
    def _respect_rate_limit(self):
        time.sleep(self.rate_limit_sec)


# ═══════════════════════════════════════════════════════════════
# 实现 1：500.com (主源)
# ═══════════════════════════════════════════════════════════════

class Source500(DataSource):
    name = "500.com"
    BASE_URL = "https://datachart.500.com/ssq/history/newinc/history.php"
    DETAIL_URL = "https://datachart.500.com/ssq/history/inc/history.php"  # 含机器/球组
    
    def fetch_latest_period(self) -> int:
        try:
            resp = self.session.get(self.BASE_URL, params={"start": 1, "end": 999999}, timeout=10)
            resp.encoding = 'gb2312'
            soup = BeautifulSoup(resp.text, 'html.parser')
            tbody = soup.find('tbody', id='tdata')
            if not tbody:
                return 0
            first_tr = tbody.find('tr')
            if not first_tr:
                return 0
            td = first_tr.find('td')
            return int(td.get_text(strip=True)) if td else 0
        except Exception as e:
            logger.error(f"[{self.name}] 获取最新期号失败: {e}")
            return 0
    
    def fetch_range(self, start: int, end: int) -> Iterator[Draw]:
        """分页拉取，每页 100 期"""
        page_size = 100
        for page_start in range(start, end + 1, page_size):
            page_end = min(page_start + page_size - 1, end)
            params = {"start": page_start, "end": page_end}
            try:
                resp = self.session.get(self.BASE_URL, params=params, timeout=15)
                resp.encoding = 'gb2312'
                soup = BeautifulSoup(resp.text, 'html.parser')
                tbody = soup.find('tbody', id='tdata')
                if not tbody:
                    break
                
                for tr in tbody.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) < 3:
                        continue
                    try:
                        period = int(tds[0].get_text(strip=True))
                        if period < start or period > end:
                            continue
                        # 红球：tds[1] 格式 "01 05 12 23 28 33"
                        reds_text = tds[1].get_text(strip=True)
                        reds = [int(x) for x in reds_text.split()]
                        blue = int(tds[2].get_text(strip=True))
                        date = tds[3].get_text(strip=True) if len(tds) > 3 else ""
                        
                        # 物理信号：需从详情页获取（预留）
                        machine, ball_set = self._fetch_physical(period)
                        
                        yield Draw(
                            period=period,
                            reds=sorted(reds),
                            blue=blue,
                            date=date,
                            machine=machine,
                            ball_set=ball_set,
                        )
                    except (ValueError, IndexError) as e:
                        logger.warning(f"[{self.name}] 解析行失败: {e}")
                        continue
                
                self._respect_rate_limit()
                
            except Exception as e:
                logger.error(f"[{self.name}] 拉取分页 {page_start}-{page_end} 失败: {e}")
                break
    
    def _fetch_physical(self, period: int) -> Tuple[str, str]:
        """获取开奖机/球组信息（预留，可后续实现）"""
        return "", ""


# ═══════════════════════════════════════════════════════════════
# 实现 2：彩经网 (备源)
# ═══════════════════════════════════════════════════════════════

class SourceCJW(DataSource):
    name = "彩经网"
    BASE_URL = "https://www.cjw.com.cn/ssq/kaijiang/"
    
    def fetch_latest_period(self) -> int:
        try:
            resp = self.session.get(self.BASE_URL, timeout=10)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 彩经网结构：表格第一行第一列为期号
            table = soup.find('table', class_='kj-table')
            if table:
                first_row = table.find('tbody').find('tr')
                if first_row:
                    td = first_row.find('td')
                    return int(td.get_text(strip=True)) if td else 0
        except Exception as e:
            logger.error(f"[{self.name}] 获取最新期号失败: {e}")
        return 0
    
    def fetch_range(self, start: int, end: int) -> Iterator[Draw]:
        # 彩经网通常只提供近期数据，不支持历史分页
        # 这里仅作演示，实际需根据站点结构实现
        logger.warning(f"[{self.name}] 历史区间拉取暂未实现，建议仅用于最新期校验")
        return
        yield  # 使函数成为生成器


# ═══════════════════════════════════════════════════════════════
# 实现 3：新浪彩票 (备源)
# ═══════════════════════════════════════════════════════════════

class SourceSina(DataSource):
    name = "新浪彩票"
    API_URL = "https://api.lottery.sina.com.cn/ssq/history"
    
    def fetch_latest_period(self) -> int:
        try:
            resp = self.session.get(self.API_URL, params={"count": 1}, timeout=10)
            data = resp.json()
            if data.get('data') and len(data['data']) > 0:
                return int(data['data'][0]['expect'])
        except Exception as e:
            logger.error(f"[{self.name}] 获取最新期号失败: {e}")
        return 0
    
    def fetch_range(self, start: int, end: int) -> Iterator[Draw]:
        try:
            # 新浪 API 支持按期号范围查询
            resp = self.session.get(self.API_URL, params={
                "start": start,
                "end": end
            }, timeout=15)
            data = resp.json()
            for item in data.get('data', []):
                period = int(item['expect'])
                if period < start or period > end:
                    continue
                reds = [int(x) for x in item['red'].split(',')]
                blue = int(item['blue'])
                date = item.get('opendate', '')
                yield Draw(
                    period=period,
                    reds=sorted(reds),
                    blue=blue,
                    date=date,
                    machine=item.get('machine', ''),
                    ball_set=item.get('ballset', ''),
                )
        except Exception as e:
            logger.error(f"[{self.name}] 拉取区间失败: {e}")
        return
        yield


# ═══════════════════════════════════════════════════════════════
# 统一管理器
# ═══════════════════════════════════════════════════════════════

class DataCollector:
    """多数据源统一采集管理器"""
    
    CSV_PATH = _DATA_DIR / "lottery_history.csv"
    CHECKPOINT_PATH = _DATA_DIR / "collector_checkpoint.json"
    PHYSICAL_PATH = _PROJECT_ROOT / "physical_signals.json"
    
    # 优先级：主源在前，备源在后
    SOURCES = [Source500(), SourceSina(), SourceCJW()]
    
    def __init__(self):
        self.checkpoint = self._load_checkpoint()
        self.physical_signals = self._load_physical()
    
    def _load_checkpoint(self) -> Dict:
        if self.CHECKPOINT_PATH.exists():
            try:
                with open(self.CHECKPOINT_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_fetched_period": 0, "last_update": ""}
    
    def _save_checkpoint(self):
        self.checkpoint["last_update"] = datetime.now().isoformat()
        with open(self.CHECKPOINT_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.checkpoint, f, ensure_ascii=False, indent=2)
    
    def _load_physical(self) -> Dict:
        if self.PHYSICAL_PATH.exists():
            try:
                with open(self.PHYSICAL_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_physical(self):
        with open(self.PHYSICAL_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.physical_signals, f, ensure_ascii=False, indent=2)
    
    def _load_existing_periods(self) -> set:
        """加载本地已有期号"""
        periods = set()
        if self.CSV_PATH.exists():
            with open(self.CSV_PATH, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if row and row[0].isdigit():
                        periods.add(int(row[0]))
        return periods
    
    def _validate_draw(self, draw: Draw) -> bool:
        """校验单期数据合法性"""
        if not (1 <= draw.period <= 999999):
            return False
        if len(draw.reds) != 6:
            return False
        if not all(1 <= r <= 33 for r in draw.reds):
            return False
        if len(set(draw.reds)) != 6:
            return False
        if not (1 <= draw.blue <= 16):
            return False
        if draw.reds != sorted(draw.reds):
            return False
        return True
    
    def _append_to_csv(self, draws: List[Draw]):
        """追加写入 CSV（按期号升序）"""
        file_exists = self.CSV_PATH.exists()
        with open(self.CSV_PATH, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["period", "red", "blue", "date", "machine", "ball_set"])
            for d in draws:
                writer.writerow(d.to_csv_row())
    
    def incremental_update(self) -> Tuple[int, int]:
        """
        增量更新：从所有源获取最新期号，取最大值为目标；
        从本地最大期号+1 开始补全。
        Returns: (新增条数, 当前最新期号)
        """
        # 1. 获取各源最新期号，取最大值
        latest_periods = {}
        for src in self.SOURCES:
            try:
                p = src.fetch_latest_period()
                if p > 0:
                    latest_periods[src.name] = p
                    logger.info(f"[{src.name}] 最新期号: {p}")
            except Exception as e:
                logger.warning(f"[{src.name}] 获取最新期号异常: {e}")
        
        if not latest_periods:
            logger.error("所有数据源均不可用")
            return 0, 0
        
        target_period = max(latest_periods.values())
        logger.info(f"目标最新期号: {target_period} (来源: {max(latest_periods, key=latest_periods.get)})")
        
        # 2. 确定本地已有最大期号
        existing = self._load_existing_periods()
        local_max = max(existing) if existing else 0
        
        if target_period <= local_max:
            logger.info(f"本地已是最新 (本地: {local_max}, 目标: {target_period})")
            return 0, local_max
        
        # 3. 从 local_max+1 到 target_period 逐源尝试补全
        new_draws = []
        missing_periods = set(range(local_max + 1, target_period + 1))
        
        for src in self.SOURCES:
            if not missing_periods:
                break
            try:
                logger.info(f"[{src.name}] 补全区间: {min(missing_periods)}-{max(missing_periods)}")
                for draw in src.fetch_range(min(missing_periods), max(missing_periods)):
                    if draw.period in missing_periods and self._validate_draw(draw):
                        new_draws.append(draw)
                        missing_periods.discard(draw.period)
                        # 记录物理信号
                        if draw.machine or draw.ball_set:
                            self.physical_signals[str(draw.period)] = {
                                "machine": draw.machine,
                                "ball_set": draw.ball_set,
                                "source": src.name,
                                "updated": datetime.now().isoformat(),
                            }
            except Exception as e:
                logger.error(f"[{src.name}] 补全失败: {e}")
        
        if missing_periods:
            logger.warning(f"仍有 {len(missing_periods)} 期缺失: {sorted(missing_periods)[:10]}...")
        
        # 4. 按期号排序并写入
        new_draws.sort(key=lambda d: d.period)
        if new_draws:
            self._append_to_csv(new_draws)
            logger.info(f"新增 {len(new_draws)} 期数据到 CSV")
        
        # 5. 更新检查点与物理信号
        self.checkpoint["last_fetched_period"] = target_period
        self._save_checkpoint()
        self._save_physical()
        
        return len(new_draws), target_period
    
    def full_sync(self, start: int = 1) -> Tuple[int, int]:
        """全量同步（慎用，会重写 CSV）"""
        logger.warning("执行全量同步，将重写历史数据...")
        # 备份原 CSV
        if self.CSV_PATH.exists():
            backup = self.CSV_PATH.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
            self.CSV_PATH.rename(backup)
            logger.info(f"原数据已备份至: {backup}")
        
        # 清空检查点
        self.checkpoint = {"last_fetched_period": 0, "last_update": ""}
        self._save_checkpoint()
        
        return self.incremental_update()


# ═══════════════════════════════════════════════════════════════
# 兼容旧接口
# ═══════════════════════════════════════════════════════════════

def main():
    """兼容旧 data_updater_v2.py 的 main() 入口"""
    collector = DataCollector()
    added, latest = collector.incremental_update()
    print(f"更新完成: 新增 {added} 期, 最新期号 {latest}")


if __name__ == "__main__":
    main()