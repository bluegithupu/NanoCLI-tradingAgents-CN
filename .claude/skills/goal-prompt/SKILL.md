---
name: goal-prompt
description: >-
  将简短任务需求扩展为可直接用于 Codex /goal 的完整提示词，包含目标、执行步骤、验证命令、产物要求与完成标准；适用于 bugfix、feature、release-readiness 等工程场景。
when_to_use: >-
  当用户说“写一个 /goal 提示词”“把一句话需求变成完整目标执行模板”“按固定模板输出可验证 goal”时使用；尤其适合需要 TDD、最小改动、状态文件更新、可复现验收的仓库。
---

# Goal Prompt

把“简单请求”转换成“可执行、可验证、可交付”的 `/goal` 提示词。

## 适用场景

- 你只有一句话需求，但希望 Codex 一次性推进到底。
- 你希望目标具备：执行步骤、验收标准、命令验证、状态同步。
- 你希望减少模糊指令导致的返工。

## 快速用法

在仓库根目录执行：

```bash
python .claude/skills/goal-prompt/scripts/build_goal_prompt.py \
  --project /Users/mac/Code/mcp-client \
  --task "修复计算器在非法输入时返回不一致错误信息" \
  --mode auto
```

可选模式：
- `auto`: 自动判断模板（默认）
- `bugfix`: 缺陷修复闭环
- `feature`: 单功能交付
- `release`: 发布就绪闸门

输出默认打印到 stdout；如需保存：

```bash
python .claude/skills/goal-prompt/scripts/build_goal_prompt.py \
  --project /Users/mac/Code/mcp-client \
  --task "为检索系统增加最小可用评分策略" \
  --mode feature \
  --output /tmp/goal_feature.md
```

## 工作流

1. 获取简短需求（1-2 句）
2. 选择模式（或 `auto`）
3. 生成完整 `/goal` 提示词
4. 直接粘贴到 Codex `/goal`

## 生成质量规则

- 默认中文输出。
- 强制“单一目标 + 可验证步骤 + 完成标准”。
- 默认包含最小改动约束，避免范围膨胀。
- 默认包含验证命令与状态文件更新要求（`progress.md`、`feature_list.json`）。

## 参考模板

详细模板见 [references/templates.md](references/templates.md)。脚本生成逻辑与该模板保持一致。
