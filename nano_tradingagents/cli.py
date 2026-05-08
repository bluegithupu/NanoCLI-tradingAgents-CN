from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from nano_tradingagents.agents import run_analysis_pipeline
from nano_tradingagents.config import load_settings, normalize_depth, parse_analysts
from nano_tradingagents.data.ashare import AShareDataProvider, validate_ashare_symbol
from nano_tradingagents.llm import create_llm
from nano_tradingagents.models import AnalysisRequest
from nano_tradingagents.reporting import save_report

app = typer.Typer(
    help="NanoCLI-tradingAgents-CN: 精简 A 股多智能体分析 CLI",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main() -> None:
    """NanoCLI-tradingAgents-CN command group."""


@app.command()
def analyze(
    symbol: str = typer.Argument(..., help="6 位 A 股代码，例如 000001、600519"),
    trade_date: Optional[str] = typer.Option(None, "--date", help="分析日期 YYYY-MM-DD，默认今天"),
    depth: str = typer.Option("standard", "--depth", help="分析深度: quick, standard, deep"),
    analysts: str = typer.Option("market,fundamentals,news", "--analysts", help="分析师列表，逗号分隔"),
    report_dir: Path = typer.Option(Path("reports"), "--report-dir", help="报告输出目录"),
    mock_llm: bool = typer.Option(False, "--mock-llm", help="使用 mock LLM，不需要 API Key"),
) -> None:
    """运行 A 股精简全流程分析。"""
    try:
        normalized_symbol = validate_ashare_symbol(symbol)
        normalized_depth = normalize_depth(depth)
        selected_analysts = parse_analysts(analysts)
        date_value = trade_date or date.today().strftime("%Y-%m-%d")
        request = AnalysisRequest(
            symbol=normalized_symbol,
            trade_date=date_value,
            depth=normalized_depth,
            analysts=selected_analysts,
            report_dir=report_dir,
            mock_llm=mock_llm,
        )
        settings = load_settings()
        llm = create_llm(settings, mock=mock_llm)
        data_provider = AShareDataProvider()

        def progress(message: str) -> None:
            console.print(f"[cyan]→[/cyan] {message}")

        state = run_analysis_pipeline(request, llm, data_provider, progress=progress)
        report_path = save_report(state, report_dir)
        decision = state.final_decision
        console.print(Panel.fit(
            f"股票: {decision.get('symbol')}\n"
            f"日期: {decision.get('date')}\n"
            f"动作: {decision.get('action')}\n"
            f"报告: {report_path}",
            title="最终结论",
        ))
    except Exception as exc:
        console.print(f"[red]错误:[/red] {exc}")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
