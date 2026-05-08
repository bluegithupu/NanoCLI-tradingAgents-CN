from pathlib import Path

from nano_tradingagents.agents import run_analysis_pipeline
from nano_tradingagents.llm import MockLLM
from nano_tradingagents.models import AShareSnapshot, AnalysisRequest
from nano_tradingagents.reporting import render_markdown


class FakeProvider:
    def load_snapshot(self, symbol, trade_date, depth):
        return AShareSnapshot(
            symbol=symbol,
            name="平安银行",
            trade_date=trade_date,
            price_table="| 日期 | 收盘 |\n|---|---|\n|2026-05-08|10.0|",
            indicators={"latest_close": 10.0, "ma5": 9.8},
            fundamentals={"行业": "银行"},
            news=[{"title": "公告样例", "time": "2026-05-08", "source": "东方财富", "url": ""}],
        )


def test_pipeline_generates_final_decision():
    request = AnalysisRequest(symbol="000001", trade_date="2026-05-08", mock_llm=True)
    state = run_analysis_pipeline(request, MockLLM(), FakeProvider())
    assert "market" in state.reports
    assert "risk" in state.reports
    assert state.final_decision["symbol"] == "000001"


def test_render_markdown_contains_sections():
    request = AnalysisRequest(symbol="000001", trade_date="2026-05-08", mock_llm=True)
    state = run_analysis_pipeline(request, MockLLM(), FakeProvider())
    markdown = render_markdown(state)
    assert "# Nano A股分析报告" in markdown
    assert "## 技术面分析" in markdown
    assert "## 风险经理最终决策" in markdown
