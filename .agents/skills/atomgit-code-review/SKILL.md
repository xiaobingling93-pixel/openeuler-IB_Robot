---
name: atomgit-code-review
description: "AtomGit 代码审查工具。当用户需要“代码审查”、“代码评审”、“code review”、“PR review”、“审阅代码”、“检查Bug”、“logic check”、“发现错误”、“审视PR”或提交检视意见到 AtomGit 时使用。适用于“审阅 #123 号PR”、“检查代码逻辑”等指令。"
license: MIT
---

# AtomGit Code Review

提取 PR 信息并提交代码审查评论到 AtomGit。

## ⚠️ 环境准备

**必须先加载环境变量**：

```bash
source .shrc_local
```

此命令会将 `libs/atomgit_sdk/src` 添加到 PYTHONPATH，使 skill 能够导入 atomgit_sdk 模块。

## ⚠️ 文件读取说明

**输出文件位于项目 `./tmp` 目录**，AI Agent 应使用 shell 命令读取：

```bash
# 读取 PR 信息
cat ./tmp/ib_robot_pr_123_info.json

# 读取审查结果（提交前确认）
cat ./tmp/ib_robot_pr_123_issues.json
```

### 大文件处理技巧

当 PR 包含大量文件时，JSON 文件可能很大。使用 `jq` 提取特定文件信息：

```bash
# 列出所有变更文件
jq '.pr.changed_files[].filename' ./tmp/ib_robot_pr_123_info.json

# 提取特定文件的内容
jq '.pr.changed_files[] | select(.filename == "lib/api.py") | .content' ./tmp/ib_robot_pr_123_info.json

# 提取特定文件的 diff
jq '.pr.changed_files[] | select(.filename == "lib/api.py") | .patch.diff' ./tmp/ib_robot_pr_123_info.json

# 提取多个文件（支持通配符）
jq '.pr.changed_files[] | select(.filename | contains("lib/")) | {filename, content}' ./tmp/ib_robot_pr_123_info.json
```

## 快速使用

```bash
# 步骤1: 提取 PR 信息
python3 atomgit_reviewer.py --pr 123

# 步骤2: 你分析代码并生成 issues.json

# 步骤3: 人类确认审查结果

# 步骤4: 提交审查结果（⚠️ 必须指定 --ai-model）
python3 atomgit_reviewer.py --pr 123 --submit-review ./tmp/ib_robot_pr_123_issues.json --ai-model claude-sonnet-4
```

**重要**: 
- 在步骤3，你必须将审查结果展示给人类确认后再提交
- **步骤4必须指定 `--ai-model` 参数**，使用你的真实模型名称（如 `claude-sonnet-4`、`gpt-4`、`gemini-pro`）
- 文件名格式：`./tmp/{repo}_pr_{number}_issues.json`（例如：`./tmp/ib_robot_pr_123_issues.json`）

## API 说明

### 提取 PR 信息

```bash
python3 atomgit_reviewer.py --pr 123
```

**输出**: 项目临时目录 `./tmp/{repo}_pr_{number}_info.json`（例如：`./tmp/ib_robot_pr_123_info.json`）

**注意**: 
- 默认输出到项目 `./tmp` 目录，**不需要指定 `--output-dir`**

```json
{
  "pr": {
    "number": 123,
    "title": "...",
    "author": "...",
    "branch": "feature → main",
    "changed_files": [
      {
        "filename": "lib/api.py",
        "status": "modified",
        "patch": "...",
        "content": "..."
      }
    ]
  }
}
```

**⚠️ 重要**：提取的 JSON 文件已经包含了所有 diff（`patch`）和文件内容（`content`）。
- **不需要** `git fetch` 或 `git diff`
- **不需要** 切换分支或修改本地代码
- 直接读取 JSON 文件中的 `changed_files` 进行审查即可

### 提交审查结果

```bash
python3 atomgit_reviewer.py --pr 123 --submit-review ./tmp/ib_robot_pr_123_issues.json --ai-model claude-sonnet-4
```

**参数**：
- `--pr`: PR 编号
- `--submit-review`: 审查结果 JSON 文件
- `--ai-model`: AI 模型名称（**必须指定真实模型名称**，用于签名）
- `--dry-run`: 仅显示计划

**⚠️ 重要**：`--ai-model` 参数**必须指定你的真实模型名称**，以便在评论中准确标识来源。

**常见模型名称**：
- `claude-sonnet-4`
- `claude-opus-4`
- `gpt-4`
- `gpt-4o`
- `gemini-pro`
- `gemini-1.5-pro`

## 你需要生成的 issues.json 格式

**重要要求**：
1. **必须使用中文**输出所有内容
2. **必须包含修复方案**（fix_code 字段）
3. **文件保存到 ./tmp 目录**，文件名格式：`./tmp/ib_robot_pr_{number}_issues.json`

```json
[
  {
    "file": "lib/api.py",
    "line": 52,
    "type": "bug",
    "severity": "error",
    "confidence": 95,
    "title": "缺少异常处理",
    "description": "response.json() 可能抛出 JSONDecodeError",
    "context_code": "return response.json()",
    "fix_code": "try:\n    return response.json()\nexcept json.JSONDecodeError:\n    return {}",
    "fix_explanation": "添加异常处理避免程序崩溃"
  }
]
```

### 字段说明

| 字段 | 必填 | 说明 | 可选值 |
|------|------|------|--------|
| file | ✅ | 文件路径 | |
| line | ✅ | 行号 | |
| type | ✅ | 问题类型（中文） | `bug`, `security`, `performance`, `maintainability` |
| severity | ✅ | 严重程度（中文） | `error`, `warning`, `suggestion`, `info` |
| confidence | ✅ | 置信度 (0-100) | |
| title | ✅ | 问题标题（中文） | |
| description | ✅ | 详细描述（中文） | |
| context_code | ❌ | 相关代码 | |
| fix_code | ✅ | 修复代码（必须提供） | |
| fix_explanation | ✅ | 修复说明（中文） | |

## 配置

在项目根目录的 `config.json` 中：

```json
{
  "atomgit": {
    "token": "your_personal_access_token",
    "owner": "openEuler",
    "repo": "IB_Robot",
    "baseUrl": "https://api.atomgit.com"
  }
}
```

## Related Skills

- `atomgit-code-review-repair`: 修复检视意见
- `atomgit-architecture-review`: 架构审查
