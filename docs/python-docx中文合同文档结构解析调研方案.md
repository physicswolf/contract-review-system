# python-docx 中文合同文档结构解析与内容使用调研方案

聚焦 DOCX 格式中文合同的条款结构解析、表格提取、批注/元数据读取与内容复用

## 目录

- 一、概述
- 1.1 工具简介
- 1.2 面向中文合同场景的定位
- 二、安装部署
- 2.1 环境要求
- 2.2 基础安装
- 2.3 工程化使用建议
- 三、支持的文档对象与合同要素
- 四、中文合同文档结构解析方案
- 4.1 整体架构
- 4.2 基础解析代码
- 4.3 按章节/条款解析合同
- 4.4 表格结构解析
- 4.5 批注、页眉页脚与元数据
- 4.6 结构化输出模型
- 五、中文合同章节解析 Demo
- 5.1 完整示例代码
- 5.2 运行方式
- 5.3 输出结果说明
- 六、按条款分块与内容使用
- 七、验证方案与边界说明
- 八、总结与建议
- 资料来源

## 一、概述

### 1.1 工具简介

`python-docx` 是用于读取、创建和更新 Microsoft Word `.docx` 文件的 Python 库。官方文档当前对应 Release v1.2.0；PyPI 显示 1.2.0 发布于 2025-06-16，项目定位为“Create, read, and update Microsoft Word .docx files”，运行要求为 Python 3.9 及以上。

从合同解析角度看，`python-docx` 的核心价值是直接读取 WordprocessingML 封装后的对象模型，将 DOCX 中的段落、表格、页眉页脚、批注、内联图片、样式、run 级格式、超链接和文档属性暴露为 Python 对象。它适合处理原始来源就是 Word 合同的场景，例如合同模板归档、条款库建设、签署前审阅、关键信息抽取、RAG 知识库预处理和自动生成合同草案。

### 1.2 面向中文合同场景的定位

中文合同通常具有较稳定的结构：合同名称、签约主体、鉴于条款、章节/条款编号、定义条款、权利义务、价款/付款、违约责任、争议解决、附件、签署页和审批批注。`python-docx` 不需要版面识别过程，可以直接从 DOCX 的逻辑结构读取这些内容，并保留许多合同解析需要的上下文。

| 合同对象 | python-docx 可读取的关键线索 | 典型用途 |
| --- | --- | --- |
| 合同标题与章节标题 | 段落文本、段落样式、编号文本、加粗/字号/居中等格式 | 生成条款树、导航目录、条款级索引 |
| 正文条款 | 段落顺序、run 文本、超链接、换行、制表符、字体格式 | 全文检索、摘要、风险规则匹配、条款复用 |
| 主体信息表、付款计划表、附件清单 | 表格行列、单元格文本、横向合并、缺失网格列、嵌套表格 | 键值字段抽取、金额/日期校验、结构化入库 |
| 审阅批注 | 批注内容、作者、时间、批注锚点范围 | 法务意见汇总、修订任务跟踪、审阅知识沉淀 |
| 页眉页脚与文档属性 | 页眉页脚文本、节信息、标题/作者/关键字/修订号等 core properties | 合同版本管理、编号识别、归档元数据补全 |

> **说明：** 定位结论：如果输入是可编辑 DOCX，且解析目标是“按合同逻辑结构使用内容”，`python-docx` 可以作为基础解析层。合同语义判断、风险识别、实体抽取和分块策略需要在它读取出的结构数据之上实现。

## 二、安装部署

### 2.1 环境要求

| 项目 | 建议 |
| --- | --- |
| Python 版本 | Python >= 3.9。生产项目建议固定小版本并记录运行环境。 |
| 操作系统 | Windows、Linux、macOS 均可运行；读取 DOCX 不依赖 Microsoft Word。 |
| 输入文件 | Microsoft Word 2007+ `.docx`。旧版 `.doc`、PDF、扫描件不属于 `python-docx` 的直接处理对象。 |
| 中文字体 | 读取文本不要求字体存在；若需要生成/改写 DOCX，模板中建议统一中文样式，例如宋体、微软雅黑、仿宋等。 |

### 2.2 基础安装

```
# 安装
pip install python-docx

# 验证
python - << "PY"
from docx import Document

doc = Document()
doc.add_heading("合同文档", level=1)
doc.add_paragraph("第一条 合同目的")
doc.save("sample_contract.docx")

loaded = Document("sample_contract.docx")
print(loaded.paragraphs[0].text)
PY
```

### 2.3 工程化使用建议

- 固定版本：在项目依赖中写明 `python-docx==1.2.0` 或经验证的版本，避免线上解析行为随依赖升级变化。
- 沉淀合同样本集：至少覆盖采购、销售、租赁、服务、劳动、保密协议、补充协议、框架协议等常见模板。
- 定义样式约定：要求模板使用标准标题样式或统一自定义样式，例如“合同标题”“一级条款”“二级条款”“签署页”。样式越稳定，结构解析越可靠。
- 保留原始证据：结构化输出中保存段落序号、表格序号、单元格坐标、样式名、原始文本，便于追溯和人工复核。
- 明确边界：不要把 OCR、PDF 版面还原、复杂修订痕迹识别放入 `python-docx` 基础层；这些应在输入转换或上层业务模块处理。

## 三、支持的文档对象与合同要素

| 对象类型 | python-docx 入口 | 中文合同解析价值 |
| --- | --- | --- |
| 文档主体 | `Document(path)`、`document.iter_inner_content()` | 按文档顺序遍历段落和表格，建立合同主内容流。 |
| 段落 | `Paragraph.text`、`Paragraph.style`、`Paragraph.paragraph_format` | 识别标题、条款正文、签署页文本、定义项和编号段落。 |
| run 与超链接 | `Paragraph.runs`、`Paragraph.iter_inner_content()` | 保留强调、下划线、字体、颜色、链接地址，适合审查重点标记和模板占位符。 |
| 表格 | `Table.rows`、`Row.cells`、`Cell.text`、`Cell.grid_span` | 抽取主体信息、付款节点、货物/服务明细、附件清单、签署栏。 |
| 嵌套内容 | `Cell.iter_inner_content()`、`Cell.tables` | 处理合同表格单元格内继续包含段落、清单或子表的情况。 |
| 节、页眉、页脚 | `document.sections`、`section.header`、`section.footer` | 读取合同编号、密级、版本号、页脚声明等非正文信息。 |
| 批注 | `document.comments`、`Document.add_comment()` | 汇总法务审阅意见，或在自动审查后写回问题批注。 |
| 内联图片 | `document.inline_shapes` | 定位签章图片、二维码、附件截图等嵌入对象；图片语义需要业务层处理。 |
| 核心属性 | `document.core_properties` | 读取标题、作者、关键字、版本、创建/修改时间等归档字段。 |

## 四、中文合同文档结构解析方案

### 4.1 整体架构

- **DOCX 输入**合同模板、签署前合同、审阅稿、补充协议

- **对象遍历**`Document.iter_inner_content()` 按顺序读取段落和表格

- **结构识别**样式、编号、中文条款模式、格式线索

- **内容归一**清洗空白、统一全角半角、保留原文与格式

- **结构化模型**条款树、表格矩阵、批注、页眉页脚、元数据

- **内容使用**JSON、Markdown、HTML、RAG 分块、字段抽取、风险审查

实现上建议将解析流程拆成四层：

1. 读取层：只负责把 `python-docx` 对象转换为稳定的内部记录，避免业务判断散落在读取代码里。
2. 结构层：基于样式和编号规则识别标题层级、条款层级、正文归属和附件边界。
3. 语义层：抽取合同主体、金额、日期、履行期限、违约责任、争议解决等字段。
4. 使用层：生成可检索 JSON、可视化 HTML、条款级 Markdown、向量库 chunk、审查报告或批注回写。

### 4.2 基础解析代码

```
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

def normalize_text(text: str) -> str:
    """保留合同原意，只做轻量空白归一。"""
    return " ".join((text or "").replace("\u3000", " ").split())

def iter_document_blocks(doc: Document):
    """按正文出现顺序读取段落和表格。"""
    for block in doc.iter_inner_content():
        if isinstance(block, Paragraph):
            text = normalize_text(block.text)
            if text:
                yield {
                    "type": "paragraph",
                    "text": text,
                    "style": block.style.name if block.style else "",
                    "alignment": str(block.alignment) if block.alignment else "",
                }
        elif isinstance(block, Table):
            yield {
                "type": "table",
                "rows": table_to_rows(block),
                "style": block.style.name if block.style else "",
            }

def table_to_rows(table: Table):
    rows = []
    for r_idx, row in enumerate(table.rows):
        row_values = []
        for c_idx, cell in enumerate(row.cells):
            row_values.append({
                "row": r_idx,
                "col": c_idx,
                "text": normalize_text(cell.text),
                "grid_span": getattr(cell, "grid_span", 1),
            })
        rows.append({
            "grid_cols_before": getattr(row, "grid_cols_before", 0),
            "grid_cols_after": getattr(row, "grid_cols_after", 0),
            "cells": row_values,
        })
    return rows

doc = Document("合同样本.docx")
for item in iter_document_blocks(doc):
    print(item["type"], item.get("text") or f"{len(item['rows'])} rows")
```

### 4.3 按章节/条款解析合同

中文合同的标题识别应优先使用样式，其次使用编号模式，最后才使用格式线索。推荐规则如下：

| 优先级 | 识别依据 | 示例 | 处理建议 |
| --- | --- | --- | --- |
| 1 | 段落样式 | `Heading 1`、`Heading 2`、`合同标题`、`一级条款` | 模板稳定时最可靠；建立样式名到层级的映射表。 |
| 2 | 中文编号 | 第一章、第一条、一、（一）、1.1、1） | 使用正则识别；保留原始编号作为 `numbering` 字段。 |
| 3 | 格式线索 | 居中、加粗、较大字号、段前段后间距 | 用于兜底，需配合样本验证，避免把正文强调误判为标题。 |
| 4 | 上下文规则 | “附件一：”“签署页”“以下无正文” | 作为特殊边界标记，影响后续条款归属。 |

```
import re

STYLE_LEVEL = {
    "Title": 0,
    "Heading 1": 1,
    "Heading 2": 2,
    "Heading 3": 3,
    "合同标题": 0,
    "一级条款": 1,
    "二级条款": 2,
    "三级条款": 3,
}

PATTERNS = [
    (1, re.compile(r"^第[一二三四五六七八九十百千万零〇]+章\s*")),
    (2, re.compile(r"^第[一二三四五六七八九十百千万零〇]+条\s*")),
    (1, re.compile(r"^[一二三四五六七八九十]+[、.．]\s*")),
    (2, re.compile(r"^[（(][一二三四五六七八九十]+[）)]\s*")),
    (3, re.compile(r"^\d+(\.\d+){1,3}\s*")),
    (3, re.compile(r"^\d+[、.．)]\s*")),
]

def detect_heading_level(text: str, style_name: str) -> int | None:
    if style_name in STYLE_LEVEL:
        return STYLE_LEVEL[style_name]
    for level, pattern in PATTERNS:
        if pattern.match(text):
            return level
    return None

def build_clause_tree(blocks):
    """把段落/表格流组装成合同条款树。"""
    root = {"title": "ROOT", "level": -1, "children": [], "content": []}
    stack = [root]

    for block in blocks:
        if block["type"] == "paragraph":
            level = detect_heading_level(block["text"], block.get("style", ""))
            if level is not None:
                node = {
                    "title": block["text"],
                    "level": level,
                    "style": block.get("style", ""),
                    "children": [],
                    "content": [],
                }
                while stack and stack[-1]["level"] >= level:
                    stack.pop()
                stack[-1]["children"].append(node)
                stack.append(node)
                continue

        stack[-1]["content"].append(block)

    return root["children"]
```

### 4.4 表格结构解析

合同表格通常承担“字段容器”角色，尤其是签约主体、联系人、付款安排、交付清单、验收标准和附件目录。解析时不要只拼接 `cell.text`，应保留表格坐标、合并信息、缺失列和单元格内的段落顺序。

- 横向合并：读取 `cell.grid_span`，把一个单元格跨越多少布局列记录下来。
- 行首/行尾缺失列：读取 `row.grid_cols_before` 和 `row.grid_cols_after`，避免把不规则表误当成标准矩阵。
- 单元格内部结构：使用 `cell.iter_inner_content()` 递归读取单元格内段落和子表，保留“表中表”。
- 键值表识别：若一行呈现“字段名/字段值”或“甲方/乙方”结构，可在业务层转换为键值记录。

```
def parse_cell_content(cell):
    content = []
    for inner in cell.iter_inner_content():
        if isinstance(inner, Paragraph):
            text = normalize_text(inner.text)
            if text:
                content.append({"type": "paragraph", "text": text})
        elif isinstance(inner, Table):
            content.append({"type": "table", "rows": table_to_rows(inner)})
    return content

def parse_contract_table(table: Table):
    parsed_rows = []
    for r_idx, row in enumerate(table.rows):
        parsed_cells = []
        for c_idx, cell in enumerate(row.cells):
            parsed_cells.append({
                "row": r_idx,
                "col": c_idx,
                "text": normalize_text(cell.text),
                "grid_span": getattr(cell, "grid_span", 1),
                "content": parse_cell_content(cell),
            })
        parsed_rows.append({
            "row": r_idx,
            "grid_cols_before": getattr(row, "grid_cols_before", 0),
            "grid_cols_after": getattr(row, "grid_cols_after", 0),
            "cells": parsed_cells,
        })
    return parsed_rows
```

### 4.5 批注、页眉页脚与元数据

合同审阅场景中，正文不是唯一有效内容。页眉页脚可能保存合同编号、密级、版本；批注可能保存法务意见；文档属性可能保存作者、标题、关键词、修订号和修改时间。

```
def read_core_properties(doc):
    props = doc.core_properties
    return {
        "title": props.title,
        "author": props.author,
        "keywords": props.keywords,
        "subject": props.subject,
        "category": props.category,
        "revision": props.revision,
        "created": props.created.isoformat() if props.created else None,
        "modified": props.modified.isoformat() if props.modified else None,
    }

def read_headers_and_footers(doc):
    items = []
    for idx, section in enumerate(doc.sections):
        for name, container in [("header", section.header), ("footer", section.footer)]:
            text = "\n".join(p.text for p in container.paragraphs if p.text.strip())
            if text.strip():
                items.append({"section": idx, "type": name, "text": text.strip()})
    return items

def read_comments(doc):
    # 1.2.0 提供 document.comments；批注锚点与正文片段的精确关联可按项目需要补充。
    comments = []
    for comment in doc.comments:
        comments.append({
            "id": comment.comment_id,
            "author": comment.author,
            "initials": comment.initials,
            "text": "\n".join(p.text for p in comment.paragraphs if p.text.strip()),
        })
    return comments
```

### 4.6 结构化输出模型

推荐将解析结果输出为可追溯 JSON。每个条款节点同时保留标题、层级、路径、正文块、表格块和来源位置。结构示例：

```
{
  "document": {
    "file_name": "合同样本.docx",
    "core_properties": {"title": "技术服务合同", "revision": 3},
    "headers_footers": [],
    "comments": []
  },
  "clauses": [
    {
      "path": ["第一章 总则", "第一条 合同目的"],
      "level": 2,
      "title": "第一条 合同目的",
      "content": [
        {"type": "paragraph", "text": "甲乙双方根据平等自愿原则签订本合同。"},
        {"type": "table", "rows": []}
      ]
    }
  ]
}
```

## 五、中文合同章节解析 Demo

### 5.1 完整示例代码

```
#!/usr/bin/env python3
"""
中文合同 DOCX 结构解析 Demo
输入：合同 .docx
输出：clause_tree.json、clauses.md、tables.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

STYLE_LEVEL = {
    "Title": 0,
    "Heading 1": 1,
    "Heading 2": 2,
    "Heading 3": 3,
    "合同标题": 0,
    "一级条款": 1,
    "二级条款": 2,
    "三级条款": 3,
}

PATTERNS = [
    (1, re.compile(r"^第[一二三四五六七八九十百千万零〇]+章\s*")),
    (2, re.compile(r"^第[一二三四五六七八九十百千万零〇]+条\s*")),
    (1, re.compile(r"^[一二三四五六七八九十]+[、.．]\s*")),
    (2, re.compile(r"^[（(][一二三四五六七八九十]+[）)]\s*")),
    (3, re.compile(r"^\d+(\.\d+){1,3}\s*")),
    (3, re.compile(r"^\d+[、.．)]\s*")),
]

def normalize_text(text: str) -> str:
    return " ".join((text or "").replace("\u3000", " ").split())

def detect_heading_level(text: str, style_name: str) -> int | None:
    if style_name in STYLE_LEVEL:
        return STYLE_LEVEL[style_name]
    for level, pattern in PATTERNS:
        if pattern.match(text):
            return level
    return None

def run_records(paragraph: Paragraph):
    records = []
    for item in paragraph.iter_inner_content():
        if item.__class__.__name__ == "Hyperlink":
            records.append({
                "type": "hyperlink",
                "text": item.text,
                "url": item.url,
            })
        else:
            text = item.text
            if not text:
                continue
            records.append({
                "type": "run",
                "text": text,
                "bold": item.bold,
                "italic": item.italic,
                "underline": bool(item.underline),
                "font": item.font.name,
                "size_pt": item.font.size.pt if item.font.size else None,
            })
    return records

def paragraph_record(paragraph: Paragraph, block_index: int):
    text = normalize_text(paragraph.text)
    style_name = paragraph.style.name if paragraph.style else ""
    return {
        "type": "paragraph",
        "index": block_index,
        "text": text,
        "style": style_name,
        "heading_level": detect_heading_level(text, style_name),
        "runs": run_records(paragraph),
    }

def parse_cell_content(cell):
    content = []
    for inner in cell.iter_inner_content():
        if isinstance(inner, Paragraph):
            text = normalize_text(inner.text)
            if text:
                content.append({
                    "type": "paragraph",
                    "text": text,
                    "style": inner.style.name if inner.style else "",
                })
        elif isinstance(inner, Table):
            content.append({"type": "table", "rows": table_rows(inner)})
    return content

def table_rows(table: Table):
    rows = []
    for r_idx, row in enumerate(table.rows):
        cells = []
        for c_idx, cell in enumerate(row.cells):
            cells.append({
                "row": r_idx,
                "col": c_idx,
                "text": normalize_text(cell.text),
                "grid_span": getattr(cell, "grid_span", 1),
                "content": parse_cell_content(cell),
            })
        rows.append({
            "row": r_idx,
            "grid_cols_before": getattr(row, "grid_cols_before", 0),
            "grid_cols_after": getattr(row, "grid_cols_after", 0),
            "cells": cells,
        })
    return rows

def table_record(table: Table, block_index: int):
    return {
        "type": "table",
        "index": block_index,
        "style": table.style.name if table.style else "",
        "rows": table_rows(table),
    }

def iter_blocks(doc: Document):
    for idx, block in enumerate(doc.iter_inner_content()):
        if isinstance(block, Paragraph):
            rec = paragraph_record(block, idx)
            if rec["text"]:
                yield rec
        elif isinstance(block, Table):
            yield table_record(block, idx)

def build_clause_tree(blocks):
    root = {"title": "ROOT", "level": -1, "children": [], "content": []}
    stack = [root]

    for block in blocks:
        if block["type"] == "paragraph" and block["heading_level"] is not None:
            level = block["heading_level"]
            node = {
                "title": block["text"],
                "level": level,
                "source_index": block["index"],
                "style": block["style"],
                "children": [],
                "content": [],
            }
            while stack and stack[-1]["level"] >= level:
                stack.pop()
            stack[-1]["children"].append(node)
            stack.append(node)
        else:
            stack[-1]["content"].append(block)

    return root["children"]

def flatten_clauses(nodes, parents=None):
    parents = parents or []
    for node in nodes:
        path = parents + [node["title"]]
        yield {
            "path": path,
            "level": node["level"],
            "title": node["title"],
            "content": node["content"],
        }
        yield from flatten_clauses(node["children"], path)

def core_properties(doc: Document):
    p = doc.core_properties
    return {
        "title": p.title,
        "author": p.author,
        "keywords": p.keywords,
        "subject": p.subject,
        "revision": p.revision,
        "created": p.created.isoformat() if p.created else None,
        "modified": p.modified.isoformat() if p.modified else None,
    }

def export_markdown(clauses, output_file: Path):
    lines = []
    for clause in clauses:
        level = min(max(clause["level"], 1), 4)
        lines.append(f"{'#' * level} {clause['title']}")
        for block in clause["content"]:
            if block["type"] == "paragraph":
                lines.append(block["text"])
            elif block["type"] == "table":
                lines.append(f"[表格：{len(block['rows'])} 行]")
        lines.append("")
    output_file.write_text("\n".join(lines), encoding="utf-8")

def parse_contract(input_file: str, output_dir: str = "./output"):
    doc = Document(input_file)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    blocks = list(iter_blocks(doc))
    tree = build_clause_tree(blocks)
    clauses = list(flatten_clauses(tree))
    tables = [block for block in blocks if block["type"] == "table"]

    payload = {
        "file": str(input_file),
        "core_properties": core_properties(doc),
        "blocks_count": len(blocks),
        "clauses_count": len(clauses),
        "clauses": clauses,
    }

    (out / "clause_tree.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "tables.json").write_text(
        json.dumps(tables, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    export_markdown(clauses, out / "clauses.md")

    print(f"解析完成：{input_file}")
    print(f"正文块：{len(blocks)}，条款：{len(clauses)}，表格：{len(tables)}")
    print(f"输出目录：{out.resolve()}")

if __name__ == "__main__":
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "./output"
    parse_contract(input_path, output_path)
```

### 5.2 运行方式

```
# 安装依赖
pip install python-docx

# 解析中文合同
python parse_docx_contract.py 合同样本.docx ./contract_output
```

### 5.3 输出结果说明

| 输出文件 | 说明 | 后续用途 |
| --- | --- | --- |
| `clause_tree.json` | 合同条款树、条款路径、正文块、表格块、文档属性 | 入库、审查、检索、接口返回 |
| `tables.json` | 所有表格的行列、单元格文本、合并信息和嵌套内容 | 主体信息、金额、日期、清单类字段抽取 |
| `clauses.md` | 按条款层级导出的 Markdown | 人工复核、知识库导入、文本检索 |

## 六、按条款分块与内容使用

中文合同内容复用的核心不是按固定字数切分，而是先保留条款路径，再在条款内部按段落和表格拆分。每个 chunk 应携带合同名、条款路径、原始标题、正文文本、表格摘要、来源索引和可追溯 ID。

### 6.1 分块策略

- 短条款：单个条款文本低于阈值时保留为一个 chunk。
- 长条款：按自然段拆分，所有子 chunk 都保留同一条款路径。
- 表格：保留结构化 JSON，同时生成一份可检索的纯文本摘要，例如“付款节点：首付款，金额：人民币 100 万元”。
- 附件：附件标题进入路径，附件正文和表格单独分块，避免和主合同条款混淆。
- 签署页：作为独立块保存，可用于签署主体、签署日期、盖章状态检查。

```
def block_to_text(block):
    if block["type"] == "paragraph":
        return block["text"]
    if block["type"] == "table":
        lines = []
        for row in block["rows"]:
            values = [cell["text"] for cell in row["cells"] if cell["text"]]
            if values:
                lines.append(" | ".join(values))
        return "\n".join(lines)
    return ""

def chunk_clauses(clauses, max_chars=900):
    chunks = []
    for idx, clause in enumerate(clauses):
        buffer = []
        for block in clause["content"]:
            text = block_to_text(block).strip()
            if not text:
                continue
            if sum(len(x) for x in buffer) + len(text) > max_chars and buffer:
                chunks.append({
                    "id": f"clause-{idx}-{len(chunks)}",
                    "path": clause["path"],
                    "title": clause["title"],
                    "text": "\n".join(buffer),
                })
                buffer = []
            buffer.append(text)
        if buffer:
            chunks.append({
                "id": f"clause-{idx}-{len(chunks)}",
                "path": clause["path"],
                "title": clause["title"],
                "text": "\n".join(buffer),
            })
    return chunks
```

### 6.2 内容使用场景

| 使用场景 | 输入数据 | 处理方式 | 输出结果 |
| --- | --- | --- | --- |
| 合同字段抽取 | 条款文本、表格键值、页眉页脚、文档属性 | 规则 + 词典 + 模型抽取，字段带来源路径 | 合同名称、主体、金额、期限、争议解决、签署日期等 |
| 风险审查 | 条款树、重点条款、批注 | 按条款路径匹配审查规则，例如违约责任、管辖条款、付款条件 | 风险清单、建议修改、证据段落 |
| 条款库建设 | 标准条款、历史合同条款、附件条款 | 按标题路径归类，保留版本、业务线和适用条件 | 可复用条款片段、相似条款检索 |
| RAG 知识库 | 条款级 chunk、表格摘要、元数据 | 使用条款路径作为 metadata，向量检索后返回可追溯出处 | 合同问答、条款解释、证据引用 |
| 模板填充 | DOCX 模板、占位符、字段值 | 定位 run 中的占位符并替换，保留段落样式和部分 run 格式 | 自动生成合同初稿 |
| 审阅回写 | 风险点、建议、定位到的 run 或段落 | 使用批注 API 写入审阅意见，或生成单独审查报告 | 带批注的 DOCX 审阅稿 |

## 七、验证方案与边界说明

### 7.1 验证方案

建议用“样本覆盖 + 结构准确率 + 字段可追溯”验证，而不是只看是否能读出纯文本。

| 验证项 | 目标 | 验收标准 |
| --- | --- | --- |
| 段落/表格顺序 | 确认正文流顺序不丢失 | 人工抽样检查 30 份合同，正文段落和表格位置与 Word 阅读顺序一致。 |
| 一级/二级条款识别 | 建立稳定条款树 | 对“第一章/第一条/一、/（一）/1.1”等常见编号均能归入正确层级。 |
| 表格抽取 | 保留行列和合并线索 | 主体信息、付款表、附件清单可还原为结构化 JSON，合并单元格不导致字段错位。 |
| 中文文本完整性 | 避免漏字、错序、异常空白 | 抽取文本与 Word 复制出的文本进行抽样比对，关键条款无缺失。 |
| 批注和元数据 | 保留审阅上下文 | 批注内容、作者、文档标题、修订号等字段可被读取并进入输出。 |
| 可追溯性 | 审查结果可回到原文 | 每个字段、风险点、chunk 都保存条款路径和来源块索引。 |

### 7.2 边界说明

- `python-docx` 直接处理的是 `.docx`，不是扫描件、图片 PDF 或旧版二进制 `.doc`。
- 它读取的是 DOCX 逻辑结构，不负责还原 Word 渲染后的真实页面坐标；页码、分页效果会受 Word 排版环境影响。
- `document.paragraphs` 不包含修订标记中的插入/删除段落；`document.tables` 只列出文档顶层表格，不包含单元格内嵌套表格。需要完整读取时应使用 `iter_inner_content()` 递归处理。
- 复杂内容控件、域代码、脚注尾注、图表对象、文本框、修订痕迹等对象的公开 API 覆盖有限，项目中应通过样本验证确定是否需要读取底层 XML。
- 标题识别不会自动理解合同语义；“第一条”到底是一级还是二级，应由合同模板规范和业务规则决定。
- 模板填充时不要简单替换 `Paragraph.text`，因为该操作会重建段落文本并丢失 run 级格式；应尽量按 run 或占位符边界替换。

> **注意：** 实施建议：先把输入合同限定为可编辑 DOCX，并建立统一模板样式；当样式不稳定时，再补充编号正则和格式线索。这样可以让 `python-docx` 的解析结果保持可解释、可测试和可回溯。

## 八、总结与建议

| 维度 | 结论 |
| --- | --- |
| 安装部署 | 部署简单，`pip install python-docx` 即可，读取 DOCX 不依赖 Office。 |
| 中文合同结构解析 | 适合从 DOCX 逻辑结构中提取段落、表格和样式；配合标题样式和编号规则可构建条款树。 |
| 表格内容使用 | 可读取行列、单元格文本、横向合并和嵌套表格，适合主体信息、付款计划、附件清单等字段抽取。 |
| 审阅与元数据 | 可访问批注、文档属性、页眉页脚和内联对象，适合法务审阅意见归档和合同版本管理。 |
| 内容复用 | 推荐输出条款树、表格 JSON 和条款级 chunk，用于检索、RAG、风险审查、条款库和模板填充。 |
| 工程边界 | 不承担 OCR、PDF 版面解析、语义风险判断和复杂修订痕迹解析；这些需要输入转换或上层业务规则补充。 |

推荐方案：中文合同 DOCX → `python-docx` 按文档顺序读取段落/表格 → 样式和中文编号规则构建条款树 → 表格、批注、页眉页脚、元数据补充上下文 → 输出 JSON / Markdown / HTML / RAG chunk → 支撑字段抽取、风险审查、条款复用和审阅回写。

落地优先级建议：先完成“读取 DOCX + 条款树 + 表格 JSON + Markdown 复核页”；验证样本稳定后，再增加批注回写、模板填充和业务字段抽取。这样可以把 `python-docx` 的稳定对象模型作为底座，同时让合同语义规则在上层独立演进。

## 资料来源

- python-docx 官方文档首页：[https://python-docx.readthedocs.io/en/latest/](https://python-docx.readthedocs.io/en/latest/)
- python-docx Document API：[https://python-docx.readthedocs.io/en/latest/api/document.html](https://python-docx.readthedocs.io/en/latest/api/document.html)
- python-docx Text API：[https://python-docx.readthedocs.io/en/latest/api/text.html](https://python-docx.readthedocs.io/en/latest/api/text.html)
- python-docx Table API：[https://python-docx.readthedocs.io/en/latest/api/table.html](https://python-docx.readthedocs.io/en/latest/api/table.html)
- python-docx Comments 用户指南：[https://python-docx.readthedocs.io/en/latest/user/comments.html](https://python-docx.readthedocs.io/en/latest/user/comments.html)
- PyPI 项目页：[https://pypi.org/project/python-docx/](https://pypi.org/project/python-docx/)
