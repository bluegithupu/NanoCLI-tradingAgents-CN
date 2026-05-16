from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AnalysisRequest:
    symbol: str
    trade_date: str
    depth: str = "standard"
    data_source: str = "tushare"
    analysts: List[str] = field(default_factory=lambda: ["market", "fundamentals", "news"])
    report_dir: Path = Path("reports")
    mock_llm: bool = False


@dataclass
class AShareSnapshot:
    symbol: str
    name: str
    trade_date: str
    price_table: str = ""
    indicators: Dict[str, Optional[float]] = field(default_factory=dict)
    fundamentals: Dict[str, Optional[str]] = field(default_factory=dict)
    news: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class AgentState:
    request: AnalysisRequest
    snapshot: Optional[AShareSnapshot] = None
    reports: Dict[str, str] = field(default_factory=dict)
    final_decision: Dict[str, str] = field(default_factory=dict)

    def add_report(self, name: str, content: str) -> None:
        self.reports[name] = content.strip()
