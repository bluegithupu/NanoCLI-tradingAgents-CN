from pathlib import Path

from fastapi.testclient import TestClient

from nano_tradingagents.models import AShareSnapshot
from nano_tradingagents.web import app as web_app_module


class FakeProvider:
    def __init__(self, *args, **kwargs):
        pass

    def load_snapshot(self, symbol, trade_date, depth):
        return AShareSnapshot(symbol=symbol, name="测试股票", trade_date=trade_date)


class FakeLLM:
    def complete(self, system: str, user: str) -> str:
        return "mocked"


def test_list_reports_sorted(tmp_path):
    older = tmp_path / "a.md"
    newer = tmp_path / "b.md"
    older.write_text("a", encoding="utf-8")
    newer.write_text("b", encoding="utf-8")

    import os

    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    rows = web_app_module.list_reports(tmp_path)
    assert len(rows) == 2
    assert rows[0]["name"] == "b.md"


def test_resolve_report_path(tmp_path):
    p = tmp_path / "ok.md"
    p.write_text("ok", encoding="utf-8")
    assert web_app_module.resolve_report_path(tmp_path, "ok.md") == p.resolve()
    assert web_app_module.resolve_report_path(tmp_path, "../x.md") is None


def test_parse_form_values_checkbox_off():
    defaults = web_app_module._default_form_values()
    body = b"symbol=000001&trade_date=2026-05-16&depth=quick&analysts=market&data_source=tushare"
    values = web_app_module._parse_form_values(body, defaults)
    assert values["mock_llm"] is False
    assert values["analysts"] == ["market"]


def test_build_request_rejects_bad_data_source():
    values = web_app_module._default_form_values()
    values["data_source"] = "bad"
    try:
        web_app_module._build_request(values)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_build_request_rejects_empty_analysts():
    values = web_app_module._default_form_values()
    values["analysts"] = []
    try:
        web_app_module._build_request(values)
    except ValueError as exc:
        assert "至少需要选择一个分析师" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_web_routes(monkeypatch, tmp_path):
    monkeypatch.setattr(web_app_module, "AShareDataProvider", FakeProvider)
    monkeypatch.setattr(web_app_module, "create_llm", lambda settings, mock=False: FakeLLM())

    class _S:
        reports_dir = tmp_path

    monkeypatch.setattr(web_app_module, "load_settings", lambda: _S())

    app = web_app_module.create_web_app()
    client = TestClient(app)

    r = client.get("/")
    assert r.status_code == 200

    r = client.post(
        "/analyze",
        data={
            "symbol": "000001",
            "trade_date": "2026-05-16",
            "depth": "quick",
            "analysts": ["market"],
            "data_source": "tushare",
            "mock_llm": "on",
        },
    )
    assert r.status_code == 200

    report_file = tmp_path / "000001_2026-05-16.md"
    assert report_file.exists()

    r = client.get("/reports")
    assert r.status_code == 200
    assert "000001_2026-05-16.md" in r.text

    r = client.get("/reports/000001_2026-05-16.md")
    assert r.status_code == 200
    assert "Nano A股分析报告" in r.text
