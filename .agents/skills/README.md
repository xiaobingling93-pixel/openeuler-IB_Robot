# AI Agent 技能库 (Skills)

此目录包含了专为 AI Agent（如 Claude Code）设计的技能插件，用于自动化 IB-Robot 项目中的各种开发工作流。每个技能都定义了精准的触发条件（Description），并提供了执行复杂任务所需的工具和上下文。

## 技能清单

| 技能名称 | 分类 | 主要触发场景 (Triggers) |
| :--- | :--- | :--- |
| [ibrobot-env](./ibrobot-env) | 环境 | 加载 `.shrc_local`、设置 `ROS_DOMAIN_ID`、解决 `ModuleNotFoundError` 等。 |
| [ibrobot-build](./ibrobot-build) | 操作 | 执行项目编译 (`colcon build`)、构建特定 package 或修复编译错误。 |
| [ibrobot-launch](./ibrobot-launch) | 操作 | 启动机器人系统、运行仿真、测试 ACT 推理或进行遥操作调试。 |
| [ibrobot-architecture](./ibrobot-architecture) | 知识 | 理解 SSOT 模式、修改 `robot_config`、解释数据流或契约设计。 |
| [ibrobot-git-flow](./ibrobot-git-flow) | 工作流 | 提交代码、推送至个人仓库、确保符合 openEuler DCO/Commit 规范。 |
| [atomgit-code-review](./atomgit-code-review) | AtomGit | 对 PR 进行代码质量审查、逻辑检查、发现潜在 Bug。 |
| [atomgit-architecture-review](./atomgit-architecture-review) | AtomGit | 验证 PR 是否符合 SSOT、契约驱动设计等项目架构支柱。 |
| [atomgit-submit-pr](./atomgit-submit-pr) | AtomGit | 创建合并请求 (PR)、从提交记录自动生成 PR 描述。 |
| [atomgit-code-review-repair](./atomgit-code-review-repair) | AtomGit | 自动根据 AtomGit 上的检视意见应用修复代码或回复评论。 |

---

## 技能分类说明

### 🤖 IB-Robot 核心操作
这些技能旨在处理 IB-Robot 软件栈特有的日常开发任务。

- **环境管理 ([ibrobot-env](./ibrobot-env))**: 确保 shell 上下文正确继承了项目特有的环境变量。
- **编译构建 ([ibrobot-build](./ibrobot-build))**: 封装了 ROS 2 复杂的编译参数，确保构建的一致性。
- **系统启动 ([ibrobot-launch](./ibrobot-launch))**: 机器人系统的总入口，支持一键拉起复杂的节点拓扑。
- **架构顾问 ([ibrobot-architecture](./ibrobot-architecture))**: 充当项目的架构师，解答一切关于设计模式和配置规范的问题。
- **工程规范 ([ibrobot-git-flow](./ibrobot-git-flow))**: 自动化执行开源社区繁琐的提交规范校验。

### 🌐 AtomGit 自动化工具
这些技能通过集成 AtomGit API，实现了 PR 生命周期和代码审查的自动化。

> **⚠️ 前置条件：配置 AtomGit Token**
> 
> 使用 AtomGit 相关技能前，必须先配置 Personal Access Token：
> 
> 1. 访问 https://atomgit.com 并登录
> 2. 点击右上角头像 → 个人设置
> 3. 找到「访问令牌」选项
> 4. 点击「新建访问令牌」，勾选 `repo` 和 `pull_request` 权限
> 5. **立即复制保存** Token（只显示一次）
> 
> 设置环境变量：
> ```bash
> export ATOMGIT_TOKEN="your_token_here"
> ```
> 
> Token 配置存储在项目根目录的 `config.json` 中，通过环境变量 `$ATOMGIT_TOKEN` 引用。

- **PR 提交 ([atomgit-submit-pr](./atomgit-submit-pr))**: 简化向官方 upstream 仓库提交代码的流程。
- **自动审查 ([atomgit-code-review](./atomgit-code-review))**: 利用 LLM 充当第一道代码防线。
- **架构扫描 ([atomgit-architecture-review](./atomgit-architecture-review))**: 专门检查是否违背了 SSOT 等核心架构原则。
- **意见修复 ([atomgit-code-review-repair](./atomgit-code-review-repair))**: 实现从“发现问题”到“修复代码”的自动化闭环。

---

## 如何增加新技能

若要向本项目添加新技能，请遵循以下步骤：
1. 在 `.agents/skills/` 下创建一个新目录。
2. 添加 `SKILL.md` 文件，确保 `description` 字段采用 **if-then** 条件触发风格（包含中英双语关键词）。
3. 编写技能所需的配套脚本（Python/Bash）或库文件。
4. 更新此 `README.md` 文件，将新技能添加到清单表格中。
