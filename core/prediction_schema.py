# -*- coding: utf-8 -*-
"""
Antigravity 统一预测输出 Schema

所有预测引擎的输出必须遵循此 schema，以便 Orchestrator 融合和回测框架消费。
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

_PROJECT_ROOT = Path(__file__).parent.resolve()


@dataclass
class PredictionGroup:
    """单组预测"""
    group: int
    reds: List[int]          # 6个红球 (已排序)
    blue: int                # 蓝球
    engine: str              # 来源引擎名
    strategy: str = ""       # 子策略/维度名
    scores: Dict[str, float] = field(default_factory=dict)  # 各维度分数
    causal_valid: bool = True  # 是否通过CausalAnalyzer验证
    causal_multiplier: float = 1.0  # 因果验证乘数

    def to_dict(self) -> dict:
        d = asdict(self)
        d["reds"] = [int(r) for r in self.reds]
        d["blue"] = int(self.blue)
        d["scores"] = {k: round(v, 4) for k, v in self.scores.items()}
        return d


@dataclass
class PredictionResult:
    """完整预测结果"""
    target_period: int
    timestamp: str
    engines: List[str]       # 使用的引擎列表
    groups: List[PredictionGroup]

    def to_dict(self) -> dict:
        return {
            "target_period": self.target_period,
            "timestamp": self.timestamp,
            "engines": self.engines,
            "groups": [g.to_dict() for g in self.groups],
            "schema_version": "1.0",
        }

    def save(self, output_dir: Optional[Path] = None) -> str:
        if output_dir is None:
            output_dir = _PROJECT_ROOT
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / "latest_prediction.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return str(filepath)

    @classmethod
    def load(cls, filepath: Optional[str] = None) -> Optional[PredictionResult]:
        if filepath is None:
            filepath = str(_PROJECT_ROOT / "latest_prediction.json")
        p = Path(filepath)
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        groups = [
            PredictionGroup(
                group=g["group"],
                reds=[int(r) for r in g["reds"]],
                blue=int(g["blue"]),
                engine=g["engine"],
                strategy=g.get("strategy", ""),
                scores=g.get("scores", {}),
                causal_valid=g.get("causal_valid", True),
                causal_multiplier=g.get("causal_multiplier", 1.0),
            )
            for g in data.get("groups", [])
        ]
        return cls(
            target_period=data["target_period"],
            timestamp=data.get("timestamp", ""),
            engines=data.get("engines", []),
            groups=groups,
        )


def save_legacy_compatible(result: PredictionResult, output_dir: Optional[Path] = None) -> str:
    """
    同时保存兼容旧格式的 latest_decision.json，
    确保 commander_bot.py 等旧消费者不受影响。
    """
    if output_dir is None:
        output_dir = _PROJECT_ROOT
    output_dir = Path(output_dir)

    # 简化为单组格式（取最高分）
    if result.groups:
        best = result.groups[0]
        legacy = {
            "period": str(result.target_period),
            "red": best.reds,
            "blue": best.blue,
            "engine": "+".join(result.engines),
            "timestamp": result.timestamp,
        }
    else:
        legacy = {
            "period": str(result.target_period),
            "red": [],
            "blue": 0,
            "engine": "+".join(result.engines),
            "timestamp": result.timestamp,
        }

    filepath = output_dir / "latest_decision.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(legacy, f, ensure_ascii=False, indent=2)
    return str(filepath)
