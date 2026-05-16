from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from nano_tradingagents.models import AShareSnapshot
from nano_tradingagents.data.tushare_provider import TushareDataProvider


A_SHARE_RE = re.compile(r"^\d{6}$")


def validate_ashare_symbol(symbol: str) -> str:
    cleaned = str(symbol or "").strip()
    if not A_SHARE_RE.match(cleaned):
        raise ValueError("Nano 版仅支持 6 位 A 股代码，例如 000001、600519")
    return cleaned


def _market_prefix(symbol: str) -> str:
    if symbol.startswith(("6", "9")):
        return f"sh{symbol}"
    return f"sz{symbol}"


def _date_compact(value: str) -> str:
    return value.replace("-", "")


def _safe_float(value) -> Optional[float]:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


class AShareDataProvider:
    """A-share data provider with configurable source priority."""

    def __init__(
        self,
        ak_module=None,
        tushare_provider: Optional[TushareDataProvider] = None,
        data_source: str = "tushare",
    ):
        self._ak = ak_module
        self._tushare = tushare_provider
        self.data_source = (data_source or "tushare").strip().lower()
        if self.data_source not in {"tushare", "akshare", "auto"}:
            raise ValueError("不支持的数据源策略: {0}，支持: tushare, akshare, auto".format(data_source))

    @property
    def ak(self):
        if self._ak is None:
            try:
                import akshare as ak  # type: ignore
            except Exception as exc:
                raise RuntimeError("AKShare 未安装或不可用，请安装 akshare 后重试") from exc
            self._ak = ak
        return self._ak

    @property
    def tushare(self) -> TushareDataProvider:
        if self._tushare is None:
            self._tushare = TushareDataProvider()
        return self._tushare

    def load_snapshot(self, symbol: str, trade_date: str, depth: str = "standard") -> AShareSnapshot:
        symbol = validate_ashare_symbol(symbol)
        warnings: List[str] = []
        name = self._get_stock_name(symbol, trade_date, warnings)
        price_df = self._get_history(symbol, trade_date, depth, warnings)
        indicators = self._calculate_indicators(price_df, warnings)
        price_table = self._format_price_table(price_df)
        fundamentals = self._get_fundamentals(symbol, trade_date, warnings)
        news = self._get_news(symbol, warnings)
        return AShareSnapshot(
            symbol=symbol,
            name=name,
            trade_date=trade_date,
            price_table=price_table,
            indicators=indicators,
            fundamentals=fundamentals,
            news=news,
            warnings=warnings,
        )

    def _get_stock_name(self, symbol: str, trade_date: str, warnings: List[str]) -> str:
        primary, fallback = self._source_order()
        name = self._get_stock_name_by_source(primary, symbol, warnings, fallback=False)
        if name:
            return name
        if fallback:
            name = self._get_stock_name_by_source(fallback, symbol, warnings, fallback=True)
            if name:
                return name
        return f"股票{symbol}"

    def _get_stock_name_by_source(
        self, source: str, symbol: str, warnings: List[str], fallback: bool
    ) -> Optional[str]:
        if source == "akshare":
            try:
                df = self.ak.stock_individual_info_em(symbol=symbol)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    key_col = "item" if "item" in df.columns else df.columns[0]
                    val_col = "value" if "value" in df.columns else df.columns[-1]
                    rows = df[df[key_col].astype(str).str.contains("股票简称|股票名称", na=False)]
                    if not rows.empty:
                        return str(rows.iloc[0][val_col])
            except Exception as exc:
                msg = "AKShare 股票名称获取失败" if not fallback else "AKShare 股票名称回退失败"
                warnings.append(f"{msg}: {exc}")
            return None
        if source == "tushare":
            if not self.tushare.enabled:
                if not fallback:
                    warnings.append("Tushare 未启用（缺少 TUSHARE_TOKEN）")
                return None
            try:
                name = self.tushare.get_stock_name(symbol)
                if name and fallback:
                    warnings.append("股票名称已回退到 Tushare")
                return name
            except Exception as exc:
                msg = "Tushare 股票名称获取失败" if not fallback else "Tushare 股票名称回退失败"
                warnings.append(f"{msg}: {exc}")
                return None
        return None

    def _get_history(self, symbol: str, trade_date: str, depth: str, warnings: List[str]) -> pd.DataFrame:
        primary, fallback = self._source_order()
        data = self._get_history_by_source(primary, symbol, trade_date, depth, warnings, fallback=False)
        if not data.empty:
            return data
        if fallback:
            data = self._get_history_by_source(fallback, symbol, trade_date, depth, warnings, fallback=True)
            if not data.empty:
                return data
        return pd.DataFrame()

    def _get_history_by_source(
        self, source: str, symbol: str, trade_date: str, depth: str, warnings: List[str], fallback: bool
    ) -> pd.DataFrame:
        if source == "akshare":
            return self._get_history_from_akshare(symbol, trade_date, depth, warnings, fallback)
        if source == "tushare":
            return self._get_history_from_tushare(symbol, trade_date, depth, warnings, fallback)
        return pd.DataFrame()

    def _get_history_from_akshare(
        self, symbol: str, trade_date: str, depth: str, warnings: List[str], fallback: bool
    ) -> pd.DataFrame:
        days = {"quick": 90, "standard": 180, "deep": 365}.get(depth, 180)
        end = datetime.strptime(trade_date, "%Y-%m-%d")
        start = end - timedelta(days=days)
        try:
            df = self.ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=_date_compact(start.strftime("%Y-%m-%d")),
                end_date=_date_compact(trade_date),
                adjust="qfq",
            )
            if not isinstance(df, pd.DataFrame) or df.empty:
                if not fallback:
                    warnings.append("AKShare 行情数据为空")
                return pd.DataFrame()
            return df.tail(120).copy()
        except Exception as exc:
            msg = "AKShare 行情数据获取失败" if not fallback else "AKShare 行情回退失败"
            warnings.append(f"{msg}: {exc}")
            return pd.DataFrame()

    def _get_history_from_tushare(
        self, symbol: str, trade_date: str, depth: str, warnings: List[str], fallback: bool
    ) -> pd.DataFrame:
        if not self.tushare.enabled:
            if not fallback:
                warnings.append("Tushare 未启用（缺少 TUSHARE_TOKEN）")
            return pd.DataFrame()
        try:
            df = self.tushare.get_history(symbol, trade_date, depth)
            if isinstance(df, pd.DataFrame) and not df.empty:
                if fallback:
                    warnings.append("行情数据已回退到 Tushare")
                return df
            if not fallback:
                warnings.append("Tushare 行情数据为空")
            return pd.DataFrame()
        except Exception as exc:
            msg = "Tushare 行情获取失败" if not fallback else "Tushare 行情回退失败"
            warnings.append(f"{msg}: {exc}")
        return pd.DataFrame()

    def _calculate_indicators(self, df: pd.DataFrame, warnings: List[str]) -> Dict[str, Optional[float]]:
        if df.empty:
            return {}
        close_col = self._find_col(df, ["收盘", "close"])
        high_col = self._find_col(df, ["最高", "high"])
        low_col = self._find_col(df, ["最低", "low"])
        volume_col = self._find_col(df, ["成交量", "volume"])
        if not close_col:
            warnings.append("行情数据缺少收盘价字段，无法计算技术指标")
            return {}
        close = pd.to_numeric(df[close_col], errors="coerce")
        latest = close.iloc[-1]
        ma5 = close.rolling(5).mean().iloc[-1] if len(close) >= 5 else None
        ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, pd.NA)
        rsi14 = 100 - (100 / (1 + rs))
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        result = {
            "latest_close": _safe_float(latest),
            "ma5": _safe_float(ma5),
            "ma20": _safe_float(ma20),
            "rsi14": _safe_float(rsi14.iloc[-1]) if len(rsi14) else None,
            "macd": _safe_float(macd.iloc[-1]) if len(macd) else None,
            "macd_signal": _safe_float(signal.iloc[-1]) if len(signal) else None,
        }
        if high_col:
            result["latest_high"] = _safe_float(df.iloc[-1][high_col])
        if low_col:
            result["latest_low"] = _safe_float(df.iloc[-1][low_col])
        if volume_col:
            result["latest_volume"] = _safe_float(df.iloc[-1][volume_col])
        return result

    def _format_price_table(self, df: pd.DataFrame) -> str:
        if df.empty:
            return "行情数据不可用"
        cols = [col for col in ["日期", "开盘", "收盘", "最高", "最低", "成交量", "涨跌幅"] if col in df.columns]
        if not cols:
            return df.tail(10).to_markdown(index=False)
        return df[cols].tail(10).to_markdown(index=False)

    def _get_fundamentals(self, symbol: str, trade_date: str, warnings: List[str]) -> Dict[str, Optional[str]]:
        primary, fallback = self._source_order()
        data = self._get_fundamentals_by_source(primary, symbol, trade_date, warnings, fallback=False)
        if data:
            return data
        if fallback:
            data = self._get_fundamentals_by_source(fallback, symbol, trade_date, warnings, fallback=True)
            if data:
                return data
        return {}

    def _get_fundamentals_by_source(
        self, source: str, symbol: str, trade_date: str, warnings: List[str], fallback: bool
    ) -> Dict[str, Optional[str]]:
        if source == "akshare":
            return self._get_fundamentals_from_akshare(symbol, warnings, fallback)
        if source == "tushare":
            return self._get_fundamentals_from_tushare(symbol, trade_date, warnings, fallback)
        return {}

    def _get_fundamentals_from_akshare(
        self, symbol: str, warnings: List[str], fallback: bool
    ) -> Dict[str, Optional[str]]:
        data: Dict[str, Optional[str]] = {}
        try:
            df = self.ak.stock_individual_info_em(symbol=symbol)
            if isinstance(df, pd.DataFrame) and not df.empty:
                key_col = "item" if "item" in df.columns else df.columns[0]
                val_col = "value" if "value" in df.columns else df.columns[-1]
                for _, row in df.iterrows():
                    key = str(row[key_col])
                    if key in {"总市值", "流通市值", "行业", "上市时间", "股票简称"}:
                        data[key] = str(row[val_col])
        except Exception as exc:
            msg = "AKShare 基本信息获取失败" if not fallback else "AKShare 基本面回退失败"
            warnings.append(f"{msg}: {exc}")
        try:
            indicator_df = self.ak.stock_financial_analysis_indicator(symbol=symbol)
            if isinstance(indicator_df, pd.DataFrame) and not indicator_df.empty:
                latest = indicator_df.iloc[0]
                for key in ["净资产收益率(%)", "销售净利率(%)", "资产负债率(%)", "每股收益(元)"]:
                    if key in indicator_df.columns:
                        data[key] = str(latest[key])
        except Exception as exc:
            msg = "AKShare 财务指标获取失败" if not fallback else "AKShare 财务指标回退失败"
            warnings.append(f"{msg}: {exc}")
        return data

    def _get_fundamentals_from_tushare(
        self, symbol: str, trade_date: str, warnings: List[str], fallback: bool
    ) -> Dict[str, Optional[str]]:
        try:
            if self.tushare.enabled:
                data = self.tushare.get_fundamentals(symbol, trade_date)
                if data and fallback:
                    warnings.append("基本面数据已回退到 Tushare")
                return data
            if not fallback:
                warnings.append("Tushare 未启用（缺少 TUSHARE_TOKEN）")
        except Exception as exc:
            msg = "Tushare 基本面获取失败" if not fallback else "Tushare 基本面回退失败"
            warnings.append(f"{msg}: {exc}")
        return {}

    def _get_news(self, symbol: str, warnings: List[str]) -> List[Dict[str, str]]:
        try:
            df = self.ak.stock_news_em(symbol=symbol)
            if not isinstance(df, pd.DataFrame) or df.empty:
                warnings.append("新闻数据为空")
                return []
            title_col = self._find_col(df, ["新闻标题", "标题", "title"])
            time_col = self._find_col(df, ["发布时间", "时间", "time"])
            source_col = self._find_col(df, ["文章来源", "来源", "source"])
            url_col = self._find_col(df, ["新闻链接", "链接", "url"])
            items: List[Dict[str, str]] = []
            for _, row in df.head(8).iterrows():
                items.append({
                    "title": str(row[title_col]) if title_col else "",
                    "time": str(row[time_col]) if time_col else "",
                    "source": str(row[source_col]) if source_col else "",
                    "url": str(row[url_col]) if url_col else "",
                })
            return items
        except Exception as exc:
            warnings.append(f"新闻获取失败: {exc}")
            return []

    def _source_order(self) -> tuple[str, Optional[str]]:
        if self.data_source == "tushare":
            return "tushare", "akshare"
        if self.data_source == "akshare":
            return "akshare", "tushare"
        # auto: 默认与 tushare 一致，后续可扩展更复杂策略
        return "tushare", "akshare"

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        lower_map = {str(col).lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
            if candidate.lower() in lower_map:
                return lower_map[candidate.lower()]
        return None
