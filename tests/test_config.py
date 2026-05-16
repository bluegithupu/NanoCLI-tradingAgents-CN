import pytest

from nano_tradingagents.config import normalize_depth, parse_analysts, parse_data_source


def test_normalize_depth_supports_cn_and_en():
    assert normalize_depth("快速") == "quick"
    assert normalize_depth("standard") == "standard"


def test_normalize_depth_rejects_unknown():
    with pytest.raises(ValueError):
        normalize_depth("full")


def test_parse_analysts_defaults_and_rejects_unknown():
    assert parse_analysts("") == ["market", "fundamentals", "news"]
    assert parse_analysts("market,news") == ["market", "news"]
    with pytest.raises(ValueError):
        parse_analysts("market,social")


def test_parse_data_source_defaults_and_rejects_unknown():
    assert parse_data_source("") == "tushare"
    assert parse_data_source("akshare") == "akshare"
    assert parse_data_source("auto") == "auto"
    with pytest.raises(ValueError):
        parse_data_source("wind")
