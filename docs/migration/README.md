# IB-Robot 文档迁移与转换指南

本目录包含了将 `wuxiaoqiang12/IB_Robot` 仓库的 GitHub Wiki/文档 转换为 openEuler 官方文档（RST 格式）的全套自动化工具。

## 转换流程概览

整个转换过程分为四个主要阶段：提取、拆分、配置、生成。

### 1. 提取 (Extraction)
使用 **DeepWiki MCP** 工具从远程仓库获取完整的文档内容。
- **工具**: `mcp_deepwiki_read_wiki_contents`
- **产出**: 原始大文件 `migration/IB_Robot_doc_raw.md`
- **说明**: 该文件包含了所有页面的 Markdown 内容，以 `# Page: <Title>` 作为分隔符。

### 2. 拆分 (Splitting)
将巨大的原始 Markdown 文件物理拆分为多个独立的页面，便于管理和局部对比。
- **脚本**: `migration/split_md.py`
- **命令**: `python3 migration/split_md.py`
- **产出**: `migration/raw_md/` 目录下的数十个 `.md` 文件。

### 3. 配置 (Configuration)
通过 JSON 配置文件定义文档的层级结构和跳转映射。
- **文件**: `migration/doc_config.json`
- **关键配置**:
    - `id_to_label`: 将 DeepWiki 的数字页码映射到唯一的 RST 锚点。
    - `hierarchy`: 定义文件夹结构、`index.rst` 标题及子页面的归属关系。
    - `title_to_label`: 建立标题与锚点的对应关系。

### 4. 生成 (Conversion)
运行核心转换脚本，将 Markdown 转换为符合 Sphinx 规范的 RST 体系。
- **脚本**: `migration/deepwiki_to_rst.py`
- **命令**: `python3 migration/deepwiki_to_rst.py <COMMIT_ID>`
- **特性**:
    - **层级化**: 自动创建子目录、`introduction.rst` 及纯净的 `index.rst`。
    - **代码保护**: 引入占位符机制，确保代码块内部的 `#` 注释不被误识别为标题。
    - **源码徽章**: 自动转换为指向 GitCode 的徽章样式链接。
    - **Mermaid/折叠块**: 完整保留绘图和 `Relevant source files` 细节。

---

## 中文本地化 (Translation) 工作流

如果你需要生成中文版文档，推荐采用“**Markdown 层级翻译**”方案，这是保证格式完整性和翻译质量的最佳路径：

### 推荐步骤

1. **获取英文源码**:
   完成上述的“提取”和“拆分”步骤，确保 `migration/raw_md/` 下有完整的英文 MD 文件。

2. **执行 AI 批量翻译**:
   编写脚本调用大模型 API 对 `raw_md/*.md` 进行翻译。
   - **保护逻辑**: 翻译时应使用正则保护 ` ``` ` 代码块、`.. mermaid::` 内容和 `[text](url)` 中的 URL 部分。
   - **一致性**: 在 Prompt 中内置术语表（如 `Inference` -> `推理`）。
   - **存储**: 将翻译后的文件存入新目录，如 `migration/raw_md_zh/`。

3. **同步配置文件**:
   更新 `doc_config.json` 中的 `title` 和 `subs` 映射，使其匹配翻译后的中文页面标题。

4. **一键生成 RST**:
   修改 `deepwiki_to_rst.py` 中的输入路径指向 `raw_md_zh/`，然后重新运行生成脚本。

### 方案优势
- **低成本维护**: 当英文文档更新时，只需针对变动的 MD 文件进行增量翻译。
- **结构对齐**: 保持文件名（slug）不变，仅翻译内容，可确保所有的内部锚点引用（`:ref:`）依然有效。

---

## 渲染增强 (Frontend)

为了让生成的文档呈现出最佳视觉效果，本项目还同步更新了以下前端资源：
- `docs/source/_static/js/custom.js`: 强化了源码徽章的识别逻辑（支持 GitCode 链接特征识别）。
- `docs/source/_static/css/custom.css`: 实现了全局可用的源码徽章样式（支持表格内嵌套）。
