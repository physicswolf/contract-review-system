# homepage PyMuPDF4LLM PDF 文档结构 JSON 调用说明

本文面向调用 `homepage/storage/parsing/{file_id}/document.json` 的使用者，说明如何从 PyMuPDF4LLM 解析的 PDF 结果中获取结构化合同内容。

示例原始文件：

```text
homepage/storage/uploads/2026/06/24/5cb3c675-5968-4917-93bf-6dd592f26817.pdf
```

示例解析结果：

```text
homepage/storage/parsing/5cb3c675-5968-4917-93bf-6dd592f26817/document.json
```

## 1. 结论

结构化章节树已经写入 `document.json` 顶层字段：

```text
contract_structure
```

调用方应优先读取：

```python
document["contract_structure"]
```

这份文件是 PyMuPDF4LLM 路径生成的自定义合同解析 JSON，不是 Docling 原始 JSON。它的结构更精简，常用字段是：

```text
texts
tables
contract_structure
warnings
```

需要特别注意：结构节点中的 `source_ref` 形如 `#/pages/3/lines/0`，它对应的是 `texts[*].prov[0].source_ref`，不是 `texts[*].self_ref`。

## 2. 当前示例文件的解析类型

该示例文件的关键元信息如下：

```json
{
  "schema_name": "PyMuPDF4LLMContractDocument",
  "version": "1.0.0",
  "name": "5cb3c675-5968-4917-93bf-6dd592f26817",
  "origin": {
    "filename": "5cb3c675-5968-4917-93bf-6dd592f26817.pdf",
    "mimetype": "application/pdf"
  },
  "parser": {
    "name": "pymupdf4llm-contract-parser",
    "pymupdf4llm": "1.27.2.3"
  }
}
```

含义：

```text
schema_name = PyMuPDF4LLMContractDocument
    说明这是 PyMuPDF4LLM PDF 解析路径生成的合同结构 JSON。

parser.name = pymupdf4llm-contract-parser
    说明 texts、tables、contract_structure 都来自 PyMuPDF4LLM Markdown 行解析和共用合同结构解析器。

contract_structure_parser 字段不存在
    对这份 JSON 是正常情况，因为它不是在 Docling JSON 上二次补充结构，而是直接构造完整解析结果。
```

## 3. 顶层 JSON 字段

这份 PDF `document.json` 的顶层字段包括：

```text
schema_name
version
name
origin
parser
texts
tables
contract_structure
warnings
```

调用方常用字段：

```text
contract_structure  结构化章节树，优先读取
texts               PyMuPDF4LLM Markdown 行转换后的文本块
tables              PyMuPDF4LLM Markdown 表格行
warnings            结构解析告警
parser              解析器信息
```

## 4. 当前示例文件规模

该示例文件当前解析结果统计：

```text
texts:    488
tables:   20
warnings: 35
```

结构树顶层有 2 个部分：

```text
ROOT
├── 第一部分 专用条款
└── 第二部分 通用条款
```

对应节点信息：

```text
第一部分 专用条款  source_ref=#/pages/3/lines/0   page_no=4   children=13  content=2
第二部分 通用条款  source_ref=#/pages/28/lines/0  page_no=29  children=9   content=0
```

注意：`source_ref` 中的 `#/pages/3` 是内部 chunk 下标，不应当直接当成人类页码。对外展示页码应使用节点的 `page_no`。

## 5. contract_structure 节点字段

`contract_structure` 是一棵树。每个节点结构类似：

```json
{
  "node_id": "node_0001",
  "parent_id": "root",
  "label": "第一部分",
  "title": "专用条款",
  "kind": "part",
  "rank": 0,
  "path": [],
  "source": "literal",
  "raw_text": "第一部分专用条款",
  "source_ref": "#/pages/3/lines/0",
  "page_no": 4,
  "line_index": 0,
  "tree_depth": 1,
  "content": [],
  "tables": [],
  "warnings": [],
  "children": []
}
```

主要字段说明：

```text
node_id      当前结构节点 ID
parent_id    父节点 ID
label        编号，例如 第一部分、一、、1、1.1、附件一
title        标题文本
kind         编号类型，例如 part、chinese、arabic、dotted、attachment
rank         层级权重，数值越小层级越高
path         阿拉伯数字编号路径，例如 1.2 会是 [1, 2]
source       编号来源，PDF 路径通常是 literal
raw_text     结构解析前的清洗后文本
source_ref   对应 PyMuPDF4LLM 页面行，例如 #/pages/4/lines/6
page_no      PDF 页码，推荐对外展示使用这个字段
line_index   页内行序号
tree_depth   结构树深度
content      当前节点直属正文
tables       当前节点下挂载的 Markdown 表格行
warnings     当前节点的解析告警
children     子章节节点
```

## 6. 当前示例文件的结构样例

`第一部分 专用条款` 下的直接子节点包括：

```text
一、工程概况
二、货物清单
三、货物供应
四、货物质量
五、货物验收
六、货物结算
七、货物付款
八、通知与送达
九、合同生效
附件一 授权委托书
附件二 项目部合规权限告知书
附件三 安全管理协议书
附件四 廉洁从业共建协议
```

`第二部分 通用条款` 下的直接子节点包括：

```text
一、货物合同附随义务
二、货物违约责任
三、货物缺陷索赔
四、合同变更
五、合同解除
六、不可抗力
七、争议解决
八、保密义务
九、其他条款
```

### 6.1 第一部分节点

```json
{
  "node_id": "node_0001",
  "parent_id": "root",
  "label": "第一部分",
  "title": "专用条款",
  "kind": "part",
  "rank": 0,
  "source_ref": "#/pages/3/lines/0",
  "page_no": 4
}
```

对应的 `texts` 条目是：

```json
{
  "self_ref": "#/texts/8",
  "label": "section_header",
  "text": "第一部分专用条款",
  "prov": [
    {
      "page_no": 4,
      "line_index": 0,
      "source_ref": "#/pages/3/lines/0"
    }
  ],
  "contract_numbering": {
    "kind": "part",
    "label": "第一部分",
    "title": "专用条款",
    "rank": 0,
    "path": [],
    "source": "literal"
  }
}
```

### 6.2 一、工程概况

```json
{
  "label": "一、",
  "title": "工程概况",
  "kind": "chinese",
  "rank": 10,
  "source_ref": "#/pages/3/lines/3",
  "page_no": 4
}
```

其子节点中，当前示例存在一个合并后的行：

```json
{
  "label": "1、",
  "title": "工程名称: ; 2、工程地点: ;",
  "kind": "arabic",
  "rank": 20,
  "path": [1],
  "source_ref": "#/pages/3/lines/4",
  "page_no": 4
}
```

这表示 PyMuPDF4LLM 将 `1、工程名称` 和 `2、工程地点` 抽在同一行里，结构解析器按行首 `1、` 建立节点，后面的 `2、工程地点` 被保留在该节点标题中。调用方需要知道这是 PDF 行抽取带来的表现。

### 6.3 1.1 子条款

```json
{
  "node_id": "node_0012",
  "parent_id": "node_0011",
  "label": "1.1",
  "title": "送货卸车: 乙方送货至甲方指定地点;合同综合单价已含卸车费用, 卸车工作由乙方负责,若由甲方负责卸车,发生的相应费用结算款中扣除。",
  "kind": "dotted",
  "rank": 21,
  "path": [1, 1],
  "source": "literal",
  "raw_text": "1.1 送货卸车: 乙方送货至甲方指定地点;合同综合单价已含卸车费用, 卸车工作由乙方负责,若由甲方负责卸车,发生的相应费用结算款中扣除。",
  "source_ref": "#/pages/4/lines/6",
  "page_no": 5,
  "line_index": 6,
  "tree_depth": 4
}
```

## 7. source_ref 与 texts 的关系

这是这份 PyMuPDF4LLM JSON 最容易用错的地方。

结构节点中的 `source_ref`：

```text
#/pages/3/lines/0
```

不是 `texts[*].self_ref`：

```text
#/texts/8
```

而是 `texts[*].prov[0].source_ref`。

所以调用方要按 `prov.source_ref` 建索引：

```python
texts_by_source_ref = {}

for item in document.get("texts", []):
    for prov in item.get("prov", []):
        source_ref = prov.get("source_ref")
        if source_ref:
            texts_by_source_ref[source_ref] = item
```

然后才能这样回查：

```python
node = document["contract_structure"]["children"][0]
source_ref = node["source_ref"]
text_item = texts_by_source_ref[source_ref]

print(text_item["self_ref"])
print(text_item["text"])
```

如果你只按 `self_ref` 建索引，会找不到结构节点引用的原始文本。

## 8. Python 调用示例

### 8.1 读取 document.json

```python
import json
from pathlib import Path


document_path = Path(
    "homepage/storage/parsing/"
    "5cb3c675-5968-4917-93bf-6dd592f26817/document.json"
)

with document_path.open("r", encoding="utf-8") as file:
    document = json.load(file)

contract_structure = document["contract_structure"]
texts = document.get("texts", [])
tables = document.get("tables", [])
warnings = document.get("warnings", [])
```

### 8.2 判断解析器类型

```python
schema_name = document.get("schema_name")
parser_name = (document.get("parser") or {}).get("name")

if schema_name == "PyMuPDF4LLMContractDocument":
    print("这是 PyMuPDF4LLM PDF 合同解析结果")

if parser_name == "pymupdf4llm-contract-parser":
    print("可以直接读取 contract_structure")
```

### 8.3 建立 source_ref 索引

```python
def build_text_index_by_source_ref(document: dict) -> dict[str, dict]:
    index = {}

    for item in document.get("texts", []):
        for prov in item.get("prov", []):
            if not isinstance(prov, dict):
                continue
            source_ref = prov.get("source_ref")
            if source_ref:
                index[source_ref] = item

    return index


texts_by_source_ref = build_text_index_by_source_ref(document)
```

### 8.4 遍历章节树

```python
def walk(node: dict, depth: int = 0):
    label = node.get("label") or ""
    title = node.get("title") or ""
    kind = node.get("kind") or ""
    page_no = node.get("page_no")
    source_ref = node.get("source_ref") or ""

    if node.get("node_id") != "root":
        indent = "  " * depth
        print(f"{indent}{label} {title} [{kind}] page={page_no} ref={source_ref}")

    for child in node.get("children", []):
        walk(child, depth + 1)


walk(contract_structure)
```

输出形态类似：

```text
  第一部分 专用条款 [part] page=4 ref=#/pages/3/lines/0
    一、 工程概况 [chinese] page=4 ref=#/pages/3/lines/3
      1、 工程名称: ; 2、工程地点: ; [arabic] page=4 ref=#/pages/3/lines/4
    二、 货物清单 [chinese] page=4 ref=#/pages/3/lines/5
  第二部分 通用条款 [part] page=29 ref=#/pages/28/lines/0
```

### 8.5 回查节点原文

```python
node = contract_structure["children"][0]
source_ref = node["source_ref"]
text_item = texts_by_source_ref[source_ref]

print("node:", node["label"], node["title"])
print("text self_ref:", text_item["self_ref"])
print("text:", text_item["text"])
print("page_no:", text_item["prov"][0]["page_no"])
print("line_index:", text_item["prov"][0]["line_index"])
```

### 8.6 获取当前节点直属正文

`content` 是当前节点直属正文，不自动包含子章节内容。

```python
def get_direct_content_text(node: dict) -> list[str]:
    return [
        item.get("text", "")
        for item in node.get("content", [])
        if item.get("text")
    ]


part = contract_structure["children"][0]
direct_texts = get_direct_content_text(part)
```

### 8.7 获取某个节点及其子节点全部正文

```python
def collect_all_content_text(node: dict) -> list[str]:
    result = []

    for item in node.get("content", []):
        text = item.get("text")
        if text:
            result.append(text)

    for child in node.get("children", []):
        result.extend(collect_all_content_text(child))

    return result


part = contract_structure["children"][0]
all_texts = collect_all_content_text(part)
```

### 8.8 拉平成章节列表

适用于前端目录、检索索引、模型输入。

```python
def flatten_outline(node: dict, parent_path: list[str] | None = None) -> list[dict]:
    parent_path = parent_path or []
    rows = []

    label = node.get("label") or ""
    title = node.get("title") or ""
    current_name = f"{label} {title}".strip()

    if node.get("node_id") != "root":
        current_path = parent_path + [current_name]
        rows.append(
            {
                "node_id": node.get("node_id"),
                "parent_id": node.get("parent_id"),
                "label": label,
                "title": title,
                "kind": node.get("kind"),
                "rank": node.get("rank"),
                "page_no": node.get("page_no"),
                "line_index": node.get("line_index"),
                "tree_depth": node.get("tree_depth"),
                "source_ref": node.get("source_ref"),
                "path_text": " / ".join(current_path),
                "content_text": "\n".join(collect_all_content_text(node)),
            }
        )
    else:
        current_path = parent_path

    for child in node.get("children", []):
        rows.extend(flatten_outline(child, current_path))

    return rows


outline_rows = flatten_outline(contract_structure)
```

### 8.9 根据页码过滤章节

```python
def find_nodes_on_page(node: dict, page_no: int) -> list[dict]:
    matched = []

    if node.get("page_no") == page_no:
        matched.append(node)

    for child in node.get("children", []):
        matched.extend(find_nodes_on_page(child, page_no))

    return matched


page4_nodes = find_nodes_on_page(contract_structure, 4)
```

### 8.10 读取表格

这份 PyMuPDF4LLM 产物中的 `tables` 是 Markdown 表格行，不是 Docling 那种结构化单元格网格。

顶层表格条目示例：

```json
{
  "self_ref": "#/tables/0",
  "page_no": 20,
  "line_index": 0,
  "text": "|38||协商维修方案|对存在的质量问题有权与建设单位协商维修方<br>案。|",
  "source": "pymupdf4llm"
}
```

读取方式：

```python
for table_line in document.get("tables", []):
    print(table_line["self_ref"])
    print(table_line["page_no"], table_line["line_index"])
    print(table_line["text"])
```

当前示例部分表格摘要：

```text
#/tables/0 page=20 line=0 |38||协商维修方案|...|
#/tables/1 page=20 line=1 |---|---|---|---|
#/tables/2 page=20 line=2 |39||组织维修|...|
#/tables/3 page=20 line=3 |40||维修验收|...|
```

当前示例中，结构节点 `附件二 项目部合规权限告知书` 挂载了 20 条表格线：

```json
{
  "node_id": "node_0076",
  "label": "附件二",
  "title": "项目部合规权限告知书",
  "kind": "attachment",
  "source_ref": "#/pages/15/lines/0",
  "page_no": 16,
  "tables": [
    {
      "source_ref": "#/pages/19/lines/0",
      "page_no": 20,
      "line_index": 0,
      "text": "|38||协商维修方案|对存在的质量问题有权与建设单位协商维修方<br>案。|",
      "source": "pymupdf4llm"
    }
  ]
}
```

### 8.11 检查解析告警

```python
for warning in document.get("warnings", []):
    print(warning.get("node_id"), warning.get("source_ref"), warning.get("message"))
```

当前示例常见告警：

```text
同级编号不连续
dotted 编号缺少显式父节点
疑似分页重复标题，已合并
```

例如：

```json
{
  "node_id": "node_0016",
  "source_ref": "#/pages/4/lines/11",
  "message": "同级编号不连续：3 后出现 5"
}
```

```json
{
  "node_id": "node_0017",
  "source_ref": "#/pages/5/lines/1",
  "message": "dotted 编号缺少显式父节点"
}
```

告警不代表节点不可用，只表示结构存在不连续、缺父级或重复标题合并等情况。调用方可以展示或记录这些告警，用于人工复核。

## 9. JavaScript 调用示例

```javascript
function buildTextIndexBySourceRef(documentJson) {
  const index = new Map();

  for (const item of documentJson.texts || []) {
    for (const prov of item.prov || []) {
      if (prov && prov.source_ref) {
        index.set(prov.source_ref, item);
      }
    }
  }

  return index;
}

function walk(node, depth = 0) {
  const label = node.label || "";
  const title = node.title || "";
  const kind = node.kind || "";
  const pageNo = node.page_no ?? "";
  const sourceRef = node.source_ref || "";

  if (node.node_id !== "root") {
    console.log(
      `${"  ".repeat(depth)}${label} ${title} [${kind}] page=${pageNo} ref=${sourceRef}`
    );
  }

  for (const child of node.children || []) {
    walk(child, depth + 1);
  }
}

function collectAllContentText(node) {
  const result = [];

  for (const item of node.content || []) {
    if (item.text) {
      result.push(item.text);
    }
  }

  for (const child of node.children || []) {
    result.push(...collectAllContentText(child));
  }

  return result;
}

const contractStructure = documentJson.contract_structure;
const textsBySourceRef = buildTextIndexBySourceRef(documentJson);

walk(contractStructure);
```

## 10. 结构编号识别规则

当前结构解析器支持以下编号类型：

| 编号类型 | 示例 | kind | rank |
| --- | --- | --- | ---: |
| 部分 | 第一部分、第二部分 | part | 0 |
| 章 | 第一章、第二章 | chapter | 0 |
| 附件边界 | 附件一： | attachment | 5 |
| 中文章节、条 | 一、；第一条 | chinese / article | 10 |
| 无内部点的阿拉伯数字 | 1、；1. | arabic | 20 |
| 一个内部点 | 1.1 | dotted | 21 |
| 两个内部点 | 1.1.1 | dotted | 22 |
| 三个内部点 | 1.1.1.1 | dotted | 23 |
| 括号序号 | （1）、（一） | parenthesized | 40 |

`rank` 越小，结构层级越高。组树时，如果新节点 `rank` 小于或等于当前栈顶节点，会向上回退后再挂载。

## 11. PyMuPDF4LLM 调用注意事项

### 11.1 source_ref 不是 texts.self_ref

PyMuPDF4LLM 路径中：

```text
contract_structure.source_ref = #/pages/{chunk_index}/lines/{line_index}
texts[*].self_ref             = #/texts/{index}
texts[*].prov[0].source_ref   = #/pages/{chunk_index}/lines/{line_index}
```

所以回查原文必须优先使用 `texts[*].prov[0].source_ref`。

### 11.2 page_no 才是展示页码

`#/pages/3/lines/0` 中的 `3` 是内部 chunk 下标。展示给用户时应使用：

```text
node.page_no
texts[*].prov[0].page_no
tables[*].page_no
```

### 11.3 表格是 Markdown 行

`tables` 中的每条记录是一个 Markdown 表格行。它适合做文本消费，但不是结构化单元格表格。如果需要单元格级处理，需要再对 Markdown 行做解析。

### 11.4 PDF 行抽取可能合并多个编号

例如当前示例中：

```text
1、工程名称: ; 2、工程地点: ;
```

被作为一行处理，结构解析器按第一个编号 `1、` 建立节点。调用方如果需要更细粒度的条款拆分，需要在业务层针对这种文本做进一步切分。

## 12. 调用建议

推荐调用顺序：

```text
1. 读取 document.json
2. 检查 schema_name 是否为 PyMuPDF4LLMContractDocument
3. 读取 contract_structure
4. 用 texts[*].prov[0].source_ref 建立文本索引
5. 遍历 contract_structure.children 构建目录或业务结构
6. 用 source_ref 回查原始文本、页码和行号
7. 按需读取 tables 和 warnings
```

不推荐：

```text
1. 不要用 texts[*].self_ref 去匹配结构节点 source_ref
2. 不要把 #/pages/3 当作 PDF 第 3 页
3. 不要假设 tables 是单元格网格
4. 不要从 texts 重新猜章节层级
5. 不要忽略 warnings
```

## 13. 当前实现关键代码摘录

以下代码直接摘自当前项目，便于调用方理解 PyMuPDF4LLM PDF `document.json` 是如何生成的。

### 13.1 PyMuPDF4LLM PDF 解析入口

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def parse_pymupdf4llm_pdf_to_json_data(
    pdf_path: Path,
    doc_id: str | None = None,
) -> dict[str, Any]:
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise RuntimeError(
            "pymupdf4llm is not installed. Install it before using "
            "PDF_PARSER_ENGINE=pymupdf4llm."
        ) from exc

    chunks = call_pymupdf4llm_to_markdown(pymupdf4llm, pdf_path)
    lines = standard_lines_from_pymupdf4llm_chunks(chunks)
    contract_structure, warnings = parse_contract_structure_from_lines(lines)

    return {
        "schema_name": PYMUPDF4LLM_SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "name": doc_id or pdf_path.stem,
        "origin": {
            "filename": pdf_path.name,
            "mimetype": "application/pdf",
        },
        "parser": {
            "name": "pymupdf4llm-contract-parser",
            "pymupdf4llm": getattr(pymupdf4llm, "__version__", None),
        },
        "texts": build_text_items_from_standard_lines(lines),
        "tables": build_table_items_from_standard_lines(lines),
        "contract_structure": contract_structure,
        "warnings": warnings,
    }
```

### 13.2 调用 PyMuPDF4LLM 转 Markdown

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def call_pymupdf4llm_to_markdown(module: Any, pdf_path: Path) -> Any:
    options = {
        "page_chunks": True,
        "header": False,
        "footer": False,
        "page_separators": False,
        "ignore_code": True,
    }
    try:
        return module.to_markdown(str(pdf_path), **options)
    except TypeError:
        fallback_options = {
            "page_chunks": True,
            "page_separators": False,
        }
        return module.to_markdown(str(pdf_path), **fallback_options)
```

### 13.3 从 PyMuPDF4LLM chunks 构造标准行

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def standard_lines_from_pymupdf4llm_chunks(chunks: Any) -> list[StandardLine]:
    if isinstance(chunks, str):
        return standard_lines_from_markdown(chunks, page_no=None, source="pymupdf4llm")

    if not isinstance(chunks, list):
        return []

    lines: list[StandardLine] = []
    for chunk_index, chunk in enumerate(chunks):
        if isinstance(chunk, str):
            page_no = chunk_index + 1
            lines.extend(
                standard_lines_from_markdown(
                    chunk,
                    page_no=page_no,
                    source="pymupdf4llm",
                    source_ref_prefix=f"#/pages/{chunk_index}/lines",
                )
            )
            continue

        if not isinstance(chunk, dict):
            continue

        page_no = extract_pymupdf4llm_page_no(chunk, chunk_index)
        text_parts = list(iter_pymupdf4llm_text_parts(chunk))
        page_text = "\n".join(text_parts) if text_parts else str(chunk.get("text") or "")
        lines.extend(
            standard_lines_from_markdown(
                page_text,
                page_no=page_no,
                source="pymupdf4llm",
                source_ref_prefix=f"#/pages/{chunk_index}/lines",
            )
        )

    return lines
```

### 13.4 过滤 PyMuPDF4LLM 页面块

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def iter_pymupdf4llm_text_parts(chunk: dict[str, Any]):
    text = str(chunk.get("text") or "")
    boxes = chunk.get("page_boxes")
    if not isinstance(boxes, list):
        yield text
        return

    for box in boxes:
        if not isinstance(box, dict):
            continue
        if box.get("class") in {"table", "picture", "page-header", "page-footer"}:
            continue
        start, stop = box.get("pos", (0, len(text)))
        yield text[start:stop]
```

```python
def extract_pymupdf4llm_page_no(chunk: dict[str, Any], fallback_index: int) -> int:
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    page_no = metadata.get("page_number")
    if isinstance(page_no, int):
        return page_no
    page_no = chunk.get("page")
    if isinstance(page_no, int):
        return page_no + 1
    return fallback_index + 1
```

### 13.5 Markdown 行标准化

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def standard_lines_from_markdown(
    markdown: str,
    *,
    page_no: int | None,
    source: str,
    source_ref_prefix: str = "#/lines",
) -> list[StandardLine]:
    raw_lines = [line for line in markdown.splitlines()]
    cleaned_lines = [clean_contract_line(line) for line in raw_lines]
    nonempty_indexes = [index for index, line in enumerate(cleaned_lines) if line]
    line_count = len(nonempty_indexes)
    lines: list[StandardLine] = []

    for output_index, raw_index in enumerate(nonempty_indexes):
        raw = raw_lines[raw_index]
        text = cleaned_lines[raw_index]
        block_type = "table" if is_markdown_table_line(raw) else "text"
        if raw.strip().startswith("#"):
            block_type = "heading"
        lines.append(
            StandardLine(
                text=text,
                source_ref=f"{source_ref_prefix}/{output_index}",
                page_no=page_no,
                line_index=output_index,
                line_count=line_count,
                block_type=block_type,
                source=source,
            )
        )

    return lines
```

### 13.6 texts 构造逻辑

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def build_text_items_from_standard_lines(lines: list[StandardLine]) -> list[dict[str, Any]]:
    text_items = []
    for index, line in enumerate(lines):
        if line.block_type == "table":
            continue
        token = parse_number_token(line.text)
        item: dict[str, Any] = {
            "self_ref": f"#/texts/{len(text_items)}",
            "parent": {"$ref": "#/body"},
            "label": "section_header" if token else "text",
            "content_layer": "body",
            "text": line.text,
            "prov": [
                {
                    "page_no": line.page_no,
                    "line_index": line.line_index,
                    "source_ref": line.source_ref,
                }
            ],
            "pdf": {
                "parser": line.source,
                "block_type": line.block_type,
            },
        }
        if token is not None:
            item["contract_numbering"] = {
                "kind": token.kind,
                "label": token.raw_label,
                "title": token.title,
                "rank": token.rank,
                "path": list(token.path),
                "source": token.source,
            }
        text_items.append(item)
    return text_items
```

### 13.7 tables 构造逻辑

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def build_table_items_from_standard_lines(lines: list[StandardLine]) -> list[dict[str, Any]]:
    tables = []
    for line in lines:
        if line.block_type != "table":
            continue
        tables.append(
            {
                "self_ref": f"#/tables/{len(tables)}",
                "page_no": line.page_no,
                "line_index": line.line_index,
                "text": line.text,
                "source": line.source,
            }
        )
    return tables
```

### 13.8 共用结构树解析入口

来源：

```text
homepage/app/services/contract_structure_parser.py
```

代码：

```python
def parse_contract_structure_from_lines(
    lines: list[StandardLine],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = ClauseNode(
        node_id="root",
        parent_id=None,
        label="",
        title="ROOT",
        kind="root",
        rank=-1,
    )
    stack = [root]
    warnings: list[dict[str, Any]] = []
    node_index = 0
    started = False

    for line_position, line in enumerate(lines):
        text = clean_contract_line(line.text)
        if not text:
            continue

        if should_skip_heading_parse(line):
            if started and is_table_line(line):
                stack[-1].tables.append(line_to_table_payload(line))
            continue

        if is_page_number_line(text, line.line_index, line.line_count):
            continue

        if is_toc_line(text):
            continue

        token = parse_number_token(text)
        if (
            token is not None
            and token.kind == "chapter"
            and line.source == "docling"
            and line.block_type != "heading"
        ):
            token = None
        if token is not None and is_attachment_list_line(lines, line, line_position):
            token = None

        if not started:
            if token is not None and token.kind in {"part", "chapter", "attachment"}:
                started = True
            else:
                continue

        if token is None:
            append_content(stack[-1], line, text)
            continue

        node_index += 1
        node = attach_node(
            stack,
            token,
            raw_text=text,
            node_id=f"node_{node_index:04d}",
            source_ref=line.source_ref,
        )
        node.page_no = line.page_no
        node.line_index = line.line_index
        node.bbox = line.bbox
        add_continuity_warning(node)
        append_node_warnings(warnings, node)

    return serialize_node(root), warnings
```

### 13.9 编号识别逻辑

来源：

```text
homepage/app/services/contract_structure_parser.py
```

代码：

```python
def parse_number_token(
    text: str,
    auto_label: str | None = None,
    outline_level: int | None = None,
) -> NumberToken | None:
    original_text = normalize_space(text)

    if auto_label:
        literal_token = parse_number_token(original_text, outline_level=outline_level)
        auto_token = parse_number_token(
            f"{auto_label}{original_text}",
            outline_level=outline_level,
        )
        if literal_token is not None:
            literal_token.auto_label = auto_label
            literal_token.literal_label = literal_token.raw_label
            literal_token.warnings.append("自动编号与文本编号同时存在")
            return literal_token
        if auto_token is not None:
            auto_token.title = original_text
            auto_token.source = "auto"
            auto_token.auto_label = auto_label
        return auto_token

    normalized = clean_contract_line(original_text)
    normalized = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", normalized)

    match = re.match(rf"^(第[{CN}0-9]+部分)\s*(.*)$", normalized)
    if match:
        return NumberToken("part", match.group(1), match.group(2).strip(), 0)

    match = re.match(rf"^(第[{CN}0-9]+章)\s*[:：]?\s*(.*)$", normalized)
    if match:
        return NumberToken("chapter", match.group(1), match.group(2).strip(), 0)

    match = re.match(rf"^(附件[{CN}0-9]+)\s*[:：]?\s*(.*)$", normalized)
    if match:
        return NumberToken("attachment", match.group(1), match.group(2).strip(), 5)

    match = re.match(rf"^(第[{CN}0-9]+条)\s*(.*)$", normalized)
    if match:
        return NumberToken("article", match.group(1), match.group(2).strip(), 10)

    match = re.match(rf"^([{CN}]+)、\s*(.*)$", normalized)
    if match:
        return NumberToken("chinese", match.group(1) + "、", match.group(2).strip(), 10)

    match = re.match(r"^(\d+(?:\.\d+)+)\.?\s*(.*)$", normalized)
    if match:
        path = tuple(int(value) for value in match.group(1).split("."))
        if is_likely_date_path(path):
            return None
        internal_dot_count = len(path) - 1
        return NumberToken(
            "dotted",
            match.group(1),
            match.group(2).strip(),
            20 + internal_dot_count,
            path,
        )

    match = re.match(r"^(\d+)([、.])\s*(?!\d)(.*)$", normalized)
    if match:
        value = int(match.group(1))
        if value > 999:
            return None
        return NumberToken(
            "arabic",
            match.group(1) + match.group(2),
            match.group(3).strip(),
            20,
            (value,),
        )

    match = re.match(rf"^([（(]\s*([{CN}0-9]+)\s*[）)])\s*(.*)$", normalized)
    if match:
        inner = match.group(2)
        path = (int(inner),) if inner.isdigit() else ()
        return NumberToken(
            "parenthesized",
            match.group(1),
            match.group(3).strip(),
            40,
            path,
        )

    return None
```

### 13.10 结构节点序列化逻辑

来源：

```text
homepage/app/services/contract_structure_parser.py
```

代码：

```python
def serialize_node(node: ClauseNode, depth: int = 0) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "parent_id": node.parent_id,
        "label": node.label,
        "title": node.title,
        "kind": node.kind,
        "rank": node.rank,
        "path": list(node.path),
        "source": node.source,
        "raw_text": node.raw_text,
        "source_ref": node.source_ref,
        "auto_label": node.auto_label,
        "literal_label": node.literal_label,
        "num_id": node.num_id,
        "ilvl": node.ilvl,
        "outline_level": node.outline_level,
        "paragraph_index": node.paragraph_index,
        "page_no": node.page_no,
        "line_index": node.line_index,
        "bbox": list(node.bbox) if node.bbox else None,
        "tree_depth": depth,
        "content": node.content,
        "tables": node.tables,
        "warnings": node.warnings,
        "children": [serialize_node(child, depth + 1) for child in node.children],
    }
```
