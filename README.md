# NanoCLI-tradingAgents-CN

一个独立、精简的 A 股多智能体分析 CLI。它只保留 A 股分析主链路，去掉原项目中的 FastAPI、Vue、MongoDB、Redis、任务队列和 Web 配置系统。

## 功能

- A 股代码校验与名称识别
- AKShare 优先的数据获取：行情、技术指标、基本面快照、个股新闻
- 精简多智能体链路：技术面、基本面、新闻、看多/看空、交易员、风险经理
- 控制台输出最终结论，并保存 Markdown 报告到 `reports/`

## 安装

推荐使用 Python 3.10-3.12。项目依赖限制为 `<3.13`，避免部分金融/LLM 依赖在更新 Python 版本上的解析问题。

```bash
cd /Users/mac/Code/NanoCLI-tradingAgents-CN
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

如果你使用 `uv`：

```bash
cd /Users/mac/Code/NanoCLI-tradingAgents-CN
uv venv --python 3.10 .venv
uv pip install --python .venv/bin/python -e '.[dev]'
source .venv/bin/activate
cp .env.example .env
```

## 命令行用法

基础格式：

```bash
nano-trading analyze <6位A股代码> [选项]
```

查看帮助：

```bash
nano-trading --help
nano-trading analyze --help
```

最小运行：

```bash
nano-trading analyze 000001
```

指定分析日期：

```bash
nano-trading analyze 600519 --date 2026-05-08
```

快速分析，减少数据回溯与整体耗时：

```bash
nano-trading analyze 000001 --depth quick
```

只运行技术面分析师，适合低成本 smoke test：

```bash
nano-trading analyze 000001 --depth quick --analysts market
```

运行完整默认分析师组合：

```bash
nano-trading analyze 000001 --analysts market,fundamentals,news
```

指定报告输出目录：

```bash
nano-trading analyze 000001 --report-dir ./reports
```

本地 mock 模式，不调用 LLM API，但仍会调用 AKShare 数据源：

```bash
nano-trading analyze 000001 --mock-llm
```

完全低成本验证 CLI、数据源和报告生成：

```bash
nano-trading analyze 000001 --date 2026-05-08 --depth quick --analysts market --mock-llm --report-dir /tmp/nano-reports
```

## 参数说明

| 参数 | 示例 | 说明 |
| --- | --- | --- |
| `symbol` | `000001` | 必填。仅支持 6 位 A 股代码，不支持美股/港股。 |
| `--date` | `2026-05-08` | 分析日期，格式 `YYYY-MM-DD`。不传则使用当天日期。 |
| `--depth` | `quick` | 分析深度：`quick`、`standard`、`deep`。默认 `standard`。 |
| `--analysts` | `market,fundamentals,news` | 分析师列表，逗号分隔。支持 `market`、`fundamentals`、`news`。 |
| `--report-dir` | `./reports` | Markdown 报告输出目录。默认 `reports`。 |
| `--mock-llm` | 无值开关 | 使用内置 mock LLM，不需要 API Key，适合测试流程。 |

分析师含义：

| 分析师 | 作用 |
| --- | --- |
| `market` | 技术面分析，使用行情、均线、RSI、MACD、成交量等数据。 |
| `fundamentals` | 基本面分析，使用 AKShare 可获取的公司信息和财务指标。 |
| `news` | 新闻分析，使用 AKShare 个股新闻。 |

无论选择哪些分析师，后续都会继续生成看多/看空观点、交易员建议和风险经理最终决策。

## LLM 配置

CLI 使用 OpenAI 兼容接口。配置写入 `.env`：

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

DeepSeek 示例：

```env
OPENAI_API_KEY=your-deepseek-api-key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
```


配置完成后运行真实 LLM 分析：

```bash
nano-trading analyze 000001 --depth quick --analysts market
```

## 输出结果

命令运行时会在终端显示当前阶段，例如：

```text
→ 加载 A 股数据
→ 运行技术面分析师
→ 生成看多/看空观点
→ 生成交易员建议
→ 生成风险决策
```

完成后显示最终结论：

```text
股票: 000001
日期: 2026-05-08
动作: 买入
报告: reports/000001_2026-05-08.md
```

报告文件是 Markdown，主要包含：

- 股票名称、分析日期、最终动作
- 数据限制或数据源失败提示
- 技术面/基本面/新闻分析
- 看多观点和看空观点
- 交易员建议
- 风险经理最终决策
- 免责声明

## 常用场景

快速验证安装是否正常：

```bash
nano-trading analyze 000001 --mock-llm --depth quick --analysts market
```

测试真实 LLM 是否连通：

```bash
python - <<'PY'
from nano_tradingagents.config import load_settings
from nano_tradingagents.llm import create_llm
llm = create_llm(load_settings())
print(llm.complete('你是连通性测试助手。', '请只回复：API OK'))
PY
```

生成一份完整 A 股报告：

```bash
nano-trading analyze 600519 --depth standard --analysts market,fundamentals,news
```

只看技术面，降低 token 成本：

```bash
nano-trading analyze 300750 --depth quick --analysts market
```

## 故障排查

`缺少 OPENAI_API_KEY`：

- 检查 `.env` 是否存在。
- 检查是否已填写 `OPENAI_API_KEY`。
- 如果只是测试流程，使用 `--mock-llm`。

`Nano 版仅支持 6 位 A 股代码`：

- 输入必须是 `000001`、`600519` 这类 6 位代码。
- 不支持 `AAPL`、`0700.HK`、`000001.SZ`。

AKShare 数据失败或新闻为空：

- 检查网络连接。
- 稍后重试，部分 AKShare 接口依赖第三方网页数据，可能临时不可用。
- 报告中的“数据限制”会标出具体失败模块。

模型响应慢：

- 使用 `--depth quick`。
- 使用 `--analysts market` 先做单模块分析。
- 换用更快的 OpenAI 兼容模型。

Python 版本不兼容：

- 使用 Python 3.10-3.12。
- 如果系统默认 Python 太新，使用 `uv venv --python 3.10 .venv`。

## 测试

```bash
pytest
```

或直接使用虚拟环境中的 pytest：

```bash
.venv/bin/python -m pytest -q
```
