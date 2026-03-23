---
name: atomgit-architecture-review
description: "AtomGit 架构审查工具。当用户需要“架构审查”、“架构评审”、“check architecture”、“review architecture compliance”、“检查架构规范”、“符合设计支柱”或对指定 PR 进行架构维度扫描并提交检视意见时调用。适用于“审阅PR架构”、“架构合规性检查”等场景。"
license: MIT
---

# AtomGit Architecture Review

提取 PR 信息并提交 IB_Robot 架构合规审查评论到 AtomGit。

## ⚠️ 环境准备

**重要**: 在使用此 skill 前，必须先加载环境配置：

```bash
source .shrc_local
```

这将把 `libs/atomgit_sdk/src` 添加到 PYTHONPATH
使 skill 能够导入 AtomGit SDK。

## ⚠️ 文件读取说明

**输出文件位于项目 `./tmp` 目录**，AI Agent 应使用 shell 命令读取：

```bash
# 读取 PR 信息
cat ./tmp/ib_robot_pr_123_arch_info.json

# 读取架构审查结果（提交前确认）
cat ./tmp/ib_robot_pr_123_arch_issues.json
```

## 快速使用

```bash
# 步骤1: 提取 PR 信息
python3 atomgit_reviewer.py --pr 123

# 步骤2: 你分析代码架构并生成 arch_issues.json

# 步骤3: 人类确认审查结果

# 步骤4: 提交审查结果（⚠️ 必须指定 --ai-model）
python3 atomgit_reviewer.py --pr 123 --submit-review ./tmp/ib_robot_pr_123_arch_issues.json --ai-model claude-sonnet-4
```

**重要**: 
- 在步骤3，你必须将审查结果展示给人类确认后再提交
- **步骤4必须指定 `--ai-model` 参数**，使用你的真实模型名称（如 `claude-sonnet-4`、`gpt-4`、`gemini-pro`）
- 文件名格式：`./tmp/{repo}_pr_{number}_arch_issues.json`

## 架构审查支柱

此工具会检查以下 IB_Robot 架构支柱：

1. **SSOT (Single Source of Truth)**
   - 配置来源唯一性
   - 数据流一致性
   - API 契约统一性

2. **Contract-Driven Design**
   - 接口定义完整性
   - 依赖注入模式
   - 契约验证

3. **Control Mode Architecture**
   - 控制模式分离
   - 状态管理一致性
   - 控制流清晰度

## API 说明

### 提取 PR 信息

```bash
python3 atomgit_reviewer.py --pr 123
```

**输出**: 项目临时目录 `./tmp/{repo}_pr_{number}_arch_info.json`

### 提交架构审查

```bash
python3 atomgit_reviewer.py --pr 123 --submit-review ./tmp/ib_robot_pr_123_arch_issues.json --ai-model claude-sonnet-4
```

## 架构问题严重性

- 🔴 **critical**: 违反核心架构原则，- 🟠 **error**: 重要架构问题
- 🟡 **warning**: 架构建议改进
- 💡 **suggestion**: 最佳实践建议
