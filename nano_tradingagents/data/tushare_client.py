from __future__ import annotations

import os
from typing import Optional


DEFAULT_TUSHARE_HTTP_URL = "http://118.89.66.41:8010/"


def create_tushare_pro_client(token: Optional[str] = None, ts_module=None, http_url: Optional[str] = None):
    """
    统一初始化 Tushare Pro 客户端。

    初始化规则：
    1) token 参数优先；否则读取环境变量 TUSHARE_TOKEN。
    2) 强制设置 pro._DataApi__http_url（可通过参数或环境变量覆盖）。

    注意：
    - 不在仓库内硬编码 token；请通过 .env / 环境变量提供。
    - 若报 token 相关错误，请确认 _DataApi__http_url 已设置到指定地址。
    """
    if ts_module is None:
        import tushare as ts  # type: ignore
    else:
        ts = ts_module

    final_token = (token if token is not None else os.getenv("TUSHARE_TOKEN", "")).strip()
    if not final_token:
        raise ValueError("缺少 TUSHARE_TOKEN，请在 .env 或环境变量中配置")

    pro = ts.pro_api(final_token)

    final_http_url = (
        http_url
        or os.getenv("TUSHARE_HTTP_URL", "").strip()
        or DEFAULT_TUSHARE_HTTP_URL
    )
    pro._DataApi__http_url = final_http_url

    return pro
