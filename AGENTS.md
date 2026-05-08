# AGENTS.md

NanoCLI-tradingAgents-CN 是一个精简的 A 股多智能体分析 CLI，核心目标是用 AKShare 数据和 OpenAI 兼容 LLM 生成 Markdown 投资分析报告。

## 启动流程

开始写代码前：

1. 确认目录：`pwd`
2. 完整阅读本文件
3. 阅读 `README.md` 和 `pyproject.toml`
4. 运行 `./init.sh` 确认基础验证通过
5. 阅读 `feature_list.json` 和 `progress.md`
6. 查看最近提交：`git log --oneline -5`

如果 `./init.sh` 已经失败，先判断失败是否和当前任务相关；相关则优先修复，不相关则在回复中说明。

## 工作规则

- 使用中文回复，除非用户特别说明。
- 一次只处理一个明确目标，不顺手重构无关代码。
- 优先保持实现简单，匹配当前 Python CLI 的结构和风格。
- 不把真实 LLM API、网络数据源或行情接口作为默认验证前提。
- 不提交或泄露 `.env`、API Key、报告中的敏感配置。
- 修改行为时优先补充或更新对应测试。

## 项目约定

- Python 版本：`>=3.10,<3.13`
- 包入口：`nano_tradingagents`
- CLI 命令：`nano-trading`
- 测试目录：`tests`
- 默认报告目录：`reports`
- 低成本人工 smoke test：

```bash
nano-trading analyze 000001 --date 2026-05-08 --depth quick --analysts market --mock-llm --report-dir /tmp/nano-reports
```

## 必需工件

- `feature_list.json`：功能状态和完成证据
- `progress.md`：会话连续性记录
- `init.sh`：标准初始化和基础验证入口
- `session-handoff.md`：较长任务或中断前的交接模板

## 验证命令

```bash
./init.sh
```

`init.sh` 当前执行项目测试：

```bash
.venv/bin/python -m pytest -q
```

如果没有 `.venv`，脚本会回退到系统 `python3` 或 `python`。

## 完成定义

一个任务完成必须满足：

- [ ] 目标行为已实现
- [ ] 相关测试已新增或更新，除非任务不涉及代码行为
- [ ] `./init.sh` 已运行，或明确说明无法运行的原因
- [ ] `progress.md` 已记录本次状态、验证结果和剩余风险
- [ ] 如涉及功能状态变化，`feature_list.json` 已同步更新

## 会话结束

结束前：

1. 更新 `progress.md`
2. 必要时更新 `feature_list.json`
3. 记录未解决的 blocker 或风险
4. 确保下一次会话可以从 `./init.sh` 和 `progress.md` 接续

