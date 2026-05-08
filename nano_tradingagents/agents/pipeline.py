from __future__ import annotations

from typing import Callable, Dict, List

from nano_tradingagents.data.ashare import AShareDataProvider
from nano_tradingagents.llm import BaseLLM, format_dict, render_context
from nano_tradingagents.models import AgentState, AnalysisRequest


ProgressCallback = Callable[[str], None]


def run_analysis_pipeline(
    request: AnalysisRequest,
    llm: BaseLLM,
    data_provider: AShareDataProvider,
    progress: ProgressCallback | None = None,
) -> AgentState:
    state = AgentState(request=request)
    _emit(progress, "加载 A 股数据")
    state.snapshot = data_provider.load_snapshot(request.symbol, request.trade_date, request.depth)

    if "market" in request.analysts:
        _emit(progress, "运行技术面分析师")
        state.add_report("market", _market_report(state, llm))
    if "fundamentals" in request.analysts:
        _emit(progress, "运行基本面分析师")
        state.add_report("fundamentals", _fundamentals_report(state, llm))
    if "news" in request.analysts:
        _emit(progress, "运行新闻分析师")
        state.add_report("news", _news_report(state, llm))

    _emit(progress, "生成看多/看空观点")
    state.add_report("bull", _stance_report(state, llm, bullish=True))
    state.add_report("bear", _stance_report(state, llm, bullish=False))

    _emit(progress, "生成交易员建议")
    state.add_report("trader", _trader_report(state, llm))

    _emit(progress, "生成风险决策")
    risk_report = _risk_report(state, llm)
    state.add_report("risk", risk_report)
    state.final_decision = _extract_decision(state)
    return state


def _emit(progress: ProgressCallback | None, message: str) -> None:
    if progress:
        progress(message)


def _snapshot_context(state: AgentState) -> str:
    snapshot = state.snapshot
    if snapshot is None:
        return "无数据"
    news_text = "\n".join(
        f"- {item.get('time', '')} {item.get('source', '')}: {item.get('title', '')}"
        for item in snapshot.news
    ) or "无可用新闻"
    warnings = "\n".join(f"- {item}" for item in snapshot.warnings) or "无"
    return render_context([
        f"股票: {snapshot.name}({snapshot.symbol})",
        f"分析日期: {snapshot.trade_date}",
        "技术指标:\n" + format_dict(snapshot.indicators),
        "最近行情:\n" + snapshot.price_table,
        "基本面快照:\n" + format_dict(snapshot.fundamentals),
        "相关新闻:\n" + news_text,
        "数据限制:\n" + warnings,
    ])


def _market_report(state: AgentState, llm: BaseLLM) -> str:
    return llm.complete(
        "你是 A 股技术面分析师。必须使用中文，基于给定真实数据，不得编造。输出包含趋势、指标、支撑阻力和技术面建议。",
        _snapshot_context(state),
    )


def _fundamentals_report(state: AgentState, llm: BaseLLM) -> str:
    return llm.complete(
        "你是 A 股基本面分析师。必须使用中文，基于给定基本面和价格数据，不得编造。输出包含估值、质量、风险和基本面建议。",
        _snapshot_context(state),
    )


def _news_report(state: AgentState, llm: BaseLLM) -> str:
    return llm.complete(
        "你是 A 股新闻分析师。必须使用中文，聚焦新闻时效性、利好利空、潜在催化和风险。缺少新闻时要明确说明。",
        _snapshot_context(state),
    )


def _stance_report(state: AgentState, llm: BaseLLM, bullish: bool) -> str:
    role = "看多研究员" if bullish else "看空研究员"
    angle = "提炼支持买入或持有的正面理由" if bullish else "提炼需要回避、减仓或等待的负面理由"
    return llm.complete(
        f"你是 A 股{role}。请{angle}，必须引用已有分析报告中的依据，不得新增未经提供的数据。",
        _reports_context(state),
    )


def _trader_report(state: AgentState, llm: BaseLLM) -> str:
    return llm.complete(
        "你是 A 股交易员。综合分析师、看多和看空观点，给出明确操作建议：买入、持有、卖出或观望。必须包含仓位、触发条件和止损/风控点。",
        _reports_context(state),
    )


def _risk_report(state: AgentState, llm: BaseLLM) -> str:
    return llm.complete(
        "你是 A 股风险经理。审核交易员建议，输出最终风险结论。必须包含最终动作、主要风险、适用投资者和免责声明。",
        _reports_context(state),
    )


def _reports_context(state: AgentState) -> str:
    snapshot_text = _snapshot_context(state)
    reports = "\n\n".join(f"## {name}\n{content}" for name, content in state.reports.items())
    return render_context([snapshot_text, reports])


def _extract_decision(state: AgentState) -> Dict[str, str]:
    risk = state.reports.get("risk", "")
    trader = state.reports.get("trader", "")
    combined = f"{risk}\n{trader}"
    action = "观望"
    for candidate in ["买入", "卖出", "持有", "观望", "减仓"]:
        if candidate in combined:
            action = candidate
            break
    return {
        "symbol": state.request.symbol,
        "date": state.request.trade_date,
        "action": action,
        "summary": risk[:300] if risk else trader[:300],
    }
