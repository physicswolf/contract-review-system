# homepage 文档结构 JSON 调用说明

本文面向调用 `homepage/storage/parsing/{file_id}/document.json` 的使用者，说明如何从解析结果中获取结构化合同内容。

示例文件：

```text
homepage/storage/parsing/a04412f8-8d91-4e29-859c-5014da5a73ae/document.json
```

## 1. 结论

结构化文档结果已经写入 `document.json` 顶层字段：

```text
contract_structure
```

调用方应优先读取：

```python
document["contract_structure"]
```

不要重新从 `texts` 中猜章节层级。`texts` 主要用于回查原始段落，`contract_structure` 才是已经整理好的章节树。

## 2. 当前示例文件的解析类型

该示例文件的关键元信息如下：

```json
{
  "schema_name": "PythonDocxContractDocument",
  "parser": {
    "name": "python-docx-contract-parser",
    "python_docx": "1.2.0"
  },
  "origin": {
    "filename": "a04412f8-8d91-4e29-859c-5014da5a73ae.docx",
    "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  }
}
```

这表示该 JSON 是由 `python-docx-contract-parser` 直接读取 DOCX 后生成的，不是 Docling PDF JSON。

## 3. 顶层 JSON 字段

常用顶层字段：

```text
schema_name          解析产物类型
version              解析产物版本
name                 文档 ID 或文件名
origin               原始文件信息
parser               解析器信息
texts                原始段落列表
tables               表格列表
contract_structure   结构化章节树
warnings             解析告警
```

调用方通常只需要：

```text
contract_structure   用于展示或消费章节树
texts                用 source_ref 回查原文
tables               获取表格内容
warnings             检查结构解析质量
```

## 4. contract_structure 节点字段

`contract_structure` 是一棵树。每个节点结构类似：

```json
{
  "node_id": "node_0002",
  "parent_id": "node_0001",
  "label": "一、",
  "title": "工程概况",
  "kind": "chinese",
  "rank": 10,
  "path": [],
  "source": "auto",
  "raw_text": "工程概况",
  "source_ref": "#/texts/13",
  "auto_label": "一、",
  "literal_label": null,
  "num_id": 3,
  "ilvl": 0,
  "outline_level": 0,
  "paragraph_index": 12,
  "tree_depth": 2,
  "content": [],
  "tables": [],
  "warnings": [],
  "children": []
}
```

主要字段说明：

```text
node_id         当前结构节点 ID
parent_id       父节点 ID
label           编号，例如 第一部分、一、、1、
title           标题文本
kind            编号类型，例如 part、chapter、attachment、chinese、arabic
rank            层级权重，数值越小层级越高
path            阿拉伯数字编号路径，例如 1.2.3 会是 [1, 2, 3]
source          编号来源，literal 表示正文显式编号，auto 表示 Word 自动编号
raw_text        原始段落文本
source_ref      对应 texts 中的原始段落位置
content         当前节点下的正文段落
tables          当前节点下的表格
warnings        当前节点的解析告警
children        子章节节点
```

## 5. 当前示例文件的实际结构

示例文件顶层结构：

```text
ROOT
├── 第一部分 专用条款
└── 第二部分 通用条款
```

`第一部分 专用条款` 下识别出的子结构包括：

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
附件一
附件二
附件三
```

示例：`#/texts/13` 的原始文本是：

```text
工程概况
```

但它在 DOCX 中有 Word 自动编号 `一、`，所以结构节点是：

```json
{
  "label": "一、",
  "title": "工程概况",
  "kind": "chinese",
  "rank": 10,
  "source": "auto",
  "source_ref": "#/texts/13"
}
```

示例：`#/texts/14` 的原始文本是：

```text
1、工程名称： ；
```

结构节点是：

```json
{
  "label": "1、",
  "title": "工程名称: ;",
  "kind": "arabic",
  "rank": 20,
  "source": "literal",
  "source_ref": "#/texts/14"
}
```

## 6. Python 调用示例

### 6.1 读取 document.json

```python
import json
from pathlib import Path


document_path = Path(
    "homepage/storage/parsing/"
    "a04412f8-8d91-4e29-859c-5014da5a73ae/document.json"
)

with document_path.open("r", encoding="utf-8") as file:
    document = json.load(file)

contract_structure = document["contract_structure"]
texts = document.get("texts", [])
tables = document.get("tables", [])
warnings = document.get("warnings", [])
```

### 6.2 判断解析器类型

```python
schema_name = document.get("schema_name")
parser_name = (document.get("parser") or {}).get("name")

if schema_name == "PythonDocxContractDocument":
    print("该文件由 python-docx 合同结构解析器生成")

if parser_name == "python-docx-contract-parser":
    print("可直接使用 contract_structure 读取 DOCX 章节树")
```

### 6.3 遍历章节树

```python
def walk(node: dict, depth: int = 0):
    label = node.get("label") or ""
    title = node.get("title") or ""
    kind = node.get("kind") or ""
    source_ref = node.get("source_ref") or ""

    if node.get("node_id") != "root":
        indent = "  " * depth
        print(f"{indent}{label}{title} [{kind}] {source_ref}")

    for child in node.get("children", []):
        walk(child, depth + 1)


walk(contract_structure)
```

输出形态类似：

```text
  第一部分专用条款 [part] #/texts/9
    一、工程概况 [chinese] #/texts/13
      1、工程名称: ; [arabic] #/texts/14
      2、工程地点: ; [arabic] #/texts/15
    二、货物清单 [chinese] #/texts/16
  第二部分通用条款 [part] #/texts/292
```

### 6.4 建立 source_ref 到原文的索引

```python
texts_by_ref = {
    item["self_ref"]: item
    for item in document.get("texts", [])
    if "self_ref" in item
}

node = contract_structure["children"][0]["children"][0]
source_ref = node["source_ref"]
raw_text = texts_by_ref[source_ref]["text"]

print(source_ref)
print(raw_text)
```

### 6.5 获取某个节点下的正文

`content` 只包含当前节点直属正文，不自动包含子章节内容。

```python
def get_direct_content_text(node: dict) -> list[str]:
    return [
        item.get("text", "")
        for item in node.get("content", [])
        if item.get("text")
    ]


node = contract_structure["children"][0]
texts = get_direct_content_text(node)

for text in texts:
    print(text)
```

如果要获取某个节点及其所有子节点的正文：

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


node = contract_structure["children"][0]
all_texts = collect_all_content_text(node)
```

### 6.6 拉平成章节列表

适用于前端目录、搜索索引或后续模型输入。

```python
def flatten_outline(node: dict, parent_path: list[str] | None = None) -> list[dict]:
    parent_path = parent_path or []
    rows = []

    label = node.get("label") or ""
    title = node.get("title") or ""
    current_name = f"{label}{title}".strip()

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

### 6.7 根据标题查找节点

```python
def find_nodes_by_title(node: dict, keyword: str) -> list[dict]:
    matched = []

    title = node.get("title") or ""
    label = node.get("label") or ""
    full_title = f"{label}{title}"

    if keyword in full_title:
        matched.append(node)

    for child in node.get("children", []):
        matched.extend(find_nodes_by_title(child, keyword))

    return matched


nodes = find_nodes_by_title(contract_structure, "工程概况")
```

### 6.8 读取表格

顶层 `tables` 保存全部表格。结构节点中的 `tables` 保存挂载到该章节下的表格引用或表格内容。

```python
for table in document.get("tables", []):
    print(table["self_ref"])
    print(table["row_count"], table["column_count"])

    for row in table["rows"]:
        print(row)
```

### 6.9 检查解析告警

```python
for warning in document.get("warnings", []):
    print(warning.get("node_id"), warning.get("source_ref"), warning.get("message"))
```

常见告警：

```text
自动编号与文本编号同时存在
dotted 编号缺少显式父节点
同级编号不连续
疑似分页重复标题，已合并
```

## 7. JavaScript 调用示例

前端或 Node.js 读取后，也应从 `contract_structure` 开始消费。

```javascript
function walk(node, depth = 0) {
  const label = node.label || "";
  const title = node.title || "";
  const kind = node.kind || "";
  const sourceRef = node.source_ref || "";

  if (node.node_id !== "root") {
    console.log(`${"  ".repeat(depth)}${label}${title} [${kind}] ${sourceRef}`);
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

## 8. 结构编号识别规则

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

## 9. texts 与 contract_structure 的关系

每个 `texts` 元素都有 `self_ref`：

```json
{
  "self_ref": "#/texts/13",
  "label": "section_header",
  "text": "工程概况",
  "docx": {
    "style": "Default",
    "outline_level": 0,
    "auto_label": "一、"
  },
  "contract_numbering": {
    "kind": "chinese",
    "label": "一、",
    "title": "工程概况",
    "rank": 10,
    "path": [],
    "source": "auto"
  }
}
```

对应的结构节点中会记录：

```json
{
  "label": "一、",
  "title": "工程概况",
  "source": "auto",
  "source_ref": "#/texts/13"
}
```

因此：

```text
contract_structure 用于结构化读取
source_ref          用于回查 texts 原始段落
texts               用于保留原文和解析元数据
```

## 10. 调用建议

推荐调用顺序：

```text
1. 读取 document.json
2. 检查 schema_name 和 parser.name
3. 读取 contract_structure
4. 遍历 children 构建目录或业务结构
5. 用 source_ref 回查 texts 原文
6. 按需读取 content、tables、warnings
```

不推荐：

```text
1. 不要只遍历 texts 来判断章节层级
2. 不要假设 text 中一定包含 Word 自动编号
3. 不要忽略 warnings
4. 不要把 label + title 当成唯一 ID，应使用 node_id 或 source_ref
```

## 11. 当前实现关键代码摘录

以下代码直接摘自当前项目，便于调用方理解 `document.json` 是如何生成的。

### 11.1 DOCX 解析入口

来源：

```text
homepage/app/services/python_docx_contract_parser.py
```

代码：

```python
def parse_docx_contract_to_json_data(docx_path: Path, doc_id: str | None = None) -> dict[str, Any]:
    doc = Document(str(docx_path))
    numbering = NumberingResolver(doc)
    root = ClauseNode(
        node_id="root",
        parent_id=None,
        label="",
        title="ROOT",
        kind="root",
        rank=-1,
    )
    stack = [root]
    texts: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    paragraph_index = -1
    node_index = 0

    blocks = list(iter_block_items(doc))
    for block_index, block in enumerate(blocks):
        if isinstance(block, Paragraph):
            paragraph_index += 1
            text = normalize_space(block.text)
            if not text:
                continue

            outline_level = get_outline_level(block)
            auto = numbering.next_label(block)
            token = parse_number_token(
                text,
                auto_label=auto["label"] if auto else None,
                outline_level=outline_level,
            )
            if token is not None and is_attachment_list_item(blocks, block_index):
                token = None
            text_item = build_docx_text_item(
                text,
                len(texts),
                paragraph_index,
                block,
                token,
                auto,
            )
            texts.append(text_item)

            if token is None:
                stack[-1].content.append(
                    {
                        "source_ref": text_item["self_ref"],
                        "paragraph_index": paragraph_index,
                        "text": text,
                    }
                )
                continue

            node_index += 1
            node = attach_node(
                stack,
                token,
                raw_text=text,
                node_id=f"node_{node_index:04d}",
                source_ref=text_item["self_ref"],
            )
            node.paragraph_index = paragraph_index
            node.outline_level = outline_level
            node.auto_label = token.auto_label
            node.literal_label = token.literal_label
            if auto:
                node.num_id = auto["num_id"]
                node.ilvl = auto["ilvl"]
            add_continuity_warning(node)
            append_node_warnings(warnings, node)
        elif isinstance(block, Table):
            table = table_to_payload(block, len(tables))
            tables.append(table)
            stack[-1].tables.append(table)

    return {
        "schema_name": SCHEMA_NAME,
        "version": SCHEMA_VERSION,
        "name": doc_id or docx_path.stem,
        "origin": {
            "filename": docx_path.name,
            "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        "parser": {
            "name": "python-docx-contract-parser",
            "python_docx": getattr(docx, "__version__", None),
        },
        "texts": texts,
        "tables": tables,
        "contract_structure": serialize_node(root),
        "warnings": warnings,
    }
```

### 11.2 text item 生成逻辑

来源：

```text
homepage/app/services/python_docx_contract_parser.py
```

代码：

```python
def build_docx_text_item(
    text: str,
    text_index: int,
    paragraph_index: int,
    paragraph: Paragraph,
    token: NumberToken | None,
    auto: dict[str, Any] | None,
) -> dict[str, Any]:
    label = "section_header" if token is not None else "text"
    item: dict[str, Any] = {
        "self_ref": f"#/texts/{text_index}",
        "parent": {"$ref": "#/body"},
        "label": label,
        "content_layer": "body",
        "text": text,
        "prov": [{"paragraph_index": paragraph_index}],
        "docx": {
            "style": paragraph.style.name if paragraph.style is not None else None,
            "outline_level": get_outline_level(paragraph),
            "auto_label": auto["label"] if auto else None,
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
    return item
```

### 11.3 编号识别逻辑

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

### 11.4 结构树挂载逻辑

来源：

```text
homepage/app/services/contract_structure_parser.py
```

代码：

```python
def attach_node(
    stack: list[ClauseNode],
    token: NumberToken,
    *,
    raw_text: str,
    node_id: str,
    source_ref: str,
) -> ClauseNode:
    while len(stack) > 1 and stack[-1].rank >= token.rank:
        stack.pop()

    parent = stack[-1]
    missing_dotted_parent = False

    if token.kind == "dotted" and token.path:
        expected_parent_path = token.path[:-1]
        found_parent_by_path = False

        for ancestor in reversed(stack):
            if expected_parent_path and ancestor.path == expected_parent_path:
                parent = ancestor
                found_parent_by_path = True
                break

            if ancestor.kind in {"part", "chapter", "attachment", "chinese", "article"}:
                break

        missing_dotted_parent = bool(expected_parent_path and not found_parent_by_path)

    if parent.children:
        last = parent.children[-1]
        if last.label == token.raw_label and last.title == token.title:
            last.warnings.append("疑似分页重复标题，已合并")
            return last

    node = ClauseNode(
        node_id=node_id,
        parent_id=parent.node_id,
        label=token.raw_label,
        title=token.title,
        kind=token.kind,
        rank=token.rank,
        path=token.path,
        source=token.source,
        raw_text=raw_text,
        source_ref=source_ref,
        auto_label=token.auto_label,
        literal_label=token.literal_label,
        warnings=list(token.warnings),
    )
    if missing_dotted_parent:
        node.warnings.append("dotted 编号缺少显式父节点")

    parent.children.append(node)
    setattr(node, "_parent_children", parent.children)
    stack.append(node)
    return node
```

### 11.5 结构节点序列化逻辑

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
