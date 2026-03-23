---
name: atomgit-submit-pr
description: "AtomGit PR 提交工具。当用户需要“提交PR”、“创建合并请求”、“create pull request”、“submit PR”、“更新PR描述”、“update PR description”、“generate PR summary”或在功能开发完成后准备合入官方 upstream 仓库时调用。"
license: MIT
---

# AtomGit PR Submit Tool

创建新 PR 或更新现有 PR 描述。

## ⚠️ 环境准备

**重要**: 在使用此 skill 前，必须先加载环境配置：

```bash
source .shrc_local
```

这将把 `libs/atomgit_sdk/src` 添加到 PYTHONPATH
使 skill 能够导入 AtomGit SDK。

## ⚠️ 获取 Fork Owner（必需）

在创建 PR 前，**必须**先通过 `git remote -v` 获取 fork owner：

```bash
git remote -v
```

输出示例：
```
origin    git@atomgit.com:YourName/IB_Robot.git (fetch)
origin    git@atomgit.com:YourName/IB_Robot.git (push)
upstream  git@atomgit.com:openEuler/IB_Robot.git (fetch)
upstream  git@atomgit.com:openEuler/IB_Robot.git (push)
```

从中提取 fork owner（即个人仓库的用户名，如 `YourName`），然后通过 `--fork-owner` 参数传递给脚本。

## 快速使用

### 创建 PR

```bash
# 步骤1: 获取 fork owner
git remote -v
# 从输出中提取个人 fork 的 owner，如 BreezeWu

# 步骤2: 创建 PR
python3 create_pr.py --branch feat/my-feature --fork-owner BreezeWu

# 指定标题和描述
python3 create_pr.py --branch feat/my-feature --fork-owner BreezeWu --title "feat: add new feature" --body "Description..."
```

### 生成/更新 PR 描述 (Agent 驱动)

当需要为已有 PR 生成高质量描述时，遵循以下 Agent 工作流：

**步骤 1: 提取 PR 上下文**
```bash
python3 generate_pr.py --pr 123 --fetch-info
```
Agent 会读取生成的 `tmp/pr_123_context.json`，其中包含所有提交记录、修改文件以及代码 Diff (patch)。

**步骤 2: Agent 分析与同步**
Agent 分析完 Diff 后，会生成一份 `description.json`:
```json
{
  "title": "feat: 新功能标题",
  "description": "详细的变更逻辑说明..."
}
```
然后运行同步命令：
```bash
python3 generate_pr.py --pr 123 --update-pr description.json
```

## API 说明

### create_pr.py

创建新的 Pull Request。

**参数**:
- `--branch`: 分支名（可选，默认当前分支）
- `--fork-owner`: Fork 仓库的 owner（**必需**，通过 `git remote -v` 获取）
- `--title`: PR 标题（可选，自动生成）
- `--body`: PR 描述（可选，自动生成）
- `--base`: 目标分支（默认：master）
- `--draft`: 创建草稿 PR（可选）
- `--dry-run`: 仅显示计划，不创建

**示例**:
```bash
# 完整示例
python3 create_pr.py --branch feat/new-feature --fork-owner BreezeWu

# 指定标题
python3 create_pr.py --branch feat/new-feature --fork-owner BreezeWu --title "feat: add new feature"
```

### generate_pr.py

管理和维护已有 PR 的数据。

**模式**:
1. `--pr <NUM> --fetch-info`: 提取 PR 的完整上下文 (提交、文件、Diff)，Agent 学习用。
2. `--pr <NUM> --update-pr <JSON>`: 将 Agent 生成的描述同步到服务器。

**参数**:
- `--pr`: PR 编号 (**必需**)
- `--output-dir`: JSON 输出目录 (默认: ./tmp)
- `--ai-model`: 签名使用的 AI 名称 (默认: agent)
- `--dry-run`: 预览生成的描述但不执行更新

## PR 描述格式

PR 描述会自动包含：

- **Summary**: 变更概述
- **Changes**: 详细变更列表
- **Testing**: 测试说明
- **Checklist**: 检查项

## 注意事项

1. **分支命名**: 建议使用 `feat/`, `fix/`, `docs/`, `refactor/` 等前缀
2. **提交信息**: 确保提交信息符合规范
3. **代码审查**: 创建 PR 后等待代码审查
4. **CI 检查**: 确保 CI 通过后再合并
