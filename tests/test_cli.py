from typer.testing import CliRunner

from nano_tradingagents import cli
from nano_tradingagents.models import AShareSnapshot


class FakeProvider:
    def load_snapshot(self, symbol, trade_date, depth):
        return AShareSnapshot(symbol=symbol, name="平安银行", trade_date=trade_date)


def test_cli_analyze_mock(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "AShareDataProvider", lambda: FakeProvider())
    runner = CliRunner()
    result = runner.invoke(cli.app, [
        "analyze",
        "000001",
        "--date",
        "2026-05-08",
        "--mock-llm",
        "--report-dir",
        str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "000001_2026-05-08.md").exists()
