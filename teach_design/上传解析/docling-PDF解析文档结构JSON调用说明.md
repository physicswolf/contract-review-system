# homepage PDF 文档结构 JSON 调用说明

本文面向调用 `homepage/storage/parsing/{file_id}/document.json` 的使用者，说明如何从 PDF 解析结果中获取结构化合同内容。

示例原始文件：

```text
homepage/storage/uploads/2026/06/24/8d68b3ee-5392-435b-a26a-f10aab24ecfe.pdf
```

示例解析结果：

```text
homepage/storage/parsing/8d68b3ee-5392-435b-a26a-f10aab24ecfe/document.json
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

这份 PDF 的 `document.json` 保留了 Docling 原始 JSON 结构，同时额外补充了：

```text
contract_structure
warnings
contract_structure_parser
```

因此不要只看 `schema_name` 判断是否已有结构树，应检查是否存在 `contract_structure`。

## 2. 当前示例文件的解析类型

该示例文件的关键元信息如下：

```json
{
  "schema_name": "DoclingDocument",
  "version": "1.10.0",
  "name": "8d68b3ee-5392-435b-a26a-f10aab24ecfe",
  "origin": {
    "mimetype": "application/pdf",
    "filename": "8d68b3ee-5392-435b-a26a-f10aab24ecfe.pdf"
  },
  "contract_structure_parser": {
    "name": "contract-structure-parser",
    "source": "docling",
    "doc_id": "8d68b3ee-5392-435b-a26a-f10aab24ecfe",
    "source_file": "8d68b3ee-5392-435b-a26a-f10aab24ecfe.pdf"
  }
}
```

含义：

```text
schema_name = DoclingDocument
    说明主体 JSON 是 Docling 产物。

contract_structure_parser.source = docling
    说明 contract_structure 是项目在 Docling JSON 上补充生成的合同结构树。

parser 字段为空
    对这份 Docling JSON 是正常情况，调用方不应依赖 parser.name 判断结构能力。
```

## 3. 顶层 JSON 字段

这份 PDF `document.json` 的顶层字段包括：

```text
schema_name
version
name
origin
furniture
body
groups
texts
pictures
tables
key_value_items
form_items
pages
contract_structure
warnings
contract_structure_parser
```

调用方常用字段：

```text
contract_structure        结构化章节树，优先读取
texts                     Docling 抽取出的文本块，用 source_ref 回查原文
tables                    Docling 抽取出的表格
pages                     页面信息
warnings                  结构解析告警
contract_structure_parser 结构树生成器信息
```

## 4. 当前示例文件规模

该示例文件当前解析结果统计：

```text
texts:    539
tables:   9
warnings: 112
```

结构树顶层有 5 个章节：

```text
ROOT
├── 第一章 协议总则
├── 第二章 协议专用条款
├── 第三章 协议通用条款
├── 第四章 附件及附表
└── 第五章 技术附件
```

对应节点信息：

```text
第一章 协议总则      source_ref=#/texts/9    page_no=3   children=10
第二章 协议专用条款  source_ref=#/texts/118  page_no=6   children=8
第三章 协议通用条款  source_ref=#/texts/202  page_no=12  children=24
第四章 附件及附表    source_ref=#/texts/355  page_no=25  children=3
第五章 技术附件      source_ref=#/texts/438  page_no=37  children=10
```

## 5. contract_structure 节点字段

`contract_structure` 是一棵树。每个节点结构类似：

```json
{
  "node_id": "node_0001",
  "parent_id": "root",
  "label": "第一章",
  "title": "协议总则",
  "kind": "chapter",
  "rank": 0,
  "path": [],
  "source": "literal",
  "raw_text": "第一章协议总则",
  "source_ref": "#/texts/9",
  "page_no": 3,
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
label        编号，例如 第一章、第一条、1.1
title        标题文本
kind         编号类型，例如 chapter、article、dotted、attachment
rank         层级权重，数值越小层级越高
path         阿拉伯数字编号路径，例如 2.1 会是 [2, 1]
source       编号来源，PDF 通常是 literal
raw_text     结构解析前的清洗后文本
source_ref   对应 texts 中的原始文本块
page_no      所在 PDF 页码
line_index   所在页内的文本行序号
bbox         Docling 坐标框，存在时可用于页面定位
tree_depth   结构树深度
content      当前节点直属正文
tables       当前节点挂载表格；Docling PDF 路径下通常为空
warnings     当前节点的解析告警
children     子章节节点
```

## 6. 当前示例文件的结构样例

`第一章 协议总则` 下的直接子节点包括：

```text
第一条 组成协议的文件
第二条 供货货物概况
第三条 联系人
第四条 协议生效及其它
第五条 双方盖章
第一条 适用范围
第二条 供货范围
第三条 协议和价格有效期限
第四条 供货方式
第五条 收货单位及联系人
```

其中 `第一条 组成协议的文件` 对应：

```json
{
  "label": "第一条",
  "title": "组成协议的文件",
  "kind": "article",
  "rank": 10,
  "source_ref": "#/texts/13",
  "page_no": 3
}
```

其子节点 `1.1` 对应：

```json
{
  "node_id": "node_0003",
  "parent_id": "node_0002",
  "label": "1.1",
  "title": "本协议由以下文件组成, 为协议履行的依据,使本协议具有完整的法律效力:",
  "kind": "dotted",
  "rank": 21,
  "path": [1, 1],
  "source": "literal",
  "raw_text": "1.1 本协议由以下文件组成, 为协议履行的依据,使本协议具有完整的法律效力:",
  "source_ref": "#/texts/14",
  "page_no": 3,
  "line_index": 5,
  "tree_depth": 3,
  "warnings": ["dotted 编号缺少显式父节点"]
}
```

另一个典型样例是 `#/texts/29`。Docling 原始文本中存在 `2. 1` 的空格问题：

```json
{
  "self_ref": "#/texts/29",
  "label": "list_item",
  "text": "1 货物名称： 液位仪及测漏传感器，供货范围详见本协议附件一。",
  "orig": "2. 1 货物名称： 液位仪及测漏传感器，供货范围详见本协议附件一。"
}
```

结构解析会优先使用更有编号信息的 `orig`，并清洗为：

```json
{
  "label": "2.1",
  "title": "货物名称: 液位仪及测漏传感器,供货范围详见本协议附件一。",
  "kind": "dotted",
  "path": [2, 1],
  "source_ref": "#/texts/29"
}
```

## 7. texts 与 source_ref

`texts` 是 Docling 的文本块列表。每个文本块有 `self_ref`，结构节点通过 `source_ref` 指向它。

示例 `#/texts/9`：

```json
{
  "self_ref": "#/texts/9",
  "label": "section_header",
  "text": "第一章 协议总则",
  "orig": "第一章 协议总则",
  "content_layer": "body",
  "prov": [
    {
      "page_no": 3,
      "bbox": {
        "l": 266.67678600000005,
        "t": 768.2897300273439,
        "r": 355.67905800000005,
        "b": 759.9647000273438,
        "coord_origin": "BOTTOMLEFT"
      },
      "charspan": [0, 8]
    }
  ]
}
```

对应结构节点：

```json
{
  "label": "第一章",
  "title": "协议总则",
  "source_ref": "#/texts/9",
  "page_no": 3
}
```

因此：

```text
contract_structure 用于结构化读取
source_ref          用于回查 texts 原始文本块
texts.prov          用于获取 PDF 页码和坐标
```

## 8. Python 调用示例

### 8.1 读取 document.json

```python
import json
from pathlib import Path


document_path = Path(
    "homepage/storage/parsing/"
    "8d68b3ee-5392-435b-a26a-f10aab24ecfe/document.json"
)

with document_path.open("r", encoding="utf-8") as file:
    document = json.load(file)

contract_structure = document["contract_structure"]
texts = document.get("texts", [])
tables = document.get("tables", [])
warnings = document.get("warnings", [])
```

### 8.2 判断是否已有合同结构树

```python
if "contract_structure" not in document:
    raise ValueError("当前 document.json 没有结构化章节树")

structure_parser = document.get("contract_structure_parser") or {}

if structure_parser.get("source") == "docling":
    print("这是基于 Docling PDF JSON 补充生成的合同结构树")
```

不要这样判断：

```python
parser_name = (document.get("parser") or {}).get("name")

if parser_name == "docling":
    print("不推荐这样判断，因为这份 Docling JSON 没有 parser 字段")
```

### 8.3 遍历章节树

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
  第一章 协议总则 [chapter] page=3 ref=#/texts/9
    第一条 组成协议的文件 [article] page=3 ref=#/texts/13
      1.1 本协议由以下文件组成, 为协议履行的依据,使本协议具有完整的法律效力: [dotted] page=3 ref=#/texts/14
      1.2 当协议各组成部分的内容之间出现冲突、 矛盾、 歧义、 错误、 疏漏等情况时,按下列文件排列顺序进行解释: [dotted] page=3 ref=#/texts/21
  第二章 协议专用条款 [chapter] page=6 ref=#/texts/118
```

### 8.4 建立 source_ref 到 texts 的索引

```python
texts_by_ref = {
    item["self_ref"]: item
    for item in document.get("texts", [])
    if "self_ref" in item
}

node = contract_structure["children"][0]
source_ref = node["source_ref"]
text_item = texts_by_ref[source_ref]

print(text_item["text"])
print(text_item["prov"][0]["page_no"])
print(text_item["prov"][0]["bbox"])
```

### 8.5 获取当前节点直属正文

`content` 是当前节点直属正文，不自动包含子章节内容。

```python
def get_direct_content_text(node: dict) -> list[str]:
    return [
        item.get("text", "")
        for item in node.get("content", [])
        if item.get("text")
    ]


chapter = contract_structure["children"][0]
direct_texts = get_direct_content_text(chapter)
```

### 8.6 获取某个节点及其子节点全部正文

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


chapter = contract_structure["children"][0]
all_texts = collect_all_content_text(chapter)
```

### 8.7 拉平成章节列表

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

### 8.8 根据页码过滤章节

```python
def find_nodes_on_page(node: dict, page_no: int) -> list[dict]:
    matched = []

    if node.get("page_no") == page_no:
        matched.append(node)

    for child in node.get("children", []):
        matched.extend(find_nodes_on_page(child, page_no))

    return matched


page3_nodes = find_nodes_on_page(contract_structure, 3)
```

### 8.9 读取 PDF 表格

Docling PDF 路径下，表格主要保存在顶层 `tables` 中。当前示例中 `contract_structure` 节点里的 `tables` 数量为 0，因此表格归属章节需要调用方按页码或业务规则关联。

```python
for table in document.get("tables", []):
    table_ref = table.get("self_ref")
    prov = (table.get("prov") or [{}])[0]
    data = table.get("data") or {}

    print(table_ref)
    print("page_no:", prov.get("page_no"))
    print("rows:", data.get("num_rows"))
    print("cols:", data.get("num_cols"))

    for row in data.get("grid") or []:
        print([cell.get("text", "") for cell in row])
```

当前示例部分表格摘要：

```text
#/tables/0 page=27 rows=10 cols=9
#/tables/1 page=29 rows=3  cols=4
#/tables/2 page=30 rows=1  cols=2
#/tables/3 page=31 rows=10 cols=2
#/tables/4 page=33 rows=3  cols=2
```

### 8.10 检查解析告警

```python
for warning in document.get("warnings", []):
    print(warning.get("node_id"), warning.get("source_ref"), warning.get("message"))
```

当前示例常见告警：

```text
dotted 编号缺少显式父节点
```

例如：

```json
{
  "node_id": "node_0003",
  "source_ref": "#/texts/14",
  "message": "dotted 编号缺少显式父节点"
}
```

这个告警表示识别到了 `1.1`，但结构栈中没有显式的 `1` 父节点。调用方仍然可以使用该节点，只是需要知道它的父级是按当前章节上下文挂载出来的。

## 9. JavaScript 调用示例

```javascript
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

function buildTextIndex(documentJson) {
  const index = new Map();

  for (const item of documentJson.texts || []) {
    if (item.self_ref) {
      index.set(item.self_ref, item);
    }
  }

  return index;
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
const textsByRef = buildTextIndex(documentJson);

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

## 11. PDF 调用注意事项

### 11.1 Docling text 与 orig

Docling 文本块中可能同时存在：

```text
text  Docling 归一化后的文本
orig  Docling 原始识别文本
```

结构解析时会优先选择更能保留编号的文本。比如 `#/texts/29`：

```text
text = 1 货物名称...
orig = 2. 1 货物名称...
```

解析器会使用 `orig` 并清洗出 `2.1`。

### 11.2 页眉页脚

Docling 的 `label` 中包含 `page_footer`、`page_header`、`title`、`section_header` 等信息。结构解析会把 `header` 或 `title` 视为标题候选，把 `table` 视为表格，其他作为普通文本。

### 11.3 chapter 识别限制

PDF 正文里可能出现“第一章”这样的引用。为了降低误识别，Docling 路径下只有当文本块被 Docling 标记为标题时，`第一章` 才会作为 `chapter` 节点进入结构树。

### 11.4 表格归属

当前 Docling PDF 路径从 `texts` 构造 `contract_structure`，不会把顶层 `tables` 自动挂到章节节点上。调用方如果需要“章节 -> 表格”的关系，建议：

```text
1. 读取 table.prov[0].page_no
2. 找到 page_no 最近的章节节点
3. 按业务规则确认归属
```

## 12. 调用建议

推荐调用顺序：

```text
1. 读取 document.json
2. 检查是否存在 contract_structure
3. 检查 contract_structure_parser.source 是否为 docling
4. 遍历 contract_structure.children 构建目录或业务结构
5. 用 source_ref 回查 texts 原文、页码和 bbox
6. 按需读取 tables、pages、warnings
```

不推荐：

```text
1. 不要只依赖 schema_name 判断是否有结构树
2. 不要从 texts 重新猜章节层级
3. 不要假设 text 比 orig 更适合编号识别
4. 不要假设 contract_structure 节点的 tables 已经包含 Docling 顶层表格
5. 不要忽略 warnings，尤其是 dotted 编号缺少显式父节点
```

## 13. 当前实现关键代码摘录

以下代码直接摘自当前项目，便于调用方理解 PDF `document.json` 是如何补充出 `contract_structure` 的。

### 13.1 PDF 解析后补充结构树

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def add_contract_structure_to_docling_pdf_json_data(
    json_data: dict[str, Any],
    *,
    source_file: str | None = None,
    doc_id: str | None = None,
) -> dict[str, Any]:
    lines = standard_lines_from_docling_json_data(json_data)
    contract_structure, warnings = parse_contract_structure_from_lines(lines)
    enriched = dict(json_data)
    enriched["schema_name"] = (
        json_data.get("schema_name") or DOCLING_PDF_STRUCTURE_SCHEMA_NAME
    )
    enriched["contract_structure"] = contract_structure
    enriched["warnings"] = list(json_data.get("warnings") or []) + warnings
    enriched["contract_structure_parser"] = {
        "name": "contract-structure-parser",
        "source": "docling",
        "doc_id": doc_id,
        "source_file": source_file,
    }
    return enriched
```

### 13.2 从 Docling JSON 抽取结构解析行

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def standard_lines_from_docling_json_data(json_data: dict[str, Any]) -> list[StandardLine]:
    raw_lines: list[StandardLine] = []
    text_items = merge_docling_inline_text_items(json_data.get("texts") or [])
    for text_index, item in enumerate(text_items):
        if not isinstance(item, dict):
            continue

        text = clean_contract_line(docling_item_text(item))
        if not text:
            continue

        page_no = extract_docling_page_no(item)
        source_ref = item.get("self_ref") or f"#/texts/{text_index}"
        raw_lines.append(
            StandardLine(
                text=text,
                source_ref=source_ref,
                page_no=page_no,
                block_type=docling_block_type(item),
                source="docling",
                extra={"text_index": text_index},
            )
        )

    return with_page_line_counts(raw_lines)
```

### 13.3 text/orig 选择逻辑

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def docling_item_text(item: dict[str, Any]) -> str:
    text = str(item.get("text") or "")
    orig = str(item.get("orig") or "")
    if not orig.strip():
        return text

    orig_token = parse_number_token(orig)
    text_token = parse_number_token(text)
    if orig_token is not None and text_token is None:
        return orig

    if str(item.get("label") or "").lower() == "list_item":
        return orig

    return text
```

### 13.4 Docling 相邻文本块合并逻辑

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def merge_docling_inline_text_items(items: list[Any]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index = 0
    while index < len(items):
        item = items[index]
        if not isinstance(item, dict):
            index += 1
            continue

        current = dict(item)
        index += 1
        while index < len(items):
            next_item = items[index]
            if not isinstance(next_item, dict) or not should_merge_docling_items(
                current,
                next_item,
            ):
                break
            current = merge_docling_items(current, next_item)
            index += 1
        merged.append(current)
    return merged
```

```python
def should_merge_docling_items(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if docling_block_type(left) == "table" or docling_block_type(right) == "table":
        return False
    if extract_docling_page_no(left) != extract_docling_page_no(right):
        return False
    if parent_ref(left) != parent_ref(right):
        return False

    left_bbox = extract_docling_bbox(left)
    right_bbox = extract_docling_bbox(right)
    if left_bbox is None or right_bbox is None:
        return False

    left_center = (left_bbox[1] + left_bbox[3]) / 2
    right_center = (right_bbox[1] + right_bbox[3]) / 2
    max_height = max(abs(left_bbox[3] - left_bbox[1]), abs(right_bbox[3] - right_bbox[1]))
    horizontal_gap = right_bbox[0] - left_bbox[2]

    return abs(left_center - right_center) <= max_height * 0.5 and -2 <= horizontal_gap <= 4
```

```python
def merge_docling_items(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_text = docling_item_text(left)
    right_text = docling_item_text(right)
    left_bbox = extract_docling_bbox(left)
    right_bbox = extract_docling_bbox(right)
    horizontal_gap = right_bbox[0] - left_bbox[2] if left_bbox and right_bbox else 0

    merged = dict(left)
    merged_text = join_inline_text(left_text, right_text, horizontal_gap)
    merged["text"] = merged_text
    if left.get("orig") or right.get("orig"):
        merged["orig"] = merged_text

    if left_bbox and right_bbox and left.get("prov"):
        prov = [dict(left["prov"][0])]
        prov[0]["bbox"] = {
            "l": min(left_bbox[0], right_bbox[0]),
            "t": max(left_bbox[1], right_bbox[1]),
            "r": max(left_bbox[2], right_bbox[2]),
            "b": min(left_bbox[3], right_bbox[3]),
            "coord_origin": "BOTTOMLEFT",
        }
        merged["prov"] = prov
    return merged
```

### 13.5 Docling 文本块类型与页码提取

来源：

```text
homepage/app/services/pdf_contract_parser.py
```

代码：

```python
def docling_block_type(item: dict[str, Any]) -> str:
    label = str(item.get("label") or "").lower()
    if "header" in label or "title" in label:
        return "heading"
    if "table" in label:
        return "table"
    return "text"
```

```python
def extract_docling_page_no(item: dict[str, Any]) -> int | None:
    prov = item.get("prov") or []
    if not prov or not isinstance(prov[0], dict):
        return None
    page_no = prov[0].get("page_no")
    return page_no if isinstance(page_no, int) else None
```

### 13.6 共用结构树解析入口

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

### 13.7 编号识别逻辑

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

### 13.8 结构节点序列化逻辑

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
