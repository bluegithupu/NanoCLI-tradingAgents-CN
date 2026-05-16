from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd

from nano_tradingagents.data.tushare_client import create_tushare_pro_client


def _to_ts_code(symbol: str) -> str:
    if symbol.startswith(("6", "9")):
        return f"{symbol}.SH"
    return f"{symbol}.SZ"


def _compact_date(value: str) -> str:
    return value.replace("-", "")


class TushareDataProvider:
    """Minimal Tushare adapter used as fallback when AKShare endpoints fail."""

    def __init__(self, token: Optional[str] = None, ts_module=None):
        self._token = (token if token is not None else os.getenv("TUSHARE_TOKEN", "")).strip()
        self._ts = ts_module
        self._pro = None

    @property
    def enabled(self) -> bool:
        return self._ts is not None or bool(self._token)

    @property
    def ts(self):
        if self._ts is None:
            import tushare as ts  # type: ignore

            self._ts = ts
        return self._ts

    @property
    def pro(self):
        if self._pro is None:
            self._pro = create_tushare_pro_client(
                token=self._token,
                ts_module=self.ts,
            )
        return self._pro

    def get_stock_name(self, symbol: str) -> Optional[str]:
        ts_code = _to_ts_code(symbol)
        df = self.pro.stock_basic(ts_code=ts_code, fields="ts_code,name")
        if not isinstance(df, pd.DataFrame) or df.empty:
            return None
        value = df.iloc[0].get("name")
        if pd.isna(value):
            return None
        return str(value)

    def get_history(self, symbol: str, trade_date: str, depth: str = "standard") -> pd.DataFrame:
        ts_code = _to_ts_code(symbol)
        days = {"quick": 90, "standard": 180, "deep": 365}.get(depth, 180)
        end = datetime.strptime(trade_date, "%Y-%m-%d")
        start = end - timedelta(days=days)

        df = None
        if hasattr(self.ts, "pro_bar"):
            df = self.ts.pro_bar(
                ts_code=ts_code,
                api=self.pro,
                start_date=_compact_date(start.strftime("%Y-%m-%d")),
                end_date=_compact_date(trade_date),
                freq="D",
                adj="qfq",
            )
        if df is None:
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=_compact_date(start.strftime("%Y-%m-%d")),
                end_date=_compact_date(trade_date),
            )

        if not isinstance(df, pd.DataFrame) or df.empty:
            return pd.DataFrame()

        frame = df.copy()
        if "trade_date" in frame.columns:
            frame["trade_date"] = frame["trade_date"].astype(str)
            frame = frame.sort_values("trade_date")

        rename_map = {
            "trade_date": "日期",
            "open": "开盘",
            "close": "收盘",
            "high": "最高",
            "low": "最低",
            "vol": "成交量",
            "pct_chg": "涨跌幅",
        }
        for src, dst in rename_map.items():
            if src in frame.columns:
                frame.rename(columns={src: dst}, inplace=True)

        if "日期" in frame.columns:
            frame["日期"] = pd.to_datetime(frame["日期"], format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")

        return frame.tail(120).reset_index(drop=True)

    def get_fundamentals(self, symbol: str, trade_date: str) -> Dict[str, Optional[str]]:
        ts_code = _to_ts_code(symbol)
        data: Dict[str, Optional[str]] = {}

        basic_df = self.pro.stock_basic(ts_code=ts_code, fields="ts_code,name,industry,list_date")
        if isinstance(basic_df, pd.DataFrame) and not basic_df.empty:
            row = basic_df.iloc[0]
            data["行业"] = str(row.get("industry", "")) or None
            list_date = row.get("list_date")
            if list_date is not None and not pd.isna(list_date):
                data["上市时间"] = str(list_date)
            stock_name = row.get("name")
            if stock_name is not None and not pd.isna(stock_name):
                data["股票简称"] = str(stock_name)

        # daily_basic 仅交易日有值，回溯最多 10 天找最近交易日
        for back in range(0, 10):
            day = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=back)).strftime("%Y%m%d")
            daily_df = self.pro.daily_basic(
                ts_code=ts_code,
                trade_date=day,
                fields="ts_code,trade_date,total_mv,circ_mv,pe,pb,pe_ttm",
            )
            if isinstance(daily_df, pd.DataFrame) and not daily_df.empty:
                row = daily_df.iloc[0]
                if row.get("total_mv") is not None and not pd.isna(row.get("total_mv")):
                    data["总市值"] = f"{float(row['total_mv']) / 10000:.2f}亿"
                if row.get("circ_mv") is not None and not pd.isna(row.get("circ_mv")):
                    data["流通市值"] = f"{float(row['circ_mv']) / 10000:.2f}亿"
                if row.get("pe_ttm") is not None and not pd.isna(row.get("pe_ttm")):
                    data["市盈率TTM"] = str(row.get("pe_ttm"))
                if row.get("pb") is not None and not pd.isna(row.get("pb")):
                    data["市净率"] = str(row.get("pb"))
                break

        indicator_df = self.pro.fina_indicator(
            ts_code=ts_code,
            limit=1,
            fields="ts_code,end_date,roe,netprofit_margin,debt_to_assets,eps",
        )
        if isinstance(indicator_df, pd.DataFrame) and not indicator_df.empty:
            row = indicator_df.iloc[0]
            mapping = {
                "roe": "净资产收益率(%)",
                "netprofit_margin": "销售净利率(%)",
                "debt_to_assets": "资产负债率(%)",
                "eps": "每股收益(元)",
            }
            for src, dst in mapping.items():
                value = row.get(src)
                if value is not None and not pd.isna(value):
                    data[dst] = str(value)

        return data
