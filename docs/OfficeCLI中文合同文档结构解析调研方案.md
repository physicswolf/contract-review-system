# OfficeCLI 中文合同文档结构解析与内容使用调研方案

## 目录

- 一、概述
- 1.1 工具简介
- 1.2 面向中文合同场景的定位
- 二、安装部署
- 2.1 环境要求
- 2.2 基础安装
- 2.3 中文合同处理配置
- 2.4 工程化使用建议
- 三、支持的文档对象与合同要素
- 四、中文合同文档解析方案
- 4.1 整体架构
- 4.2 基础读取命令
- 4.3 Word DOM 路径与结构解析
- 4.4 条款与章节解析
- 4.5 表格结构解析
- 4.6 批注、修订、内容控件与表单域
- 4.7 渲染、质量检查与可追溯验证
- 五、中文合同解析 Demo
- 5.1 完整示例代码
- 5.2 运行方式
- 5.3 输出结果说明
- 六、按条款分块与内容使用
- 七、验证方案与边界说明
- 八、总结与建议
- 资料来源

## 一、概述

### 1.1 工具简介

`OfficeCLI` 是面向 Office 文档自动化的命令行工具，主要用于读取、创建、修改和验证 Word、Excel、PowerPoint 文件。官方仓库将其定位为面向 AI agent 的 Office 套件，提供单二进制分发、无需本机安装 Microsoft Office、支持命令行和 JSON 输出的能力。

截至本次调研日期，GitHub 项目页面显示最新 release 为 `v1.0.115`，发布日期为 2026-06-18；官方 Wiki 页面同时存在不同基准版本标注，例如 `v1.0.64`。因此，本文把结论分为两类：

- 稳定能力面：`.docx` / `.xlsx` / `.pptx` 读写、DOM-like 路径、`view` / `get` / `query` / `set` / `dump` / `batch` / `merge` / `validate` 等命令。
- 需要落地验证的细节：具体 JSON 字段大小写、个别 selector 写法、插件命令、导出能力和不同版本的边缘行为。

核心能力包括：

| 能力 | 说明 | 合同场景价值 |
| --- | --- | --- |
| 文档读取 | 读取文本、结构、样式、表格、批注、修订等信息 | 从源 `docx` 中抽取合同正文、条款、表格和审阅痕迹 |
| DOM-like 路径 | 使用 `/body/p[1]`、`/body/tbl[1]` 等路径定位元素 | 建立可追溯的合同元素路径，便于回写和审计 |
| JSON 输出 | 多数命令支持 `--json` | 便于后端服务、Python 脚本、RAG 管线消费 |
| 查询选择器 | 支持类似 CSS 的选择器和 `--find` 文本检索 | 按标题样式、文本关键词、属性筛选合同结构 |
| 文档修改 | `set` / `add` / `remove` / `move` / `swap` | 可用于模板生成、条款替换、格式修正和批量修订 |
| 模板合并 | `merge` 替换 `{{key}}` 占位符 | 适合合同模板字段填充和批量出具 |
| Dump / Batch | 将文档或子树导出为可回放 JSON，再批量执行 | 适合沉淀合同模板结构、复用人工样本文档 |
| 渲染与检查 | 输出 HTML / PNG、`view issues`、`validate` | 支持解析结果人工复核、格式质量检查和 OpenXML 验证 |
| MCP 集成 | 内置 MCP 服务配置入口 | 便于接入 AI agent 工作流，但合同解析系统不强依赖 MCP |

### 1.2 面向中文合同场景的定位

中文合同常见形态包括合同正文、附件、报价清单、付款计划、签署页、页眉页脚中的合同编号、审阅批注、修订痕迹、内容控件、表单域和公司模板样式。若业务能拿到原始 `docx` 文件，`OfficeCLI` 适合定位为“Office 源文档结构化入口层”：

- 直接读取 Word 源文件，保留段落、运行、样式、编号、表格、页眉页脚、批注、修订等 Office 结构。
- 用 DOM-like 路径建立“抽取结果 -> 原始元素”的映射，满足合同审查、证据定位和人工复核需要。
- 用 `view text` / `view outline` / `view annotated` 获取不同粒度的合同文本视图。
- 用 `get` / `query` 获取结构化 JSON，避免只依赖纯文本正则。
- 用 `dump` 将成熟合同样本固化为可回放结构，为模板生成和批量处理服务。
- 用 `merge` 对合同模板中的 `{{key}}` 占位符做字段填充。
- 用 `view issues` / `validate` 在交付前检查格式、结构和 OpenXML 合法性。

需要明确的是，`OfficeCLI` 不是法律语义理解工具。它可以把中文合同文档的结构和内容抽取出来，也可以回写和生成 Office 文档；但“条款是否公平”“违约责任是否过重”“付款条件风险等级”等判断仍需要业务规则、合同知识库或模型层完成。

## 二、安装部署

### 2.1 环境要求

| 项目 | 建议 |
| --- | --- |
| 操作系统 | Windows、macOS、Linux，按官方 release 下载对应二进制 |
| 运行依赖 | 官方说明为单二进制、无需本机安装 Office、无需额外运行时依赖 |
| 构建依赖 | 如需从源码构建，需要 .NET SDK；官方 README 当前提到 .NET 10 SDK 用于编译 |
| 主要输入 | `.docx`、`.xlsx`、`.pptx` |
| 合同重点格式 | 中文合同源文件优先使用 `.docx`；`.doc`、PDF 导出等能力按插件或版本说明验证 |
| 输出形式 | 文本、JSON、HTML、截图、dump JSON、批量命令结果 |
| 许可证 | GitHub 仓库标注 Apache License 2.0 |

本次本地环境未安装 `officecli`，`Get-Command officecli` 未返回可执行文件。因此本文中的命令和 Demo 是基于官方文档整理的落地方案模板，尚未在本机执行验证。

### 2.2 基础安装

官方 README 提供的安装方式包括脚本安装和 release 二进制下载。

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/iOfficeAI/OfficeCLI/main/install.sh | bash
```

Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/iOfficeAI/OfficeCLI/main/install.ps1 | iex
```

手动安装：

1. 从 GitHub Releases 下载对应平台二进制。
2. 将二进制放入固定目录，例如 Windows 的工具目录或 Linux 的 `/usr/local/bin`。
3. 确保 `officecli` 在 `PATH` 中。
4. 验证版本：

```bash
officecli --version
```

常见配置：

```bash
# 查看帮助
officecli --help

# 如需关闭自动更新
officecli config autoUpdate false

# CI 中临时跳过更新检查
OFFICECLI_SKIP_UPDATE=1 officecli --version
```

面向合同解析系统，建议采用“固定版本 + 可回滚”的部署方式：

- 生产环境固定 release 版本，不直接跟随最新版本。
- 将 `officecli --version` 写入解析日志。
- 每次升级前用合同样本集回归验证文本、路径、表格、批注、修订、模板合并和渲染结果。
- Windows 服务、Linux 容器和 CI 环境分别验证中文路径、中文文件名、中文字体和标准输出编码。

### 2.3 中文合同处理配置

中文合同处理重点不在安装 OCR，而在 Office 源文件解析、中文字体渲染、JSON 编码和样式体系识别。

| 配置项 | 建议 |
| --- | --- |
| 编码 | Python 调用时显式使用 `encoding="utf-8"`；Windows PowerShell 建议使用 UTF-8 输出环境 |
| 中文字体 | 如果使用 `view html`、`view screenshot` 或 `watch`，服务器需安装合同模板常用中文字体 |
| 样式命名 | 国内合同模板常见中文样式名、手工加粗标题、自动编号混用，不能只依赖 `Heading1` |
| 路径引用 | 命令行中对中文路径、空格路径加引号；脚本中使用参数数组调用，避免拼接 shell 字符串 |
| 更新策略 | 离线或内网环境建议关闭自动更新，统一发版 |
| 输出留存 | 保留原始 `docx`、文本视图、结构 JSON、问题列表、版本号和处理日志 |

中文合同通常包含“甲方/乙方”“合同编号”“签订地点”“签订日期”“标的”“价款”“付款”“验收”“违约责任”“争议解决”“生效”“附件”等字段。OfficeCLI 本身不直接理解这些业务字段，建议通过以下组合实现：

- `view text` 获取稳定全文输入。
- `view outline` 获取标题和大纲线索。
- `get / --depth N --json` 获取结构树和路径。
- `query` 按样式、文本、类型筛选候选元素。
- 业务层使用中文合同编号规则、关键词词典、正则和模型进行字段归并。

### 2.4 工程化使用建议

- 固定版本：建议在部署清单中锁定 OfficeCLI release 版本，并记录官方 Wiki 基准版本。
- 分层使用：读取优先用 `view`、结构定位用 `get` / `query`、修改用 `set` / `add`、底层兜底才使用 `raw` / `raw-set`。
- 保留路径：所有抽取出的条款、表格、批注、修订都保存 OfficeCLI path，避免后续无法追溯。
- 避免一次性深度过大：长合同用 `/body`、章节、表格子树逐步读取，防止 JSON 过大。
- 命令封装：后端服务通过 subprocess 或官方 SDK 封装调用，不在业务代码中散落命令字符串。
- 样本回归：建立中文合同样本集，覆盖普通正文、复杂编号、嵌套表格、批注修订、页眉页脚、附件和签署页。
- 安全处理：不要直接把不可信用户输入拼接进命令行；模板合并时校验 JSON 字段白名单。
- 审计日志：记录输入文件哈希、OfficeCLI 版本、命令、退出码、stderr、输出文件路径和解析耗时。

## 三、支持的文档对象与合同要素

OfficeCLI 的 Word 支持面较广，适合把中文合同拆成“可追溯结构单元”。下表按合同解析价值整理：

| Word 对象 | OfficeCLI 访问方式 | 中文合同解析价值 |
| --- | --- | --- |
| Document | `/` | 文档根节点，作为全量结构、元数据和全局操作入口 |
| Body | `/body` | 合同正文主体，条款解析的主要区域 |
| Paragraph | `/body/p[N]` | 合同标题、章节标题、普通条款、签署语、附件标题 |
| Run | `/body/p[N]/r[M]` | 加粗、下划线、颜色、局部替换、变量占位符 |
| Table | `/body/tbl[N]` | 甲乙方信息、付款计划、服务清单、附件清单、验收标准 |
| Row / Cell | `/body/tbl[N]/tr[M]/tc[K]` | 表格行列结构，适合抽取键值和明细项 |
| Style | 样式属性、`query` 选择器 | 识别标题层级、正文样式、模板差异 |
| Numbering | 编号属性、段落文本 | 识别“一、”“1.”“（一）”“第十条”等条款层级 |
| Header / Footer | `/header[N]`、`/footer[N]` | 合同编号、密级、页码、模板页眉页脚噪声 |
| Section | `/section[N]` | 附件、签署页、不同页面设置和分节信息 |
| Picture | 图片节点 | 签章图片、二维码、附件截图、图片化说明 |
| Watermark | 水印节点 | “草稿”“保密”“内部资料”等水印识别 |
| Hyperlink | 超链接节点 | 外部附件链接、平台链接、引用资料 |
| Bookmark | 书签节点 | 模板锚点、交叉引用、字段定位 |
| Field | field 节点 | 页码、目录、交叉引用、文档属性、合并字段 |
| TOC | 目录节点 | 合同目录和章节跳转线索 |
| Comment | comment 节点 | 法务审阅意见、业务修改建议、谈判记录 |
| Revision | revision 相关属性 | 跟踪修订，区分新增、删除、格式修改、移动 |
| SDT / Content Control | `/body/sdt[N]` | 合同模板字段、受控输入区域、系统生成字段 |
| Form Field | form field 节点 | 表单式合同字段，如主体、金额、日期 |
| Footnote / Endnote | 脚注尾注节点 | 例外说明、定义补充、引用说明 |
| OLE Object | OLE 节点 | 嵌入 Excel、附件对象、报价文件等 |

对中文合同解析而言，最重要的不是把所有对象都平铺为文本，而是建立三个层次：

- 阅读文本层：合同标题、正文、表格文本、批注文本。
- 结构路径层：每个段落、表格、批注、修订对应 OfficeCLI path。
- 业务语义层：主体、金额、期限、权利义务、违约责任、争议解决、附件等业务字段。

## 四、中文合同文档解析方案

### 4.1 整体架构

```text
中文合同 docx
        ↓
OfficeCLI
        ↓
多视图输出
  - view text
  - view outline
  - view annotated
  - get/query JSON
  - dump JSON
  - issues/validate
        ↓
结构识别层
  - 文档根、正文、页眉页脚
  - 段落、标题、编号
  - 表格、单元格
  - 批注、修订、内容控件
        ↓
中文合同归一层
  - 中文编号归一
  - 段落合并与空白清洗
  - 页眉页脚去噪
  - 表格键值抽取
  - 审阅痕迹归档
        ↓
结构化输出
  - contract_text.txt
  - document_tree.json
  - clauses.json
  - tables.json
  - comments.json
  - revisions.json
  - issues.json
        ↓
业务使用
  - 字段抽取
  - 条款审查
  - RAG 检索
  - 模板填充
  - 版本比对
  - 可视化复核
```

建议把 OfficeCLI 的命令分成三层使用：

| 层级 | 命令 | 用途 |
| --- | --- | --- |
| L1 读取视图 | `view text`、`view outline`、`view annotated`、`view stats`、`view issues` | 快速拿到文本、大纲、标注视图和质量问题 |
| L2 DOM 操作 | `get`、`query`、`set`、`add`、`remove`、`move`、`swap` | 读取和修改具体元素，建立路径级追溯 |
| L3 原始 OpenXML | `raw`、`raw-set`、`add-part`、`validate` | 处理高阶对象或命令未覆盖的底层结构 |

合同解析系统建议默认停留在 L1 / L2。只有遇到特殊模板、复杂字段、非常规 OpenXML 结构时，再使用 L3。

### 4.2 基础读取命令

基础文本读取：

```bash
officecli view contract.docx text > contract_text.txt
```

读取大纲：

```bash
officecli view contract.docx outline --json > outline.json
```

读取带结构标注的视图：

```bash
officecli view contract.docx annotated --json > annotated.json
```

读取文档根节点和有限深度子节点：

```bash
officecli get contract.docx / --depth 3 --json > document_tree.json
```

读取正文区域：

```bash
officecli get contract.docx /body --depth 4 --json > body_tree.json
```

按样式查询标题：

```bash
officecli query contract.docx "paragraph[style=Heading1]" --json > heading1.json
officecli query contract.docx "paragraph[style=Heading2]" --json > heading2.json
```

按关键词查找候选条款：

```bash
officecli query contract.docx --find "违约责任" --json > breach_candidates.json
officecli query contract.docx --find "争议解决" --json > dispute_candidates.json
officecli query contract.docx --find "付款" --json > payment_candidates.json
```

质量问题检查：

```bash
officecli view contract.docx issues --json > issues.json
```

OpenXML 验证：

```bash
officecli validate contract.docx --json > validate.json
```

渲染 HTML 和截图：

```bash
officecli view contract.docx html -o contract.html
officecli view contract.docx screenshot -o contract.png
```

说明：

- 官方文档中 `view` 支持 `text`、`annotated`、`outline`、`stats`、`issues`、`html`、`screenshot`、`svg` 等模式；部分模式或格式可能依赖插件或版本。
- `get` / `query` 的 `--json` 输出字段在 README 和 Wiki 示例中存在大小写差异。工程实现应通过兼容包装层读取 `path` / `Path`、`text` / `Text`、`children` / `Children` 等字段。
- 路径索引是 1-based，即第一个段落为 `/body/p[1]`。

### 4.3 Word DOM 路径与结构解析

OfficeCLI 的路径不是完整 XPath，而是面向文档对象的 DOM-like 路径。常见 Word 路径包括：

| 路径 | 含义 | 合同用途 |
| --- | --- | --- |
| `/` | 文档根 | 全文结构入口 |
| `/body` | 正文 | 合同条款主体 |
| `/body/p[1]` | 正文第 1 个段落 | 合同标题或首段 |
| `/body/p[1]/r[1]` | 第 1 个段落的第 1 个 run | 局部格式、占位符替换 |
| `/body/tbl[1]` | 正文第 1 个表格 | 主体信息表、付款表 |
| `/body/tbl[1]/tr[1]` | 第 1 个表格的第 1 行 | 表头或首行 |
| `/body/tbl[1]/tr[1]/tc[1]` | 第 1 个表格第 1 行第 1 个单元格 | 表格键值 |
| `/header[1]` | 第 1 个页眉 | 合同编号、密级 |
| `/footer[1]` | 第 1 个页脚 | 页码、模板信息 |
| `/section[1]` | 第 1 个分节 | 页面设置、附件分节 |
| `/comments/c[@commentId=N]` | 指定批注 | 审阅意见定位 |
| `/body/sdt[1]` | 第 1 个内容控件 | 模板字段、受控输入 |

结构解析建议：

1. 先用 `get / --depth 2 --json` 获取文档顶层结构，判断正文、页眉页脚、批注、附件等对象是否存在。
2. 再用 `get /body --depth 4 --json` 获取主体段落、表格和 run 信息。
3. 对大型合同，不建议一次性获取过深 JSON。可以先读取段落和表格路径列表，再按路径逐个读取子树。
4. 对可变文档，优先保存 `paraId`、`textId` 等稳定标识。如果版本输出中包含这些属性，应和 path 一起保存。
5. 对回写场景，先 `query` 找到元素，再 `get` 确认上下文，最后 `set` 修改，修改后运行 `validate` 和 `view issues`。

段落解析后的标准内部结构建议如下：

```json
{
  "type": "paragraph",
  "path": "/body/p[12]",
  "text": "第三条 付款方式",
  "style": "Heading2",
  "numbering": "第三条",
  "runs": [
    {
      "path": "/body/p[12]/r[1]",
      "text": "第三条 付款方式",
      "bold": true
    }
  ],
  "source": {
    "file": "contract.docx",
    "officecli_version": "v1.0.115"
  }
}
```

表格解析后的标准内部结构建议如下：

```json
{
  "type": "table",
  "path": "/body/tbl[2]",
  "rows": [
    {
      "row_index": 1,
      "cells": [
        {
          "cell_index": 1,
          "path": "/body/tbl[2]/tr[1]/tc[1]",
          "text": "付款节点"
        },
        {
          "cell_index": 2,
          "path": "/body/tbl[2]/tr[1]/tc[2]",
          "text": "付款比例"
        }
      ]
    }
  ]
}
```

### 4.4 条款与章节解析

中文合同条款结构通常不完全依赖 Word 标题样式。常见情况包括：

- 标准标题样式：`Heading1`、`Heading2`、`标题 1`、`标题 2`。
- 手工标题：加粗、居中、字号较大，但样式仍是正文。
- 中文编号：`第一章`、`第一条`、`一、`、`（一）`、`1.`、`1.1`、`第1条`。
- 表格内条款：付款、验收、服务清单可能以表格形式存在。
- 附件条款：附件一、附件二中存在独立编号。

建议采用“样式 + 编号规则 + 关键词 + 路径上下文”的混合策略。

#### 4.4.1 样式优先识别

先查询标题样式：

```bash
officecli query contract.docx "paragraph[style=Heading1]" --json > heading1.json
officecli query contract.docx "paragraph[style=Heading2]" --json > heading2.json
```

如果合同模板使用中文样式名，需要先查看正文结构中的样式字段，再决定 selector：

```bash
officecli get contract.docx /body --depth 3 --json > body_tree.json
```

内部处理建议：

- 将 `Heading1`、`标题 1`、`Title` 等归一为 `level=1`。
- 将 `Heading2`、`标题 2`、含 `第X条` 的段落归一为 `level=2`。
- 对只有加粗、居中、较大字号的段落，结合文本长度和编号规则判断是否为标题。

#### 4.4.2 中文编号规则

建议在业务层定义条款编号正则：

```python
CLAUSE_PATTERNS = [
    r"^第[一二三四五六七八九十百千万零〇0-9]+章[ 　]*(.+)$",
    r"^第[一二三四五六七八九十百千万零〇0-9]+节[ 　]*(.+)$",
    r"^第[一二三四五六七八九十百千万零〇0-9]+条[ 　]*(.+)$",
    r"^[一二三四五六七八九十]+、[ 　]*(.+)$",
    r"^（[一二三四五六七八九十]+）[ 　]*(.+)$",
    r"^[0-9]+[.．、][ 　]*(.+)$",
    r"^[0-9]+(?:[.．][0-9]+)+[ 　]*(.+)$"
]
```

解析规则：

- `第X章` 通常作为一级章节。
- `第X条` 通常作为核心条款节点。
- `一、` 可作为章节或条款，需结合上下文判断。
- `（一）`、`1.`、`1.1` 可作为子条款。
- 如果一个段落只有编号没有标题，下一段可能是标题或正文，需要合并判断。

#### 4.4.3 关键词增强

中文合同的核心风险条款可通过关键词建立候选集：

```bash
officecli query contract.docx --find "违约责任" --json
officecli query contract.docx --find "解除" --json
officecli query contract.docx --find "保密" --json
officecli query contract.docx --find "知识产权" --json
officecli query contract.docx --find "争议解决" --json
```

关键词只用于召回，不应直接作为最终分类。最终条款分类建议结合：

- 标题文本。
- 当前条款正文。
- 上级章节标题。
- 表格标题和表头。
- 批注内容。
- 业务模型或规则库。

#### 4.4.4 条款树输出

建议输出条款树 `clauses.json`：

```json
[
  {
    "clause_id": "clause_003",
    "level": 2,
    "number": "第三条",
    "title": "付款方式",
    "path": "/body/p[18]",
    "start_path": "/body/p[18]",
    "end_path": "/body/p[24]",
    "text": "第三条 付款方式...",
    "children": [],
    "tables": [
      "/body/tbl[2]"
    ],
    "comments": [
      "/comments/c[@commentId=5]"
    ],
    "source": {
      "file": "contract.docx",
      "view": "get /body --depth 4 --json"
    }
  }
]
```

### 4.5 表格结构解析

中文合同中的关键事实经常在表格中，不能只保留 Markdown 或纯文本。典型表格包括：

- 合同主体信息表：甲方、乙方、统一社会信用代码、地址、联系人。
- 商务条款表：金额、税率、付款节点、发票类型、账户信息。
- 服务清单表：服务内容、数量、单价、交付时间。
- 验收标准表：交付物、验收方式、验收周期、责任人。
- 附件目录表：附件名称、版本、页数、效力优先级。

读取表格列表：

```bash
officecli query contract.docx "table" --json > tables_index.json
```

读取指定表格：

```bash
officecli get contract.docx /body/tbl[1] --depth 6 --json > table_1.json
```

表格解析建议：

1. 保存表格 path、所在段落上下文、前后标题。
2. 识别表头行，若首行包含“项目/内容”“付款节点/金额”等字段，则作为结构化表。
3. 对两列表格，优先按键值表解析。
4. 对多列表格，按表头归一字段名。
5. 对合并单元格、嵌套段落、多行说明保留原始 cell path 和原始文本。
6. 对金额、日期、比例、税率、账户等字段单独做格式归一。

推荐表格输出结构：

```json
{
  "path": "/body/tbl[3]",
  "title": "付款计划",
  "context_before": "第四条 合同价款及付款",
  "table_type": "payment_schedule",
  "headers": ["付款节点", "付款条件", "付款比例", "付款金额"],
  "rows": [
    {
      "row_index": 2,
      "cells": {
        "付款节点": {
          "path": "/body/tbl[3]/tr[2]/tc[1]",
          "text": "预付款"
        },
        "付款条件": {
          "path": "/body/tbl[3]/tr[2]/tc[2]",
          "text": "合同生效后五个工作日内"
        },
        "付款比例": {
          "path": "/body/tbl[3]/tr[2]/tc[3]",
          "text": "30%"
        },
        "付款金额": {
          "path": "/body/tbl[3]/tr[2]/tc[4]",
          "text": "人民币300,000元"
        }
      }
    }
  ]
}
```

### 4.6 批注、修订、内容控件与表单域

合同审查场景中，批注和修订往往比正文更重要。OfficeCLI 的 Word 支持面包括 comments、revisions、SDT、form fields 等对象，建议作为独立审阅数据层处理。

#### 4.6.1 批注

批注用途：

- 法务审查意见。
- 业务确认事项。
- 谈判保留点。
- 需对方确认的问题。

可通过文档结构或评论路径读取批注。若已知批注 ID：

```bash
officecli get contract.docx "/comments/c[@commentId=1]" --json
```

工程输出建议：

```json
{
  "comment_id": "1",
  "path": "/comments/c[@commentId=1]",
  "author": "Legal",
  "text": "建议明确逾期付款违约金上限。",
  "anchor_path": "/body/p[36]",
  "created_at": null,
  "status": "open"
}
```

批注处理策略：

- 不要把批注直接混入正文条款，应作为审阅层关联到对应 path。
- 如果批注锚点落在 run 中，向上归并到段落或条款。
- 对“已解决”“需确认”“高风险”等状态可在业务层归类。

#### 4.6.2 修订

修订用途：

- 识别对方新增或删除的条款。
- 识别金额、期限、责任上限等关键字段变更。
- 在合同定稿前生成修订风险清单。

官方 Word reference 中列出修订类型包括 `ins`、`del`、`format`、`moveFrom`、`moveTo`，并支持接受或拒绝修订的操作属性。示例：

```bash
# 接受全部修订
officecli set contract.docx / --prop accept-changes=all

# 拒绝全部修订
officecli set contract.docx / --prop reject-changes=all
```

合同解析系统建议：

- 默认不要自动接受或拒绝修订。
- 将修订文本、作者、类型、路径、所在条款保存到 `revisions.json`。
- 对金额、日期、违约责任、解除权、争议解决相关修订进行高优先级复核。
- 在生成给 LLM 的合同正文时，明确选择“原文版本”“接受修订后版本”或“带修订版本”，不能混用。

#### 4.6.3 内容控件与表单域

内容控件和表单域常用于合同模板字段，例如：

- 合同编号。
- 甲方名称、乙方名称。
- 金额、币种、税率。
- 签订日期、履行期限。
- 项目名称、服务范围。

读取内容控件：

```bash
officecli get contract.docx /body/sdt[1] --depth 4 --json
```

处理建议：

- 将 SDT 的 tag、alias、文本值与 path 一起保存。
- 如果模板使用 `{{party_a}}` 等占位符，也可用 `merge` 进行填充。
- 对受控字段建立字段白名单，避免把任意正文误识别为合同元数据。

### 4.7 渲染、质量检查与可追溯验证

OfficeCLI 的一个特点是提供面向 agent 的渲染闭环。对中文合同而言，渲染和质量检查主要用于人工复核与交付前检查。

HTML 渲染：

```bash
officecli view contract.docx html -o contract.html
```

截图：

```bash
officecli view contract.docx screenshot -o contract.png
```

实时预览：

```bash
officecli watch contract.docx
```

质量问题检查：

```bash
officecli view contract.docx issues --json > issues.json
```

OpenXML 验证：

```bash
officecli validate contract.docx --json > validate.json
```

质量检查建议重点关注：

- 空段落、重复标点、混用中英文标点。
- CJK 与 Latin 字体混用导致的显示问题。
- 标题样式不一致。
- 首行缩进漂移。
- 表格宽度、单元格溢出、跨页表格。
- 图片签章是否丢失。
- 页眉页脚中的合同编号是否一致。
- 目录页码是否需要刷新。
- 修订是否仍未接受或拒绝。

对于最终交付合同，建议形成一份解析审计包：

```text
contract_original.docx
officecli_version.txt
contract_text.txt
document_tree.json
clauses.json
tables.json
comments.json
revisions.json
issues.json
validate.json
contract.html
contract.png
parse_log.json
```

## 五、中文合同解析 Demo

### 5.1 完整示例代码

以下 Demo 展示如何用 Python 包装 OfficeCLI，完成中文合同的基础解析、条款识别、表格索引、问题检查和结果保存。由于本地环境未安装 `officecli`，该代码为可落地模板，需要在安装并验证命令行为后运行。

```python
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


DOCX = Path("contract.docx")
OUT_DIR = Path("contract_officecli_output")


CLAUSE_RE = re.compile(
    r"^("
    r"第[一二三四五六七八九十百千万零〇0-9]+[章节条款]"
    r"|[一二三四五六七八九十]+、"
    r"|（[一二三四五六七八九十]+）"
    r"|\([0-9]+\)"
    r"|[0-9]+(?:[.．][0-9]+)*[.．、]?"
    r")\s*(.*)$"
)

CORE_KEYWORDS = [
    "合同编号",
    "甲方",
    "乙方",
    "合同价款",
    "付款",
    "验收",
    "违约责任",
    "解除",
    "保密",
    "知识产权",
    "争议解决",
    "生效",
    "附件",
]


@dataclass
class Paragraph:
    path: str
    text: str
    style: str | None = None
    node_type: str | None = None


@dataclass
class Clause:
    clause_id: str
    level: int
    number: str
    title: str
    path: str
    text: str
    keyword_hits: list[str]


def run_cli(*args: str, expect_json: bool = False) -> Any:
    cmd = ["officecli", *args]
    if expect_json and "--json" not in cmd:
        cmd.append("--json")

    completed = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "OfficeCLI command failed\n"
            f"command: {' '.join(cmd)}\n"
            f"exit_code: {completed.returncode}\n"
            f"stderr: {completed.stderr.strip()}"
        )

    if expect_json:
        if not completed.stdout.strip():
            return None
        return json.loads(completed.stdout)

    return completed.stdout


def pick(node: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in node:
            return node[name]
    attrs = node.get("attributes") or node.get("Attributes") or {}
    for name in names:
        if name in attrs:
            return attrs[name]
        upper = name[:1].upper() + name[1:]
        if upper in attrs:
            return attrs[upper]
    return default


def child_nodes(node: Any) -> list[dict[str, Any]]:
    if not isinstance(node, dict):
        return []
    children = (
        node.get("children")
        or node.get("Children")
        or node.get("childNodes")
        or node.get("ChildNodes")
        or []
    )
    return [child for child in children if isinstance(child, dict)]


def walk(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, list):
        for item in node:
            yield from walk(item)
        return

    if not isinstance(node, dict):
        return

    yield node
    data = node.get("data") or node.get("Data")
    if isinstance(data, (dict, list)):
        yield from walk(data)

    for child in child_nodes(node):
        yield from walk(child)


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_paragraph_node(node: dict[str, Any]) -> bool:
    tag = str(pick(node, "tag", "type", "Type", default="")).lower()
    path = str(pick(node, "path", "Path", default=""))
    return tag in {"p", "paragraph"} or "/p[" in path


def extract_paragraphs(tree: Any) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    seen_paths: set[str] = set()

    for node in walk(tree):
        if not is_paragraph_node(node):
            continue

        path = str(pick(node, "path", "Path", default=""))
        if not path or path in seen_paths:
            continue

        text = normalize_text(str(pick(node, "text", "Text", "preview", "Preview", default="")))
        if not text:
            continue

        style = pick(node, "style", "Style", default=None)
        node_type = str(pick(node, "tag", "type", "Type", default="paragraph"))
        paragraphs.append(Paragraph(path=path, text=text, style=style, node_type=node_type))
        seen_paths.add(path)

    return paragraphs


def infer_level(number: str, style: str | None) -> int:
    style_text = str(style or "").lower()
    if "heading1" in style_text or "标题 1" in style_text:
        return 1
    if "heading2" in style_text or "标题 2" in style_text:
        return 2
    if re.match(r"^第.+章$", number):
        return 1
    if re.match(r"^第.+节$", number):
        return 2
    if re.match(r"^第.+条$", number):
        return 2
    if number.endswith("、"):
        return 2
    if number.startswith("（"):
        return 3
    if "." in number or "．" in number:
        return min(number.count(".") + number.count("．") + 2, 5)
    return 3


def keyword_hits(text: str) -> list[str]:
    return [kw for kw in CORE_KEYWORDS if kw in text]


def extract_clauses(paragraphs: list[Paragraph]) -> list[Clause]:
    clauses: list[Clause] = []
    current: Clause | None = None

    for para in paragraphs:
        match = CLAUSE_RE.match(para.text)
        style_text = str(para.style or "")
        is_heading_style = style_text and (
            "heading" in style_text.lower() or "标题" in style_text or "title" in style_text.lower()
        )

        if match or is_heading_style:
            if current:
                clauses.append(current)

            if match:
                number = match.group(1)
                title = match.group(2).strip() or para.text
            else:
                number = ""
                title = para.text

            current = Clause(
                clause_id=f"clause_{len(clauses) + 1:04d}",
                level=infer_level(number, para.style),
                number=number,
                title=title,
                path=para.path,
                text=para.text,
                keyword_hits=keyword_hits(para.text),
            )
            continue

        if current:
            current.text = f"{current.text}\n{para.text}"
            current.keyword_hits = sorted(set(current.keyword_hits + keyword_hits(para.text)))

    if current:
        clauses.append(current)

    return clauses


def extract_table_paths(tree: Any) -> list[str]:
    table_paths: list[str] = []
    seen: set[str] = set()

    for node in walk(tree):
        tag = str(pick(node, "tag", "type", "Type", default="")).lower()
        path = str(pick(node, "path", "Path", default=""))
        if (tag in {"tbl", "table"} or "/tbl[" in path) and path and path not in seen:
            table_paths.append(path)
            seen.add(path)

    return table_paths


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if not DOCX.exists():
        raise FileNotFoundError(f"Input file not found: {DOCX}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    version = run_cli("--version")
    (OUT_DIR / "officecli_version.txt").write_text(version, encoding="utf-8")

    text = run_cli("view", str(DOCX), "text")
    (OUT_DIR / "contract_text.txt").write_text(text, encoding="utf-8")

    outline = run_cli("view", str(DOCX), "outline", expect_json=True)
    save_json(OUT_DIR / "outline.json", outline)

    body_tree = run_cli("get", str(DOCX), "/body", "--depth", "5", expect_json=True)
    save_json(OUT_DIR / "body_tree.json", body_tree)

    paragraphs = extract_paragraphs(body_tree)
    save_json(OUT_DIR / "paragraphs.json", [asdict(item) for item in paragraphs])

    clauses = extract_clauses(paragraphs)
    save_json(OUT_DIR / "clauses.json", [asdict(item) for item in clauses])

    table_paths = extract_table_paths(body_tree)
    save_json(OUT_DIR / "table_paths.json", table_paths)

    for index, table_path in enumerate(table_paths, start=1):
        table_tree = run_cli("get", str(DOCX), table_path, "--depth", "6", expect_json=True)
        save_json(OUT_DIR / f"table_{index:02d}.json", table_tree)

    issues = run_cli("view", str(DOCX), "issues", expect_json=True)
    save_json(OUT_DIR / "issues.json", issues)

    validation = run_cli("validate", str(DOCX), expect_json=True)
    save_json(OUT_DIR / "validate.json", validation)

    # Optional visual artifacts. Enable after confirming the installed version supports these modes.
    # run_cli("view", str(DOCX), "html", "-o", str(OUT_DIR / "contract.html"))
    # run_cli("view", str(DOCX), "screenshot", "-o", str(OUT_DIR / "contract.png"))


if __name__ == "__main__":
    main()
```

### 5.2 运行方式

准备目录：

```text
project/
  contract.docx
  parse_contract_officecli.py
```

运行：

```bash
python parse_contract_officecli.py
```

预期输出：

```text
contract_officecli_output/
  officecli_version.txt
  contract_text.txt
  outline.json
  body_tree.json
  paragraphs.json
  clauses.json
  table_paths.json
  table_01.json
  table_02.json
  issues.json
  validate.json
```

如需提取特定条款候选，可单独执行：

```bash
officecli query contract.docx --find "违约责任" --json > breach_candidates.json
officecli query contract.docx --find "争议解决" --json > dispute_candidates.json
```

如需将合同模板中的占位符填充为正式合同：

```bash
officecli merge contract_template.docx contract_output.docx "{\"party_a\":\"甲方公司\",\"party_b\":\"乙方公司\",\"amount\":\"人民币100万元\"}"
```

如需将人工整理的样本文档导出为可回放结构：

```bash
officecli dump contract_sample.docx / -o contract_blueprint.json
officecli batch contract_new.docx --input contract_blueprint.json --json
```

### 5.3 输出结果说明

| 输出文件 | 内容 | 用途 |
| --- | --- | --- |
| `officecli_version.txt` | OfficeCLI 版本 | 解析审计、问题复现 |
| `contract_text.txt` | 纯文本视图 | 全文检索、LLM 输入、人工快速阅读 |
| `outline.json` | 大纲视图 | 初步章节树、目录核对 |
| `body_tree.json` | 正文 DOM 子树 | 路径级结构解析 |
| `paragraphs.json` | 段落列表 | 条款识别、字段抽取 |
| `clauses.json` | 条款树 | RAG 分块、审查任务、风险定位 |
| `table_paths.json` | 表格路径索引 | 表格逐个解析入口 |
| `table_XX.json` | 表格 DOM 子树 | 付款计划、主体信息、清单抽取 |
| `issues.json` | 文档质量问题 | 交付前检查 |
| `validate.json` | OpenXML 验证结果 | 文件合法性和回写后验证 |

## 六、按条款分块与内容使用

### 6.1 分块策略

OfficeCLI 提供 path 和结构树，适合将中文合同拆为可追溯 chunk。建议分块策略如下：

| Chunk 类型 | 切分依据 | 内容 | 元数据 |
| --- | --- | --- | --- |
| 合同元信息块 | 首页段落、主体信息表、内容控件 | 合同名称、编号、甲乙方、金额、日期 | 文件名、path、字段来源 |
| 章节块 | `第X章`、`一、`、Heading1 | 章节标题和下属条款摘要 | chapter path、level |
| 条款块 | `第X条`、Heading2、编号段落 | 条款标题、正文、子条款 | clause path、start/end path、number |
| 子条款块 | `（一）`、`1.`、`1.1` | 细分义务、条件、例外 | parent clause、level |
| 表格块 | `/body/tbl[N]` | 表头、行数据、上下文标题 | table path、row/cell path |
| 批注块 | comment 节点 | 审阅意见、作者、锚点 | comment path、anchor path |
| 修订块 | revision 节点 | 新增、删除、格式修订 | revision type、author、anchor path |
| 附件块 | 附件标题、后续段落和表格 | 附件条款、清单、技术要求 | appendix number、paths |

推荐 chunk 元数据：

```json
{
  "chunk_id": "contract_001_clause_004",
  "doc_type": "contract",
  "source_file": "contract.docx",
  "officecli_version": "v1.0.115",
  "chunk_type": "clause",
  "title": "第四条 合同价款及付款",
  "number": "第四条",
  "path": "/body/p[28]",
  "start_path": "/body/p[28]",
  "end_path": "/body/p[39]",
  "parent_path": "/body/p[12]",
  "text": "第四条 合同价款及付款...",
  "tables": ["/body/tbl[2]"],
  "comments": [],
  "revisions": [],
  "keywords": ["合同价款", "付款"]
}
```

### 6.2 内容使用场景

#### 6.2.1 合同字段抽取

可抽取字段：

- 合同名称、合同编号。
- 甲方、乙方、丙方。
- 签订日期、签订地点。
- 合同金额、币种、税率。
- 履行期限、交付时间、验收周期。
- 付款节点、付款条件、发票要求。
- 违约金、责任上限、解除条件。
- 保密期限、知识产权归属。
- 争议解决方式、管辖法院或仲裁机构。

实现建议：

- 对表格字段优先从 table cell 抽取。
- 对正文关键字段使用关键词召回 + 条款上下文抽取。
- 对模板字段优先从 SDT、form field 或 `{{key}}` 占位符抽取。
- 每个字段保存来源 path 和原文片段。

#### 6.2.2 条款审查

OfficeCLI 输出适合作为条款审查的结构化输入：

- 按条款块分别送入规则引擎或模型，降低上下文噪声。
- 对高风险条款保留原文 path，用于生成审查报告。
- 对批注、修订单独生成审阅清单。
- 对表格条款保留行列结构，避免付款计划被错误拼接。

审查输出建议：

```json
{
  "risk_id": "risk_010",
  "clause_path": "/body/p[45]",
  "clause_title": "违约责任",
  "risk_type": "liability_cap_missing",
  "risk_level": "high",
  "evidence": "本条约定逾期违约金，但未设置责任上限。",
  "suggestion": "建议增加违约金累计上限或总责任上限。"
}
```

#### 6.2.3 RAG 检索

RAG 管线建议：

```text
OfficeCLI 解析
  ↓
条款级 chunk
  ↓
字段归一和元数据补全
  ↓
向量化 + 关键词索引
  ↓
检索召回
  ↓
按 path 回查原文和表格
  ↓
生成带证据位置的回答
```

检索元数据建议包括：

- `contract_id`
- `source_file`
- `chunk_type`
- `path`
- `clause_number`
- `clause_title`
- `party_role`
- `keywords`
- `has_table`
- `has_comment`
- `has_revision`
- `page_or_render_anchor`，如通过渲染视图建立页面定位

### 6.3 模板生成与批量处理

OfficeCLI 不仅能解析，也能用于合同模板生成和批处理。

#### 模板填充

适合合同模板中使用明确占位符：

```text
甲方：{{party_a}}
乙方：{{party_b}}
合同金额：{{amount}}
签订日期：{{sign_date}}
```

填充命令：

```bash
officecli merge template.docx output.docx "{\"party_a\":\"甲方公司\",\"party_b\":\"乙方公司\",\"amount\":\"人民币100万元\",\"sign_date\":\"2026年6月20日\"}"
```

建议：

- 占位符命名采用英文 snake_case。
- 金额、日期、公司名称在传入前完成校验。
- 生成后运行 `validate`、`view issues` 和 HTML/截图渲染。

#### Dump / Batch 复用

适合把人工设计的合同样本转成可复用结构：

```bash
officecli dump sample_contract.docx / -o sample_contract_blueprint.json
officecli batch new_contract.docx --input sample_contract_blueprint.json --json
```

使用建议：

- 对标准模板、附件表格、封面页、签署页，可通过 dump 固化结构。
- 对业务变量仍建议使用 `merge` 或 `set` 按路径填充。
- Dump 结果属于结构蓝图，不应直接替代合同数据模型。

## 七、验证方案与边界说明

### 7.1 验证方案

落地前建议建立中文合同样本集，并按以下维度验证：

| 验证项 | 方法 | 通过标准 |
| --- | --- | --- |
| 文本完整性 | `view text` 与人工阅读对照 | 标题、正文、表格文本、签署语无明显缺失 |
| 条款层级 | `clauses.json` 与合同目录/人工标注对照 | 章节、条、子条款层级基本一致 |
| 路径追溯 | 随机抽样 path，使用 `get` 回查 | 每个字段和条款可定位到原始元素 |
| 表格解析 | 抽样付款表、主体表、服务清单 | 行列、表头、金额、日期保持正确 |
| 批注修订 | 构造含批注和修订的样本 | 批注、修订类型、锚点能被识别或保留 |
| 页眉页脚 | 含合同编号和页码的样本 | 能区分正文与页眉页脚噪声 |
| 模板填充 | 使用 `merge` 生成合同 | 占位符替换完整，中文格式正常 |
| 回写验证 | `set` 修改关键字段后 `validate` | 文件可打开，OpenXML 验证通过或问题可解释 |
| 渲染复核 | `view html` / `screenshot` | 中文字体、表格、签章显示可接受 |
| 性能 | 长合同和批量合同样本 | 耗时、内存、输出大小满足业务 SLA |

建议样本覆盖：

- 简单 Word 转合同。
- 带中文标题样式的标准模板。
- 手工编号和手工加粗标题的合同。
- 多级编号合同。
- 多表格合同。
- 含页眉页脚、封面、目录、附件的合同。
- 含批注、修订和内容控件的审阅版合同。
- 含图片签章和水印的合同。
- 中文路径、中文文件名、空格文件名。

### 7.2 边界说明

OfficeCLI 在中文合同解析中的主要边界如下：

- 主要面向 Office 源文件。扫描 PDF、图片合同、纸质合同 OCR 不应作为 OfficeCLI 的主处理对象。
- `.docx` 是中文合同解析的重点；`.doc`、PDF 导出、特殊格式处理需要结合插件和版本验证。
- CLI 工具本身不提供法律语义判断，需要业务规则或模型层完成风险审查。
- JSON 字段、selector 细节和插件能力随版本演进，生产系统必须固定版本并做回归测试。
- Word 文档中样式混乱、手工编号、嵌套表格、合并单元格会增加业务解析复杂度。
- 批注和修订的最终呈现方式可能与 Word 客户端视图存在差异，需要用人工样本校验。
- 渲染 HTML/截图依赖字体和平台环境，中文字体缺失会影响视觉复核。
- `raw` / `raw-set` 能力强，但会增加 OpenXML 破坏风险，除非确有必要，不建议作为常规解析入口。
- 自动接受或拒绝修订属于高风险写操作，合同系统应默认只读取和展示，不自动定稿。

## 八、总结与建议

`OfficeCLI` 适合作为中文合同 `docx` 源文档的结构化解析与自动化处理工具。它的核心价值在于：用命令行方式读取 Office 文档结构，用 path 建立元素级追溯，用 JSON 输出接入后端和 RAG 管线，并能进一步执行模板填充、文档修改、质量检查和渲染复核。

对于中文合同解析，推荐落地方式如下：

1. 将 `OfficeCLI` 定位为 `docx` 结构化入口，不承担法律判断。
2. 读取层使用 `view text`、`view outline`、`get /body --depth N --json` 和 `query`。
3. 条款层采用“样式 + 中文编号 + 关键词 + path 上下文”的混合识别策略。
4. 表格层保留行、列、单元格 path，不把关键商务表格简单压成纯文本。
5. 审阅层单独保存批注、修订、内容控件和表单域。
6. 生成层使用 `merge` 处理模板占位符，使用 `dump` / `batch` 复用成熟样本文档结构。
7. 验证层固定执行 `view issues`、`validate`、HTML/截图渲染和样本回归。
8. 生产层固定 OfficeCLI 版本，记录版本号、命令、输出和文件哈希。

优先级建议：

| 阶段 | 目标 | 交付物 |
| --- | --- | --- |
| POC | 验证中文合同 `docx` 读取、条款识别、表格抽取 | `contract_text.txt`、`body_tree.json`、`clauses.json`、`tables.json` |
| 试点 | 接入 20-50 份真实合同样本，验证样式、表格、批注、修订 | 样本回归报告、字段抽取准确率、问题清单 |
| 工程化 | 封装 OfficeCLI 调用服务，固定版本和审计日志 | 解析服务、输出 schema、监控指标 |
| 生产 | 接入合同审查、RAG、模板生成流程 | 条款库、风险审查报告、模板填充流水线 |

综合判断：如果业务能拿到原始 Word 合同，OfficeCLI 的 path、JSON、查询、批处理和渲染能力对中文合同结构解析有较高实用价值。落地风险主要在版本演进、复杂 Word 模板差异、中文样式不规范和审阅痕迹处理细节，需要通过固定版本和样本回归控制。

## 资料来源

- OfficeCLI GitHub 仓库：https://github.com/iOfficeAI/OfficeCLI
- OfficeCLI Releases：https://github.com/iOfficeAI/OfficeCLI/releases
- OfficeCLI Wiki 首页：https://github.com/iOfficeAI/OfficeCLI/wiki
- Word Reference：https://github.com/iOfficeAI/OfficeCLI/wiki/word-reference
- Command Reference：https://github.com/iOfficeAI/OfficeCLI/wiki/command-reference
- View Command：https://github.com/iOfficeAI/OfficeCLI/wiki/command-view
- Get Command：https://github.com/iOfficeAI/OfficeCLI/wiki/command-get
- Query Command：https://github.com/iOfficeAI/OfficeCLI/wiki/command-query
- Dump Command：https://github.com/iOfficeAI/OfficeCLI/wiki/command-dump
- Batch Command：https://github.com/iOfficeAI/OfficeCLI/wiki/command-batch
- Merge Command：https://github.com/iOfficeAI/OfficeCLI/wiki/command-merge
- Validate Command：https://github.com/iOfficeAI/OfficeCLI/wiki/command-validate
- OfficeCLI License：https://github.com/iOfficeAI/OfficeCLI/blob/main/LICENSE
