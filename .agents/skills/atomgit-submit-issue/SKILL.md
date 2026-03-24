---
name: atomgit-submit-issue
description: "AtomGit Issue 提交工具。当用户需要“提交Issue”、“创建问题”、“create issue”、“submit issue”、“报告Bug”、“提出建议”或“记录待办事项”时调用。"
license: MIT
---

# AtomGit Issue Submit Tool

创建新 Issue 或管理现有 Issue。

## ⚠️ 环境准备

**重要**: 在使用此 skill 前，必须先加载环境配置：

```bash
source .shrc_local
```

这将把 `libs/atomgit_sdk/src` 添加到 PYTHONPATH
使 skill 能够导入 AtomGit SDK。

## ⚠️ 获取仓库配置（必需）

在使用前，建议通过 `git remote -v` 确认仓库的 owner 和 repo：

```bash
git remote -v
```

脚本会自动从环境变量或 `git remote` 中推断，也可以通过参数指定。

## 快速使用

### 创建 Issue

```bash
# 提交一个简单的 Issue
python3 submit_issue.py --title "发现一个 Bug" --body "在执行 build.sh 时报错..."

# 指定标签和指派人
python3 submit_issue.py --title "功能建议: 增加单元测试" --body "为了提高代码质量..." --labels enhancement,bug --assignees BreezeWu
```

### 获取 Issue 信息 (Agent 驱动)

当需要分析已有 Issue 时，Agent 可以调用：

```bash
python3 submit_issue.py --issue 123 --fetch-info
```
Agent 会读取生成的 `tmp/issue_123_context.json`。

## API 说明

### submit_issue.py

创建或更新 Issue。

**参数**:
- `--title`: Issue 标题（创建时**必需**）
- `--body`: Issue 描述
- `--labels`: 标签列表，逗号分隔（如: bug,high-priority）
- `--assignees`: 指派人列表，逗号分隔
- `--issue`: Issue 编号（用于更新或获取信息）
- `--state`: Issue 状态（open 或 closed，用于更新）
- `--fetch-info`: 提取 Issue 详情到 JSON 文件
- `--dry-run`: 仅显示计划，不执行实际操作

**示例**:
```bash
# 更新 Issue 状态
python3 submit_issue.py --issue 123 --state closed

# 修改 Issue 标题和内容
python3 submit_issue.py --issue 123 --title "已修正: 编译错误" --body "通过更新依赖已解决。"
```

## 注意事项

1. **环境配置**: 确保 `ATOMGIT_TOKEN` 已正确配置在环境变量中。
2. **Issue 规范**: 建议在标题中使用清晰的前缀，如 `[Bug]`, `[Feature]`, `[Task]` 等。
3. **标签管理**: 使用仓库已有的标签，或者在提交时创建清晰的新标签。
