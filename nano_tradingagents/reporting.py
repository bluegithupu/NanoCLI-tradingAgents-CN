from __future__ import annotations

from pathlib import Path

from nano_tradingagents.models import AgentState


TITLE_MAP = {
    "market": "技术面分析",
    "fundamentals": "基本面分析",
    "news": "新闻分析",
    "bull": "看多观点",
    "bear": "看空观点",
    "trader": "交易员建议",
    "risk": "风险经理最终决策",
}


def render_markdown(state: AgentState) -> str:
    snapshot = state.snapshot
    decision = state.final_decision
    lines = [
        f"# Nano A股分析报告 - {state.request.symbol}",
        "",
        f"- 分析日期: {state.request.trade_date}",
        f"- 分析深度: {state.request.depth}",
        f"- 最终动作: {decision.get('action', '观望')}",
    ]
    if snapshot:
        lines.extend([
            f"- 股票名称: {snapshot.name}",
            "",
            "## 数据限制",
        ])
        if snapshot.warnings:
            lines.extend(f"- {item}" for item in snapshot.warnings)
        else:
            lines.append("- 无")
    for key, content in state.reports.items():
        lines.extend(["", f"## {TITLE_MAP.get(key, key)}", "", content])
    lines.extend([
        "",
        "## 免责声明",
        "",
        "本报告由自动化工具生成，仅用于研究和学习，不构成投资建议。投资有风险，决策需独立判断。",
    ])
    return "\n".join(lines).strip() + "\n"


def save_report(state: AgentState, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{state.request.symbol}_{state.request.trade_date}.md"
    path.write_text(render_markdown(state), encoding="utf-8")
    return path
