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

4. **Package-Specific Architecture Compliance**
   - **核心原则**: 每个 ROS 包必须遵循其在 `ibrobot-architecture` 中定义的职责边界。
   - **关键检查**: 
     - 检查改动是否符合该包的设计初衷（如 `robot_teleop` 应保持轻量，不应引入运动学 IK 或重型规划逻辑）。
     - 验证包之间的依赖是否符合分层设计，严禁职责越界。
     - 识别“职责蔓延”：如果一个简单的驱动包开始处理复杂的业务逻辑，必须提出警告。

## 架构审查协议 (Mandatory Protocol)

在分析代码前，你 **必须** 遵循以下协议以确保对各包职责有准确认知：

1. **同步上下文 (Context Sync)**: 
   - 针对 PR 涉及的每一个包（如 `robot_teleop`），首先调用 `ibrobot-architecture` skill 或读取该包根目录下的 `README.md`。
   - 确认该包的设计初衷、职责边界及禁止的行为（如禁止引入运动学、禁止直接操作硬件等）。
2. **定位变更层级**: 判断变更文件位于哪一层（硬件层、驱动层、业务层、模型层）。
3. **依赖审计**: 检查是否引入了不符合分层原则的跨包依赖。
4. **SSOT 验证**: 检查配置是否统一来自 `robot_config`，严禁硬编码。
5. **职责合规性判断**: 根据步骤 1 获取的契约，判断当前改动是否导致了“职责蔓延”或“架构违越”。
6. **输出审查结果**: 生成符合 JSON 格式的 `arch_issues.json`。

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
