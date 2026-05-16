from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from nano_tradingagents.agents import run_analysis_pipeline
from nano_tradingagents.config import load_settings, normalize_depth, parse_analysts, parse_data_source
from nano_tradingagents.data.ashare import AShareDataProvider, validate_ashare_symbol
from nano_tradingagents.llm import create_llm
from nano_tradingagents.models import AnalysisRequest
from nano_tradingagents.reporting import save_report


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_web_app() -> FastAPI:
    app = FastAPI(title="Nano TradingAgents Web", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            context={
                "error": "",
                "values": _default_form_values(),
            },
        )

    @app.post("/analyze", response_class=HTMLResponse)
    async def analyze(request: Request) -> HTMLResponse:
        values = _default_form_values()
        try:
            values = _parse_form_values(await request.body(), defaults=values)
            analysis_request = _build_request(values)
        except Exception as exc:
            return templates.TemplateResponse(
                request,
                "index.html",
                context={"error": str(exc), "values": values},
                status_code=400,
            )

        try:
            settings = load_settings()
            llm = create_llm(settings, mock=values["mock_llm"])
            provider = AShareDataProvider(data_source=analysis_request.data_source)

            progress_logs: List[str] = []

            def progress(msg: str) -> None:
                progress_logs.append(msg)

            state = run_analysis_pipeline(analysis_request, llm, provider, progress=progress)
            report_path = save_report(state, analysis_request.report_dir)

            return templates.TemplateResponse(
                request,
                "result.html",
                context={
                    "state": state,
                    "report_name": report_path.name,
                    "report_relpath": str(report_path),
                    "progress_logs": progress_logs,
                },
            )
        except Exception as exc:
            return templates.TemplateResponse(
                request,
                "index.html",
                context={"error": f"分析执行失败: {exc}", "values": values},
                status_code=500,
            )

    @app.get("/reports", response_class=HTMLResponse)
    async def reports(request: Request) -> HTMLResponse:
        report_dir = load_settings().reports_dir
        items = list_reports(report_dir)
        return templates.TemplateResponse(
            request,
            "reports.html",
            context={"reports": items},
        )

    @app.get("/reports/{name}", response_class=HTMLResponse)
    async def report_detail(request: Request, name: str) -> HTMLResponse:
        report_dir = load_settings().reports_dir
        path = resolve_report_path(report_dir, name)
        if path is None:
            raise HTTPException(status_code=404, detail="报告不存在")
        content = path.read_text(encoding="utf-8")
        return templates.TemplateResponse(
            request,
            "report_detail.html",
            context={"name": path.name, "content": content},
        )

    return app


def _default_form_values() -> Dict[str, object]:
    today = date.today().strftime("%Y-%m-%d")
    return {
        "symbol": "000001",
        "trade_date": today,
        "depth": "quick",
        "analysts": ["market", "fundamentals", "news"],
        "data_source": "tushare",
        "mock_llm": True,
    }


def _parse_form_values(body: bytes, defaults: Dict[str, object]) -> Dict[str, object]:
    raw = parse_qs(body.decode("utf-8"), keep_blank_values=True)

    def _get(key: str, default: str = "") -> str:
        values = raw.get(key)
        if not values:
            return default
        return values[-1].strip()

    parsed = dict(defaults)
    parsed["symbol"] = _get("symbol", str(defaults["symbol"]))
    parsed["trade_date"] = _get("trade_date", str(defaults["trade_date"]))
    parsed["depth"] = _get("depth", str(defaults["depth"]))
    parsed["analysts"] = [item.strip() for item in raw.get("analysts", []) if item.strip()]
    parsed["data_source"] = _get("data_source", str(defaults["data_source"]))
    parsed["mock_llm"] = _to_bool(_get("mock_llm", ""))
    return parsed


def _build_request(values: Dict[str, object]) -> AnalysisRequest:
    symbol = validate_ashare_symbol(str(values["symbol"]))
    trade_date = str(values["trade_date"]).strip()
    if not trade_date:
        trade_date = date.today().strftime("%Y-%m-%d")
    _ = datetime.strptime(trade_date, "%Y-%m-%d")

    depth = normalize_depth(str(values["depth"]))
    analysts_value = values.get("analysts", [])
    if isinstance(analysts_value, list):
        if not analysts_value:
            raise ValueError("至少需要选择一个分析师")
        analysts = parse_analysts(",".join(str(item) for item in analysts_value))
    else:
        analysts = parse_analysts(str(analysts_value))
    data_source = parse_data_source(str(values["data_source"]))

    return AnalysisRequest(
        symbol=symbol,
        trade_date=trade_date,
        depth=depth,
        data_source=data_source,
        analysts=analysts,
        report_dir=load_settings().reports_dir,
        mock_llm=bool(values["mock_llm"]),
    )


def _to_bool(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "on", "yes", "y"}


def list_reports(report_dir: Path) -> List[Dict[str, str]]:
    if not report_dir.exists() or not report_dir.is_dir():
        return []

    def _sort_key(path: Path) -> float:
        return path.stat().st_mtime

    rows: List[Dict[str, str]] = []
    for path in sorted(report_dir.glob("*.md"), key=_sort_key, reverse=True):
        stat = path.stat()
        rows.append(
            {
                "name": path.name,
                "updated_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "size_kb": f"{stat.st_size / 1024:.1f}",
            }
        )
    return rows


def resolve_report_path(report_dir: Path, name: str) -> Optional[Path]:
    if not name or Path(name).name != name or not name.endswith(".md"):
        return None

    base = report_dir.resolve()
    target = (base / name).resolve()
    if target.parent != base:
        return None
    if not target.exists() or not target.is_file():
        return None
    return target
