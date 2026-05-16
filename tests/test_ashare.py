import pandas as pd
import pytest

from nano_tradingagents.data.ashare import AShareDataProvider, validate_ashare_symbol
from nano_tradingagents.data.tushare_provider import TushareDataProvider


class FakeAK:
    def stock_individual_info_em(self, symbol):
        return pd.DataFrame([
            {"item": "股票简称", "value": "平安银行"},
            {"item": "行业", "value": "银行"},
            {"item": "总市值", "value": "1000亿"},
        ])

    def stock_zh_a_hist(self, symbol, period, start_date, end_date, adjust):
        rows = []
        for idx in range(30):
            rows.append({
                "日期": f"2026-04-{idx + 1:02d}",
                "开盘": 10 + idx * 0.1,
                "收盘": 10 + idx * 0.2,
                "最高": 10.5 + idx * 0.2,
                "最低": 9.8 + idx * 0.2,
                "成交量": 100000 + idx,
                "涨跌幅": 1.0,
            })
        return pd.DataFrame(rows)

    def stock_financial_analysis_indicator(self, symbol):
        return pd.DataFrame([{
            "净资产收益率(%)": "12.3",
            "销售净利率(%)": "20.1",
            "资产负债率(%)": "55.0",
            "每股收益(元)": "1.23",
        }])

    def stock_news_em(self, symbol):
        return pd.DataFrame([{
            "新闻标题": "公司发布公告",
            "发布时间": "2026-05-08 10:00:00",
            "文章来源": "东方财富",
            "新闻链接": "https://example.com",
        }])


def test_validate_ashare_symbol():
    assert validate_ashare_symbol("000001") == "000001"
    with pytest.raises(ValueError):
        validate_ashare_symbol("AAPL")


def test_provider_load_snapshot_with_fake_ak():
    provider = AShareDataProvider(ak_module=FakeAK())
    snapshot = provider.load_snapshot("000001", "2026-05-08", "quick")
    assert snapshot.name == "平安银行"
    assert snapshot.indicators["latest_close"] is not None
    assert snapshot.fundamentals["行业"] == "银行"
    assert snapshot.news[0]["title"] == "公司发布公告"


class FakeAKBroken:
    def stock_individual_info_em(self, symbol):
        raise RuntimeError("ak broken")

    def stock_zh_a_hist(self, symbol, period, start_date, end_date, adjust):
        raise RuntimeError("ak broken")

    def stock_financial_analysis_indicator(self, symbol):
        raise RuntimeError("ak broken")

    def stock_news_em(self, symbol):
        return pd.DataFrame([{
            "新闻标题": "新闻可用",
            "发布时间": "2026-05-08 10:00:00",
            "文章来源": "东方财富",
            "新闻链接": "https://example.com",
        }])


class FakePro:
    def stock_basic(self, ts_code=None, fields=None, **kwargs):
        if fields == "ts_code,name":
            return pd.DataFrame([{"ts_code": ts_code, "name": "平安银行"}])
        return pd.DataFrame([{"ts_code": ts_code, "name": "平安银行", "industry": "银行", "list_date": "19910403"}])

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
        self._pro = FakePro()

    def pro_api(self, token):
        return self._pro

    def pro_bar(self, **kwargs):
        return None


def test_provider_fallback_to_tushare_when_ak_fails():
    tushare = TushareDataProvider(token="fake-token", ts_module=FakeTS())
    provider = AShareDataProvider(ak_module=FakeAKBroken(), tushare_provider=tushare, data_source="akshare")
    snapshot = provider.load_snapshot("000001", "2026-05-08", "quick")
    assert snapshot.name == "平安银行"
    assert snapshot.indicators["latest_close"] is not None
    assert snapshot.fundamentals["行业"] == "银行"
    assert any("回退到 Tushare" in w for w in snapshot.warnings)


def test_provider_tushare_first_strategy_uses_tushare_when_both_available():
    tushare = TushareDataProvider(token="fake-token", ts_module=FakeTS())
    provider = AShareDataProvider(ak_module=FakeAK(), tushare_provider=tushare, data_source="tushare")
    snapshot = provider.load_snapshot("000001", "2026-05-08", "quick")
    assert snapshot.name == "平安银行"
    assert snapshot.fundamentals["行业"] == "银行"
    # FakeTS 历史最新收盘为 10.7，FakeAK 为更大序列值；用于确认主源优先级
    assert abs(snapshot.indicators["latest_close"] - 10.7) < 1e-6
