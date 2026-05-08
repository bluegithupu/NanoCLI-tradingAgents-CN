import pandas as pd
import pytest

from nano_tradingagents.data.ashare import AShareDataProvider, validate_ashare_symbol


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
