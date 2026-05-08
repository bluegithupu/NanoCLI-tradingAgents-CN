from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    load_dotenv = None


DEPTHS = {"quick", "standard", "deep"}
ANALYSTS = {"market", "fundamentals", "news"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    request_timeout: int = 120
    reports_dir: Path = Path("reports")


def load_settings() -> Settings:
    if load_dotenv:
        load_dotenv()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        request_timeout=int(os.getenv("OPENAI_TIMEOUT", "120")),
        reports_dir=Path(os.getenv("NANO_REPORTS_DIR", "reports")),
    )


def normalize_depth(depth: str) -> str:
    normalized = (depth or "standard").strip().lower()
    mapping = {"快速": "quick", "标准": "standard", "深度": "deep"}
    normalized = mapping.get(normalized, normalized)
    if normalized not in DEPTHS:
        raise ValueError(f"不支持的分析深度: {depth}，支持: quick, standard, deep")
    return normalized


def parse_analysts(value: str) -> List[str]:
    if not value:
        return ["market", "fundamentals", "news"]
    analysts = [item.strip().lower() for item in value.split(",") if item.strip()]
    unknown = [item for item in analysts if item not in ANALYSTS]
    if unknown:
        raise ValueError(f"不支持的分析师: {', '.join(unknown)}，支持: market,fundamentals,news")
    if not analysts:
        raise ValueError("至少需要选择一个分析师")
    return analysts
