# PyMuPDF4LLM 中文合同文档结构解析与内容使用调研方案

## 目录

- 一、概述
- 1.1 工具简介
- 1.2 面向中文合同场景的定位
- 二、安装部署
- 2.1 环境要求
- 2.2 基础安装
- 2.3 OCR 与中文语言配置
- 2.4 工程化使用建议
- 三、支持的文档对象与合同要素
- 四、中文合同文档解析方案
- 4.1 整体架构
- 4.2 基础解析代码
- 4.3 Markdown 结构解析
- 4.4 JSON / bbox 结构解析
- 4.5 OCR 与扫描合同处理
- 4.6 表格、图片、签章与页眉页脚
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

`pymupdf4llm` 是 PyMuPDF 面向 LLM / RAG 场景的高层扩展包，用于把 PDF 等文档转换为 Markdown、JSON 或纯文本。官方文档描述其特点是轻量、无需 GPU，内置布局分析能力，可将文档内容整理成适合 LLM、向量检索和 RAG 管线使用的结构化数据。

截至本次调研日期，PyPI 显示当前版本为 `1.27.2.3`，发布日期为 2026-04-24，运行要求为 Python `>=3.10`。官方文档也标注覆盖版本至 `1.27.2.3`。

核心 API 包括：

| API | 输出 | 主要用途 |
| --- | --- | --- |
| `to_markdown(path_or_doc)` | Markdown 字符串或 page chunk 列表 | LLM 输入、RAG 分块、人工复核 |
| `to_json(path_or_doc)` | JSON 字符串 | bbox、layout、元素类型、坐标追溯 |
| `to_text(path_or_doc)` | 纯文本字符串 | 简单检索、全文索引、规则匹配 |
| `LlamaMarkdownReader().load_data(path)` | LlamaIndex Document 列表 | 直接接入 LlamaIndex |
| `get_key_values(path_or_doc)` | 表单字段列表 | 读取带 widget 的 Form PDF 键值 |
| `markdown_to_pdf(md_path, ...)` | PyMuPDF Document 或 PDF 文件 | 将 Markdown 转回 PDF |

### 1.2 面向中文合同场景的定位

中文合同 PDF 常见来源包括：Word 转 PDF、系统套打 PDF、扫描盖章件、含图片签章的电子合同、带附件的多页合同。`pymupdf4llm` 的优势在于直接面向 PDF 解析，能够输出 Markdown 和 JSON，并在需要时自动启用 OCR。

在中文合同解析中，建议把 `pymupdf4llm` 定位为“PDF 内容结构化入口层”：

- 从 PDF 中提取自然阅读顺序文本，减少多栏、页眉页脚、表格、图片区域对普通文本抽取的干扰。
- 用 Markdown 的标题、列表、表格形式承接合同条款结构，便于人工复核和 RAG 切分。
- 用 JSON 中的 bbox、layout element、page boxes 等信息建立可追溯证据链。
- 对扫描合同或文本层异常合同，使用自动 OCR、强制 OCR 或自定义 OCR 插件恢复文本。
- 对图片、签章、附件页、页眉页脚进行可控保留或排除。

需要明确的是，`pymupdf4llm` 不会自动理解“违约责任是否合理”“付款条件是否有风险”等法律语义；它提供的是文档内容和结构数据，合同字段抽取、风险审查、条款分类仍需业务规则或模型层完成。

## 二、安装部署

### 2.1 环境要求

| 项目 | 建议 |
| --- | --- |
| Python 版本 | Python `>=3.10` |
| 主要依赖 | 安装 `pymupdf4llm` 会自动安装或升级 `PyMuPDF` 和 `pymupdf-layout` |
| 运行环境 | 本地运行，无需 GPU、云服务或 LLM token |
| 默认输入 | PDF 为主要对象；XPS/OXPS、EPUB/MOBI/FB2、图片等也可处理 |
| Office 支持 | DOCX/XLSX/PPTX/HWP 等 Office 格式需要配合 PyMuPDF Pro |
| 许可证 | PyPI 标注为 AGPL v3 或 Artifex 商业许可双许可证 |

### 2.2 基础安装

```bash
pip install pymupdf4llm
```

基础验证：

```python
import pymupdf4llm

md = pymupdf4llm.to_markdown("contract.pdf")
print(md[:1000])
```

输出到文件：

```python
from pathlib import Path
import pymupdf4llm

md = pymupdf4llm.to_markdown("contract.pdf")
Path("contract.md").write_text(md, encoding="utf-8")
```

### 2.3 OCR 与中文语言配置

官方文档显示，`pymupdf4llm` 支持自动 OCR。默认情况下，它会分析页面是否需要 OCR：如果页面无可选文本、文本乱码、图片区域疑似包含文字，或存在模拟文字的矢量图形，就可能触发 OCR。OCR 可通过参数控制：

```python
import pymupdf4llm

# 自动 OCR，默认 use_ocr=True
md = pymupdf4llm.to_markdown("mixed_contract.pdf")

# 强制指定页面 OCR，pages 使用 0-based 页码
md = pymupdf4llm.to_markdown(
    "contract_scan.pdf",
    pages=[0, 1, 2],
    force_ocr=True,
    ocr_language="chi_sim+eng",
)

# 禁用 OCR：适合确信 PDF 都是数字文本的场景
md = pymupdf4llm.to_markdown("digital_contract.pdf", use_ocr=False)
```

中文合同的 OCR 建议：

- 如果使用 Tesseract，安装中文简体语言包，并在调用时设置 `ocr_language="chi_sim+eng"`；繁体合同使用 `chi_tra+eng`。
- 若合同包含复杂印章、图片背景、低质量扫描，可优先评估 RapidOCR 或 PaddleOCR 插件。
- 不要对干净的数字 PDF 全量 `force_ocr=True`，官方文档明确提示这会显著降低速度，并可能降低干净文本质量。
- 对扫描件建议建立 OCR 质量抽样：合同名称、条款编号、金额、日期、主体名称、签章页是重点检查对象。

### 2.4 工程化使用建议

- 固定版本：建议在项目依赖中写明 `pymupdf4llm==1.27.2.3` 或经内部验证的版本。
- 明确输入分类：先区分数字 PDF、扫描 PDF、混合 PDF、图片合同、Office 文档。
- 保留中间产物：同时保存 Markdown、JSON、page chunk、图片目录和解析日志。
- 对合同正文和证据链分开建模：Markdown 适合阅读和切分，JSON/bbox 适合溯源和可视化定位。
- 将 OCR 设为可配置：按业务线、合同来源、文件质量决定是否自动 OCR、强制 OCR、禁用 OCR。
- 关注许可证：AGPL 与商业许可会影响闭源商业系统的引入方式，正式落地前需要法务或合规确认。

## 三、支持的文档对象与合同要素

| 文档对象 | PyMuPDF4LLM 能力 | 合同解析价值 |
| --- | --- | --- |
| 数字 PDF 正文 | Markdown / TXT / JSON 输出 | 提取合同条款、定义、权利义务、违约责任等文本 |
| 多页 PDF | `pages` 选择、`page_chunks=True` | 按页处理长合同，保留页码元数据 |
| 页眉页脚 | `header` / `footer` 参数控制 | 排除重复合同编号、页码、密级水印等噪声 |
| 标题层级 | Markdown `#` 标题、layout box class、TOC 辅助 | 构建合同章节树、条款目录 |
| 表格 | Markdown 表格、JSON layout / bbox、page chunk tables | 抽取主体信息、付款计划、服务清单、附件目录 |
| 图片与矢量图 | `write_images`、`embed_images`、graphics / picture box | 提取签章、二维码、附件截图、图片化条款 |
| 扫描页 | 自动 OCR、`force_ocr`、`use_ocr`、OCR 插件 | 恢复扫描合同文本 |
| 表单 PDF | `get_key_values()` | 抽取带 widget 的字段，例如表单合同中的甲方、金额、日期 |
| 文档元数据 | page chunk `metadata`、PyMuPDF metadata | 归档字段、来源文件、页数、标题、作者等 |
| LLM / RAG 集成 | LlamaIndex reader、LangChain 加载/切分方式 | 向量化、问答、条款检索、证据引用 |

## 四、中文合同文档解析方案

### 4.1 整体架构

```text
中文合同 PDF / 扫描 PDF / 图片合同
        ↓
PyMuPDF4LLM
        ↓
Markdown / JSON / TXT / Page Chunks / Images
        ↓
结构识别层
  - 合同标题
  - 章节标题
  - 条款编号
  - 表格区域
  - 附件与签署页
        ↓
内容归一层
  - 空白归一
  - 中文编号规范化
  - 页眉页脚去重
  - OCR 质量标记
        ↓
结构化输出
  - clause_tree.json
  - contract.md
  - tables.json
  - chunks.jsonl
  - images/
        ↓
业务使用
  - 字段抽取
  - 风险审查
  - RAG 检索
  - 条款库
  - 可视化溯源
```

### 4.2 基础解析代码

```python
from pathlib import Path
import json
import pymupdf4llm

input_pdf = "contract.pdf"
output_dir = Path("contract_output")
output_dir.mkdir(exist_ok=True)

# Markdown：适合人工复核和 RAG 文本切分
md = pymupdf4llm.to_markdown(
    input_pdf,
    header=False,
    footer=False,
    use_ocr=True,
    ocr_language="chi_sim+eng",
)
(output_dir / "contract.md").write_text(md, encoding="utf-8")

# JSON：适合 bbox / layout / 坐标追溯
json_text = pymupdf4llm.to_json(
    input_pdf,
    use_ocr=True,
    ocr_language="chi_sim+eng",
)
(output_dir / "contract_layout.json").write_text(json_text, encoding="utf-8")

# Page chunks：适合页级元数据和向量库入库
chunks = pymupdf4llm.to_markdown(
    input_pdf,
    page_chunks=True,
    header=False,
    footer=False,
    use_ocr=True,
    ocr_language="chi_sim+eng",
)
(output_dir / "page_chunks.json").write_text(
    json.dumps(chunks, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
```

### 4.3 Markdown 结构解析

`to_markdown()` 的输出是最适合直接给 LLM 和人工复核的格式。它可能包含：

- `#` 到 `######` 标题；
- 段落正文；
- 有序 / 无序列表；
- GitHub 风格表格；
- 加粗、斜体、等宽文本；
- 图片引用；
- 页面分隔符（可选）。

中文合同条款树建议从 Markdown 解析，而不是只从纯文本解析。原因是 Markdown 已经承接了一部分布局和标题判断结果。

```python
import re

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CN_CLAUSE_RE = re.compile(
    r"^(第[一二三四五六七八九十百千万零〇]+[章节条]|"
    r"[一二三四五六七八九十]+[、.．]|"
    r"[（(][一二三四五六七八九十]+[）)]|"
    r"\d+(\.\d+){1,3})"
)

def parse_markdown_clauses(md_text: str):
    root = {"title": "ROOT", "level": 0, "children": [], "content": []}
    stack = [root]

    for line in md_text.splitlines():
        raw = line.strip()
        if not raw:
            continue

        match = HEADING_RE.match(raw)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
        elif CN_CLAUSE_RE.match(raw):
            # 对合同编号做兜底识别。若 Markdown 未识别为标题，仍可转为低层级条款。
            level = 3
            title = raw
        else:
            stack[-1]["content"].append(raw)
            continue

        node = {"title": title, "level": level, "children": [], "content": []}
        while stack and stack[-1]["level"] >= level:
            stack.pop()
        stack[-1]["children"].append(node)
        stack.append(node)

    return root["children"]
```

标题识别策略：

| 优先级 | 线索 | 示例 | 建议 |
| --- | --- | --- | --- |
| 1 | Markdown 标题 | `# 技术服务合同`、`## 第一章 总则` | 作为主线索 |
| 2 | 中文条款编号 | `第一条`、`一、`、`（一）` | 作为兜底补齐 |
| 3 | PDF TOC / bookmark | `TocHeaders`、page chunk `toc_items` | 对带书签的正式合同优先使用 |
| 4 | 字体 / bbox / layout class | `title`、`section-header`、字号 | 用 JSON 辅助复核 |
| 5 | 业务关键词 | `附件一`、`签署页`、`以下无正文` | 标记合同边界和特殊页 |

### 4.4 JSON / bbox 结构解析

`to_json()` 返回包含坐标、布局类型、字体信息和文本元素的结构化 JSON。对于中文合同，JSON 的主要价值不是直接给 LLM，而是做可追溯定位和结构校验：

- 记录条款文本来自第几页、哪个 bbox；
- 区分正文、标题、表格、图片、页眉、页脚等 layout box；
- 发现 OCR 区域、图片区域、签章区域；
- 支持前端高亮展示风险条款所在位置；
- 对表格抽取结果进行坐标级复核。

官方 API 中，box class / boxclass 可能包括：

```text
text
picture
table
caption
title
section-header
page-header
page-footer
list-item
footnote
formula
```

建议输出结构：

```json
{
  "file": "contract.pdf",
  "pages": [
    {
      "page_number": 1,
      "width": 595.0,
      "height": 842.0,
      "blocks": [
        {
          "type": "title",
          "text": "技术服务合同",
          "bbox": [100, 80, 500, 120]
        }
      ]
    }
  ],
  "clauses": [
    {
      "path": ["第一章 总则", "第一条 合同目的"],
      "text": "甲乙双方根据平等自愿原则签订本合同。",
      "sources": [
        {"page": 1, "bbox": [72, 130, 520, 180]}
      ]
    }
  ]
}
```

### 4.5 OCR 与扫描合同处理

中文合同会经常遇到“文字可见但不可选”的扫描 PDF，或“可选文本层乱码”的 PDF。`pymupdf4llm` 的 OCR 策略适合先作为自动处理层，但需要业务侧做质量闭环。

处理建议：

- 数字 PDF：默认 `use_ocr=False` 或 `use_ocr=True` 均可，建议先压测性能；如果合同来源稳定且都是可选文本，禁用 OCR 可减少耗时。
- 扫描 PDF：使用 `use_ocr=True`，安装中文 OCR 依赖，设置 `ocr_language="chi_sim+eng"`。
- 混合 PDF：保留默认自动 OCR，避免对干净页面重复 OCR。
- 文本层乱码：对问题页使用 `force_ocr=True`，不要对整份合同盲目强制 OCR。
- 历史 OCR 层质量差：可以通过自定义 `ocr_function` 和页面分析结果决定是否重做 OCR。

示例：

```python
import pymupdf4llm

def extract_scan_contract(pdf_path: str):
    return pymupdf4llm.to_markdown(
        pdf_path,
        header=False,
        footer=False,
        use_ocr=True,
        force_ocr=False,
        ocr_language="chi_sim+eng",
        ocr_dpi=300,
        show_progress=True,
    )
```

### 4.6 表格、图片、签章与页眉页脚

#### 表格

合同中的表格通常是高价值字段来源，例如：

- 甲乙方信息；
- 联系人和地址；
- 服务范围清单；
- 付款节点；
- 违约金计算标准；
- 附件目录；
- 验收标准。

Markdown 表格适合阅读和 LLM 输入；JSON / bbox 适合字段定位和复核。建议同时保存：

- `contract.md`：保留表格为 GFM pipe table；
- `contract_layout.json`：保留坐标和 layout；
- `tables.json`：业务侧二次解析出的表格结构。

#### 图片与签章

`to_markdown()` 支持 `write_images=True` 和 `embed_images=True`。合同签章场景建议优先写出图片文件，不建议默认 base64 内嵌到 Markdown，因为会显著增大文件体积。

```python
import pymupdf4llm

md = pymupdf4llm.to_markdown(
    "signed_contract.pdf",
    write_images=True,
    image_path="./contract_output/images",
    image_format="png",
    dpi=150,
    force_text=True,
)
```

业务侧可进一步对图片做：

- 签章图片数量统计；
- 签章页识别；
- 二维码或水印识别；
- 图片区域 OCR；
- 图片 bbox 与“甲方盖章”“乙方盖章”文字的邻近关系判断。

#### 页眉页脚

合同页眉页脚常见重复内容包括合同编号、页码、密级、公司名称、版本号。RAG 场景中重复页眉页脚会污染向量检索，应优先去掉：

```python
md = pymupdf4llm.to_markdown(
    "contract.pdf",
    header=False,
    footer=False,
)
```

如果页眉中包含合同编号、项目编号等关键元数据，则建议：

- 第一次解析保留 `header=True, footer=True`，抽取元数据；
- 正文入库时使用 `header=False, footer=False`；
- 元数据单独挂到合同级 metadata。

## 五、中文合同解析 Demo

### 5.1 完整示例代码

```python
#!/usr/bin/env python3
"""
中文合同 PDF 解析 Demo
输入：PDF / 扫描 PDF / 图片化合同 PDF
输出：Markdown、布局 JSON、页级 chunks、条款树、RAG chunks
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf4llm


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CN_CLAUSE_RE = re.compile(
    r"^(第[一二三四五六七八九十百千万零〇]+[章节条]|"
    r"[一二三四五六七八九十]+[、.．]|"
    r"[（(][一二三四五六七八九十]+[）)]|"
    r"\d+(\.\d+){1,3})"
)


def parse_markdown_clauses(md_text: str):
    root = {"title": "ROOT", "level": 0, "children": [], "content": []}
    stack = [root]

    for line_no, line in enumerate(md_text.splitlines(), start=1):
        raw = line.strip()
        if not raw:
            continue

        heading = HEADING_RE.match(raw)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
        elif CN_CLAUSE_RE.match(raw):
            level = 3
            title = raw
        else:
            stack[-1]["content"].append({"line": line_no, "text": raw})
            continue

        node = {
            "title": title,
            "level": level,
            "line": line_no,
            "children": [],
            "content": [],
        }
        while stack and stack[-1]["level"] >= level:
            stack.pop()
        stack[-1]["children"].append(node)
        stack.append(node)

    return root["children"]


def flatten_clauses(nodes, parents=None):
    parents = parents or []
    for node in nodes:
        path = parents + [node["title"]]
        yield {
            "title": node["title"],
            "level": node["level"],
            "path": path,
            "line": node["line"],
            "content": node["content"],
        }
        yield from flatten_clauses(node["children"], path)


def clause_text(clause):
    return "\n".join(item["text"] for item in clause["content"]).strip()


def chunk_clauses(clauses, max_chars=900):
    chunks = []
    for idx, clause in enumerate(clauses):
        text = clause_text(clause)
        if not text:
            continue

        buffer = []
        current_len = 0
        paragraphs = [p for p in text.splitlines() if p.strip()]

        for para in paragraphs:
            if buffer and current_len + len(para) > max_chars:
                chunks.append({
                    "id": f"clause-{idx}-{len(chunks)}",
                    "title": clause["title"],
                    "path": clause["path"],
                    "text": "\n".join(buffer),
                })
                buffer = []
                current_len = 0

            buffer.append(para)
            current_len += len(para)

        if buffer:
            chunks.append({
                "id": f"clause-{idx}-{len(chunks)}",
                "title": clause["title"],
                "path": clause["path"],
                "text": "\n".join(buffer),
            })

    return chunks


def parse_contract_pdf(input_file: str, output_dir: str = "./contract_output"):
    out = Path(output_dir)
    images = out / "images"
    out.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)

    md = pymupdf4llm.to_markdown(
        input_file,
        header=False,
        footer=False,
        use_ocr=True,
        force_ocr=False,
        ocr_language="chi_sim+eng",
        write_images=True,
        image_path=str(images),
        image_format="png",
        dpi=150,
        show_progress=True,
    )
    (out / "contract.md").write_text(md, encoding="utf-8")

    layout_json = pymupdf4llm.to_json(
        input_file,
        use_ocr=True,
        ocr_language="chi_sim+eng",
        write_images=False,
    )
    (out / "contract_layout.json").write_text(layout_json, encoding="utf-8")

    page_chunks = pymupdf4llm.to_markdown(
        input_file,
        page_chunks=True,
        header=False,
        footer=False,
        use_ocr=True,
        ocr_language="chi_sim+eng",
    )
    (out / "page_chunks.json").write_text(
        json.dumps(page_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    tree = parse_markdown_clauses(md)
    clauses = list(flatten_clauses(tree))
    rag_chunks = chunk_clauses(clauses)

    (out / "clause_tree.json").write_text(
        json.dumps(tree, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "clauses.json").write_text(
        json.dumps(clauses, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "rag_chunks.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in rag_chunks),
        encoding="utf-8",
    )

    print(f"解析完成：{input_file}")
    print(f"输出目录：{out.resolve()}")
    print(f"条款数：{len(clauses)}，RAG chunks：{len(rag_chunks)}，页 chunks：{len(page_chunks)}")


if __name__ == "__main__":
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "./contract_output"
    parse_contract_pdf(input_path, output_path)
```

### 5.2 运行方式

```bash
pip install pymupdf4llm

# 若处理中文扫描件，请安装对应 OCR 引擎和中文语言资源
# 示例：Ubuntu + Tesseract
sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng

python parse_contract_pdf.py 合同样本.pdf ./contract_output
```

### 5.3 输出结果说明

| 输出文件 / 目录 | 说明 | 用途 |
| --- | --- | --- |
| `contract.md` | 去除页眉页脚后的 Markdown 主文本 | 人工复核、LLM 输入、Markdown 切分 |
| `contract_layout.json` | JSON 布局、bbox、元素信息 | 坐标追溯、前端高亮、结构校验 |
| `page_chunks.json` | 每页 chunk、metadata、page boxes、toc items | 页级入库、页码引用、长文档处理 |
| `clause_tree.json` | 基于 Markdown 标题和中文编号构建的条款树 | 合同目录、条款级检索 |
| `clauses.json` | 扁平条款列表，包含 path 和 content | 字段抽取、风险审查 |
| `rag_chunks.jsonl` | 条款级 RAG chunks | 向量库、问答、语义检索 |
| `images/` | 抽取出的图片或签章区域 | 签章检测、二维码识别、图片复核 |

## 六、按条款分块与内容使用

### 6.1 分块策略

中文合同不建议仅按固定字数切分。推荐顺序：

1. PDF → Markdown / JSON / page chunks；
2. Markdown → 条款树；
3. 条款树 → 条款级 chunk；
4. JSON / bbox → 给 chunk 补充页码和坐标证据；
5. 表格和图片 → 另建结构化字段或专门 chunk；
6. 输出到向量库或业务数据库。

chunk metadata 建议包含：

```json
{
  "id": "contract-001-clause-12",
  "contract_id": "contract-001",
  "file_path": "合同样本.pdf",
  "title": "第三条 服务内容",
  "path": ["第二章 服务范围", "第三条 服务内容"],
  "page_start": 3,
  "page_end": 4,
  "bbox_refs": [
    {"page": 3, "bbox": [72, 120, 520, 280]}
  ],
  "content_type": "clause",
  "ocr_used": false,
  "text": "乙方应按照附件一所列服务清单..."
}
```

### 6.2 内容使用场景

| 使用场景 | 输入 | 处理方式 | 输出 |
| --- | --- | --- | --- |
| 合同字段抽取 | Markdown 条款、表格、页眉元数据 | 规则 + 模型抽取，字段带来源路径 | 主体、金额、期限、争议解决、签署日期 |
| 风险审查 | 条款树、RAG chunks、bbox | 按条款路径匹配审查规则 | 风险点、建议、证据页码 |
| 合同问答 | 条款级 chunk、page metadata | 向量检索 + rerank + 引用 | 带条款出处的回答 |
| 条款库建设 | 历史合同条款、合同类型、业务线 | 按条款标题和语义聚类 | 标准条款、替代条款、相似条款 |
| 签章检查 | 图片目录、签署页文本、bbox | 图像检测 + 关键字邻近关系 | 是否盖章、盖章主体、签署页完整性 |
| 付款条件抽取 | Markdown 表格、JSON 表格 bbox | 表格结构化 + 金额日期解析 | 付款节点、金额、比例、条件 |
| 可视化复核 | JSON bbox、原 PDF 页面 | 页面高亮定位 | 人工复核界面 |

### 6.3 RAG 管线建议

```python
import json
import pymupdf4llm
from langchain.text_splitter import MarkdownTextSplitter

md = pymupdf4llm.to_markdown(
    "contract.pdf",
    header=False,
    footer=False,
    use_ocr=True,
    ocr_language="chi_sim+eng",
)

splitter = MarkdownTextSplitter(
    chunk_size=900,
    chunk_overlap=100,
)
docs = splitter.create_documents([md])

for idx, doc in enumerate(docs):
    doc.metadata.update({
        "source": "contract.pdf",
        "chunk_id": idx,
        "parser": "pymupdf4llm",
    })
```

实际落地时，应优先使用条款树切分，再用 Markdown splitter 作为条款过长时的二级切分策略。

## 七、验证方案与边界说明

### 7.1 验证方案

| 验证项 | 目标 | 验收标准 |
| --- | --- | --- |
| 数字 PDF 文本完整性 | 验证原生文本抽取质量 | 合同名称、主体、金额、日期、条款编号无关键漏字 |
| 扫描 PDF OCR 质量 | 验证中文 OCR 可用性 | 重点字段抽样准确率达到业务阈值，乱码页可被发现 |
| 条款层级识别 | 验证章节树可靠性 | `第一章`、`第一条`、`一、`、`（一）`、`1.1` 可归入合理层级 |
| 表格解析 | 验证付款表、主体表可用性 | 表格内容不串行，关键字段可抽取，复杂表格可人工复核 |
| 页眉页脚处理 | 降低 RAG 噪声 | 重复页码、公司名、合同编号不会大量进入正文 chunk |
| bbox 追溯 | 支持证据定位 | 风险点和字段能追溯到页码与坐标区域 |
| 签章图片 | 保留签署证据 | 签章页图片能输出或定位，签署页文本可解析 |
| 性能 | 支撑批量合同处理 | 数字 PDF 和扫描 PDF 分别建立耗时基准，OCR 不阻塞主流程 |

### 7.2 边界说明

- `pymupdf4llm` 的核心对象是 PDF 等文档内容抽取，不负责法律语义判断。
- Office 文档支持需要 PyMuPDF Pro；普通 `pymupdf4llm` 方案中，应优先处理 PDF。
- OCR 不是万能修复。低分辨率、倾斜、遮挡、印章覆盖、手写签字会影响识别效果。
- 表格输出为 Markdown 或 JSON 布局信息，并不等同于业务字段结构；字段抽取仍需表格后处理。
- 标题层级可能受 PDF 字体、版式、书签、OCR 结果影响。正式项目应建立样本集验证，而不是完全依赖默认标题识别。
- `page_chunks=True` 是页级 chunk，不等同于条款级 chunk；合同 RAG 更适合先解析条款树，再生成条款 chunk。
- `write_images=True` 会产生图片文件，需要规划存储、清理、脱敏和访问权限。
- AGPL / 商业许可需要在闭源或商业系统中提前确认合规路径。

## 八、总结与建议

| 维度 | 结论 |
| --- | --- |
| 安装部署 | `pip install pymupdf4llm` 即可，Python 要求 `>=3.10`，无需 GPU |
| PDF 文本解析 | 适合数字 PDF 的 Markdown、JSON、TXT 抽取，尤其适合 LLM / RAG 管线 |
| 中文扫描件 | 支持自动 OCR 和 OCR 插件；中文场景需要配置中文语言包或中文 OCR 引擎 |
| 合同结构解析 | Markdown 标题 + 中文编号正则 + JSON bbox 可构建条款树和证据链 |
| 表格处理 | 可生成 Markdown 表格和布局数据，适合进一步抽取付款、主体、清单字段 |
| 图片/签章 | 可写出图片或内嵌图片引用，适合签章页、二维码、附件图片处理 |
| RAG 适配 | 支持 page chunks、LlamaIndex、LangChain；合同场景建议二次构建条款 chunk |
| 工程边界 | 不负责法律风险判断、复杂表格业务语义、低质量 OCR 纠错和许可证合规决策 |

推荐落地链路：

```text
中文合同 PDF
  → pymupdf4llm.to_markdown(header=False, footer=False, use_ocr=True)
  → pymupdf4llm.to_json() / page_chunks=True
  → Markdown 条款树解析
  → 表格、图片、签章、页眉元数据单独结构化
  → 条款级 chunks + bbox 证据
  → 字段抽取 / 风险审查 / RAG 检索 / 可视化复核
```

最小可行方案建议：

1. 先支持数字 PDF 合同，输出 Markdown、JSON、page chunks。
2. 增加中文编号正则，生成条款树和条款级 RAG chunks。
3. 对样本中的扫描合同开启 OCR，并单独评估 OCR 准确率。
4. 对表格、签章页、附件页建立专项规则，不把它们简单当普通段落。
5. 所有字段和风险点必须保留页码、bbox 或条款路径，确保可追溯。

## 资料来源

- PyMuPDF4LLM 官方文档：https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/
- PyMuPDF4LLM API 文档：https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html
- PyMuPDF4LLM OCR Plugins 文档：https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/ocr-plugins.html
- PyMuPDF, LLM & RAG 文档：https://pymupdf.readthedocs.io/en/latest/rag.html
- PyPI 项目页：https://pypi.org/project/pymupdf4llm/
- GitHub 项目页：https://github.com/pymupdf/PyMuPDF4LLM
