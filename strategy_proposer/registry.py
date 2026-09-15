# -*- coding: utf-8 -*-
"""
Antigravity 策略框架 — 策略注册表 V1.0

跟踪每个假设的完整生命周期。
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from strategy_proposer.hypothesis import Hypothesis

_PROJECT_ROOT = Path(__file__).resolve().parent


class StrategyRegistry:
    """策略注册表 — 假设生命周期管理"""

    def __init__(self, path: Optional[str] = None):
        self.path = path or str(_PROJECT_ROOT / "strategy_registry.json")
        self.hypotheses: Dict[str, Hypothesis] = {}  # id -> Hypothesis
        self.stats = {
            "total_proposed": 0,
            "total_survived": 0,
            "total_eliminated": 0,
            "last_updated": None,
        }

    def add(self, hypothesis: Hypothesis):
        """添加假设"""
        self.hypotheses[hypothesis.id] = hypothesis
        self.stats["total_proposed"] += 1
        self.stats["last_updated"] = datetime.now().isoformat()

    def get_survived(self) -> List[Hypothesis]:
        """获取所有存活的假设"""
        return [h for h in self.hypotheses.values() if h.status == "survived"]

    def get_eliminated(self) -> List[Hypothesis]:
        """获取所有淘汰的假设"""
        return [h for h in self.hypotheses.values() if h.status == "eliminated"]

    def get_by_category(self, category: str) -> List[Hypothesis]:
        """按类别获取假设"""
        return [h for h in self.hypotheses.values() if h.template_category == category]

    def get_by_status(self, status: str) -> List[Hypothesis]:
        """按状态获取假设"""
        return [h for h in self.hypotheses.values() if h.status == status]

    def update_stats(self):
        """更新统计"""
        self.stats["total_survived"] = len(self.get_survived())
        self.stats["total_eliminated"] = len(self.get_eliminated())
        self.stats["last_updated"] = datetime.now().isoformat()

    def save(self, path: Optional[str] = None):
        """保存到文件"""
        p = path or self.path
        data = {
            "hypotheses": {hid: h.to_dict() for hid, h in self.hypotheses.items()},
            "stats": self.stats,
            "updated_at": datetime.now().isoformat(),
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: Optional[str] = None):
        """从文件加载"""
        p = path or self.path
        if not Path(p).exists():
            return
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        for hid, hd in data.get("hypotheses", {}).items():
            h = Hypothesis.from_dict(hd)
            self.hypotheses[hid] = h
        self.stats = data.get("stats", self.stats)

    def summary(self) -> Dict:
        """获取注册表摘要"""
        self.update_stats()
        return {
            "total_proposed": self.stats["total_proposed"],
            "total_survived": self.stats["total_survived"],
            "total_eliminated": self.stats["total_eliminated"],
            "categories": dict(self._count_by_field("template_category")),
            "statuses": dict(self._count_by_field("status")),
            "last_updated": self.stats["last_updated"],
        }

    def _count_by_field(self, field: str) -> Dict[str, int]:
        counts = {}
        for h in self.hypotheses.values():
            val = getattr(h, field, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts
