from __future__ import annotations

from typing import Dict, Iterable, Optional

from nano_tradingagents.config import Settings


class BaseLLM:
    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError


class MockLLM(BaseLLM):
    def complete(self, system: str, user: str) -> str:
        first_line = system.strip().splitlines()[0] if system.strip() else "分析"
        return (
            f"{first_line}\n\n"
            "这是 mock LLM 输出，用于本地验证流程。基于已提供的数据，建议保持谨慎，"
            "重点关注趋势、估值和新闻催化是否一致。"
        )


class OpenAICompatibleLLM(BaseLLM):
    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ValueError("缺少 OPENAI_API_KEY。可配置 .env，或使用 --mock-llm 运行本地流程验证。")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - dependency issue
            raise RuntimeError("openai 包不可用，请安装项目依赖") from exc
        self.model = settings.openai_model
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.request_timeout,
        )

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        return content.strip()


def create_llm(settings: Settings, mock: bool = False) -> BaseLLM:
    if mock:
        return MockLLM()
    return OpenAICompatibleLLM(settings)


def render_context(parts: Iterable[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def format_dict(data: Dict[str, object]) -> str:
    if not data:
        return "无可用数据"
    return "\n".join(f"- {key}: {value}" for key, value in data.items())
