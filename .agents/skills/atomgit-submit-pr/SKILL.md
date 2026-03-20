---
name: atomgit-submit-pr
description: "AtomGit PR 提交工具。创建新 PR 或更新现有 PR 描述。"
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

## 快速使用

### 创建 PR

```bash
# 自动从当前分支创建 PR
python3 create_pr.py --branch feat/my-feature

# 指定标题和描述
python3 create_pr.py --branch feat/my-feature --title "feat: add new feature" --body "Description..."
```

### 生成 PR 描述

```bash
# 从 git 提交生成 PR 描述
python3 generate_pr.py --branch feat/my-feature

# 提取 PR 信息（用于更新 PR）
python3 generate_pr.py --pr 123 --fetch-info

# 更新 PR 描述
python3 generate_pr.py --pr 123 --update-pr
```

## API 说明

### create_pr.py

创建新的 Pull Request。

**参数**:
- `--branch`: 分支名（必需）
- `--title`: PR 标题（可选，自动生成）
- `--body`: PR 描述（可选，自动生成）
- `--base`: 目标分支（默认：master）
- `--draft`: 创建草稿 PR
- `--dry-run`: 仅显示计划，不创建

**示例**:
```bash
python3 create_pr.py --branch feat/new-feature
```

### generate_pr.py

生成或更新 PR 描述。

**模式**:
1. `--branch`: 生成 PR 描述（默认）
2. `--pr --fetch-info`: 提取 PR 信息
3. `--pr --update-pr`: 更新 PR 描述

**示例**:
```bash
# 生成描述
python3 generate_pr.py --branch feat/new-feature

# 更新 PR #123 的描述
python3 generate_pr.py --pr 123 --update-pr
```

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
