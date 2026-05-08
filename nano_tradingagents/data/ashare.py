from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from nano_tradingagents.models import AShareSnapshot


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
    """AKShare-first A-share data provider with explicit degraded results."""

    def __init__(self, ak_module=None):
        self._ak = ak_module

    @property
    def ak(self):
        if self._ak is None:
            try:
                import akshare as ak  # type: ignore
            except Exception as exc:
                raise RuntimeError("AKShare 未安装或不可用，请安装 akshare 后重试") from exc
            self._ak = ak
        return self._ak

    def load_snapshot(self, symbol: str, trade_date: str, depth: str = "standard") -> AShareSnapshot:
        symbol = validate_ashare_symbol(symbol)
        warnings: List[str] = []
        name = self._get_stock_name(symbol, warnings)
        price_df = self._get_history(symbol, trade_date, depth, warnings)
        indicators = self._calculate_indicators(price_df, warnings)
        price_table = self._format_price_table(price_df)
        fundamentals = self._get_fundamentals(symbol, warnings)
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

    def _get_stock_name(self, symbol: str, warnings: List[str]) -> str:
        try:
            df = self.ak.stock_individual_info_em(symbol=symbol)
            if isinstance(df, pd.DataFrame) and not df.empty:
                key_col = "item" if "item" in df.columns else df.columns[0]
                val_col = "value" if "value" in df.columns else df.columns[-1]
                rows = df[df[key_col].astype(str).str.contains("股票简称|股票名称", na=False)]
                if not rows.empty:
                    return str(rows.iloc[0][val_col])
        except Exception as exc:
            warnings.append(f"股票名称获取失败: {exc}")
        return f"股票{symbol}"

    def _get_history(self, symbol: str, trade_date: str, depth: str, warnings: List[str]) -> pd.DataFrame:
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
                warnings.append("行情数据为空")
                return pd.DataFrame()
            return df.tail(120).copy()
        except Exception as exc:
            warnings.append(f"行情数据获取失败: {exc}")
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

    def _get_fundamentals(self, symbol: str, warnings: List[str]) -> Dict[str, Optional[str]]:
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
            warnings.append(f"基本信息获取失败: {exc}")
        try:
            indicator_df = self.ak.stock_financial_analysis_indicator(symbol=symbol)
            if isinstance(indicator_df, pd.DataFrame) and not indicator_df.empty:
                latest = indicator_df.iloc[0]
                for key in ["净资产收益率(%)", "销售净利率(%)", "资产负债率(%)", "每股收益(元)"]:
                    if key in indicator_df.columns:
                        data[key] = str(latest[key])
        except Exception as exc:
            warnings.append(f"财务指标获取失败: {exc}")
        return data

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

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        lower_map = {str(col).lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
            if candidate.lower() in lower_map:
                return lower_map[candidate.lower()]
        return None
