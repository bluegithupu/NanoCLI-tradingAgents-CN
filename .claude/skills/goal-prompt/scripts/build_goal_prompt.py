#!/usr/bin/env python3
"""Build a full /goal prompt from a short task description."""

from __future__ import annotations

import argparse
from pathlib import Path


BUGFIX_KEYWORDS = ("修复", "bug", "报错", "异常", "回归", "失败", "错误", "fix")
RELEASE_KEYWORDS = ("发布", "上线", "ready", "闸门", "审计", "质量", "release")


def infer_mode(task: str) -> str:
    lower = task.lower()
    if any(k in lower for k in BUGFIX_KEYWORDS):
        return "bugfix"
    if any(k in lower for k in RELEASE_KEYWORDS):
        return "release"
    return "feature"


def bugfix_prompt(project: str, task: str) -> str:
    return f"""目标：在 {project} 中完成“{task}”的缺陷修复闭环，严格使用 TDD，并保持最小改动。

工作约束：
- 回复与注释使用中文。
- 遵循仓库 AGENTS.md：单一功能原则、验证优先、会话结束更新 progress.md 与 feature_list.json。
- 只修改与该缺陷直接相关的文件；不要做顺手重构。
- 如果信息不足，先声明假设并选择最保守实现。
- 不使用破坏性 git 命令。

执行步骤：
1) 读取上下文：AGENTS.md、docs/ARCHITECTURE.md、main.py、tests/ 相关测试。
2) 明确缺陷定义：给出当前行为、期望行为、复现输入、影响范围。
3) 先写失败测试：新增或扩展最小测试并确认失败（红灯）。
4) 实现最小修复：仅改必要代码，不引入未请求的新抽象。
5) 验证：运行 uv run pytest tests/ -v，必要时补充定向测试命令。
6) 状态更新：在 progress.md 追加修复记录；在 feature_list.json 更新对应 evidence（若适用）。
7) 输出结果：列出改动文件、改动目的、关键测试结果、残余风险。

完成标准（必须全部满足）：
- 至少一个“先失败后通过”的测试证明修复有效。
- 全量测试通过，或明确说明阻塞原因与证据。
- progress.md 与 feature_list.json 已更新且内容与本次改动一致。
- 提供可复现的执行与验证命令。"""


def feature_prompt(project: str, task: str) -> str:
    return f"""目标：在 {project} 完成“{task}”的单功能端到端交付（测试、实现、验证、状态同步），要求可复现、可维护。

功能范围：
- 只实现一个功能，不并行做第二个功能。
- 采用最小实现策略：先可用，再完善，不做超范围设计。

执行流程：
1) 前置检查：阅读 AGENTS.md、docs/ARCHITECTURE.md、feature_list.json、progress.md，并运行 ./init.sh。
2) 需求冻结：用 5-10 行定义输入、输出、非目标、兼容性要求。
3) 测试先行（TDD）：先写测试并确认新增测试先失败。
4) 实现：仅在必要模块改动，保持现有代码风格。
5) 验证：运行 uv run pytest tests/ -v；如适用再运行 uv run mypy main.py。
6) 文档与状态：更新 feature_list.json 与 progress.md，记录证据与风险。
7) 交付输出：提供改动清单、验收结果、后续最小下一步。

完成标准：
- 新功能有自动化测试证明，且测试通过。
- 不引入与目标无关代码。
- 状态文件已更新且与真实结果一致。
- 给出“仓库可重启并复现”的验证说明。"""


def release_prompt(project: str, task: str) -> str:
    return f"""目标：围绕“{task}”，对 {project} 执行一次发布前质量闸门检查与必要修正，输出可审计结论（Ready/Not Ready）。

范围与原则：
- 优先级：正确性 > 安全性 > 可维护性。
- 仅修复会阻塞发布的问题；非阻塞项记录为风险，不做扩展开发。
- 所有结论必须有命令输出或代码证据支撑。

执行步骤：
1) 基线确认：读取 AGENTS.md、docs/ARCHITECTURE.md、feature_list.json、progress.md，整理已知风险。
2) 自动化闸门：运行 uv run pytest tests/ -v；如适用运行 uv run mypy main.py。
3) 定向修复：仅处理阻塞与高风险问题，并补回归测试（若合理）。
4) 安全与配置审计：检查密钥管理、注入风险入口、基础配置完整性。
5) 文档与状态：在 progress.md 记录闸门结果；在 feature_list.json 更新 evidence。
6) 最终判定：输出 Ready 或 Not Ready，并给出最小阻塞清单。

完成标准：
- 给出明确发布结论及证据链。
- 阻塞问题已修复并验证，或已形成可执行阻塞清单。
- 状态文件更新完成，可供下一会话直接接手。"""


def build_prompt(project: str, task: str, mode: str) -> str:
    selected = infer_mode(task) if mode == "auto" else mode
    if selected == "bugfix":
        return bugfix_prompt(project, task)
    if selected == "release":
        return release_prompt(project, task)
    return feature_prompt(project, task)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build full /goal prompt from short task")
    parser.add_argument("--project", required=True, help="Project path")
    parser.add_argument("--task", required=True, help="Short task description")
    parser.add_argument(
        "--mode",
        choices=("auto", "bugfix", "feature", "release"),
        default="auto",
        help="Goal prompt template mode",
    )
    parser.add_argument("--output", help="Optional output file path")
    args = parser.parse_args()

    prompt = build_prompt(args.project, args.task, args.mode)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(prompt + "\n", encoding="utf-8")
        print(f"已写入: {output_path}")
        return

    print(prompt)


if __name__ == "__main__":
    main()
