import pandas as pd

from nano_tradingagents.data.tushare_provider import TushareDataProvider


class FakePro:
    def stock_basic(self, ts_code=None, fields=None, **kwargs):
        if fields == "ts_code,name":
            return pd.DataFrame([{"ts_code": ts_code, "name": "平安银行"}])
        if "industry" in (fields or ""):
            return pd.DataFrame([{"ts_code": ts_code, "name": "平安银行", "industry": "银行", "list_date": "19910403"}])
        return pd.DataFrame()

    def daily(self, ts_code=None, start_date=None, end_date=None):
        return pd.DataFrame([
            {"ts_code": ts_code, "trade_date": "20260507", "open": 10.0, "close": 10.5, "high": 10.8, "low": 9.9, "vol": 1000, "pct_chg": 1.0},
            {"ts_code": ts_code, "trade_date": "20260508", "open": 10.5, "close": 10.7, "high": 10.9, "low": 10.2, "vol": 1200, "pct_chg": 1.9},
        ])

    def daily_basic(self, ts_code=None, trade_date=None, fields=None):
        if trade_date == "20260508":
            return pd.DataFrame([{"ts_code": ts_code, "trade_date": trade_date, "total_mv": 1000000, "circ_mv": 800000, "pe": 8.5, "pb": 1.2, "pe_ttm": 8.3}])
        return pd.DataFrame()

    def fina_indicator(self, ts_code=None, limit=None, fields=None):
        return pd.DataFrame([{"ts_code": ts_code, "end_date": "20250331", "roe": 12.3, "netprofit_margin": 20.1, "debt_to_assets": 55.0, "eps": 1.23}])


class FakeTS:
    def __init__(self):
        self.last_token = None
        self._pro = FakePro()

    def pro_api(self, token):
        self.last_token = token
        return self._pro

    def pro_bar(self, **kwargs):
        return None


def test_tushare_provider_history_and_fundamentals():
    fake_ts = FakeTS()
    provider = TushareDataProvider(token="fake-token", ts_module=fake_ts)
    name = provider.get_stock_name("000001")
    assert name == "平安银行"
    assert fake_ts.last_token == "fake-token"

    history = provider.get_history("000001", "2026-05-08", depth="quick")
    assert not history.empty
    assert "收盘" in history.columns
    assert history.iloc[-1]["日期"] == "2026-05-08"

    fundamentals = provider.get_fundamentals("000001", "2026-05-08")
    assert fundamentals["行业"] == "银行"
    assert fundamentals["净资产收益率(%)"] == "12.3"
