# blocks.json 增加 rank 信息 + 原文改用 blocks 渲染设计说明书

**项目**：contract-review-system  
**日期**：2026-07-02  
**版本**：v1.0  
**对应计划书**：`docs/planning/blocks_rank与原文渲染计划书.md`

---

## 一、`block_builder.py` — blocks 增加 kind/rank

### 1.1 导入 `parse_number_token`

```python
from src.services.contract_structure_parser import parse_number_token
```

`parse_number_token` 在 `contract_structure_parser.py` 中定义，识别合同编号体系（第X章、第一条、1.1、（一）、一、等），返回 `NumberToken` 含 `kind` 和 `rank`。

### 1.2 DOCX 路径 — `_build_docx_blocks`

现有 `_extract_markdown_lines` 输出的每行文本已经是带编号的（如 `"第四条 项目交付与验收"`）。在生成 block 时调用 `parse_number_token`：

```python
def _build_docx_blocks(source_path, document):
    md_lines = _parse_markdown_lines(_extract_markdown_lines(source_path))
    total_pages, units = _load_document_units(document)
    flat_text = _build_flat_document(units)
    _locate_markdown_lines(md_lines, flat_text, units)

    blocks = []
    for line in md_lines:
        page, bbox = _build_bbox(_units_for_range(units, line.start, line.end))
        token = line.token  # 已有：_parse_markdown_lines 中已调用 parse_number_token
        blocks.append({
            "no": line.no,
            "page": page,
            "text": line.text,
            "kind": token.kind if token else None,
            "rank": token.rank if token else None,
            "bbox": bbox,
        })

    return {"total_pages": total_pages, "blocks": blocks}
```

> `_parse_markdown_lines` 中**已经在调用** `parse_number_token(text)`（line 121 的 `MarkdownLine` 构造），只需在输出 block 时把 `line.token.kind` 和 `line.token.rank` 写入。

### 1.3 PDF 路径 — `_build_pdf_blocks`

PDF document.json 的 texts 条目没有自动编号。但 `parse_number_token` 能直接解析 text 中的编号：

```python
def _build_pdf_blocks(document):
    total_pages, units = _load_document_units(document)
    blocks = []
    for no, unit in enumerate(units, 1):
        token = parse_number_token(unit.text)
        blocks.append({
            "no": no,
            "page": unit.page,
            "text": unit.text,
            "kind": token.kind if token else None,
            "rank": token.rank if token else None,
            "bbox": _bbox_to_block_bbox(unit.bbox),
        })
    return {"total_pages": total_pages, "blocks": blocks}
```

---

## 二、`contracts.py` — 原文渲染改用 blocks.json

### 2.1 当前实现

`_original_text_for_contract` 遍历 `document.json` 的 `contract_structure` 树，为每个节点的 title 生成 `{type: "h2"/"h3", text}`，为 content 中的每段生成 `{type: "p"/"highlight", text}`。

### 2.2 新实现

改用 blocks.json，根据 `rank` 决定 type：

```python
def _original_text_for_contract(contract, highlights):
    """从 blocks.json 渲染原文，根据 rank 决定层级。"""
    file_id = contract["file_id"]
    try:
        data = _load_blocks_json(file_id)
        blocks = data.get("blocks") or []
    except Exception:
        return _fallback_original_text(contract)
    
    result = []
    for block in blocks:
        rank = block.get("rank")
        text = block.get("text", "")
        if not text:
            continue
        
        # rank 决定视觉层级
        if rank is not None and rank <= 5:
            # chapter, part, attachment → h2
            result.append({"type": "h2", "text": text})
        elif rank is not None and rank <= 15:
            # article, heading → h3
            result.append({"type": "h3", "text": text})
        else:
            # 正文段落
            is_highlight = any(mark and (mark in text or text in mark) for mark in highlights)
            result.append({"type": "highlight" if is_highlight else "p", "text": text})
    
    return result or _fallback_original_text(contract)
```

### 2.3 新增辅助函数

```python
def _load_blocks_json(file_id: str) -> dict:
    """加载 blocks.json。"""
    settings = get_settings()
    path = settings.parsing_root / file_id / "blocks.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))
```

`_original_text_for_contract` 被两处调用：
- `start_audit_from_upload` / `start_audit`：`_original_text_for_contract(contract, [])` — 无高亮
- `get_audit_result`：`_original_text_for_contract(contract, highlights)` — 命中条款高亮

两处调用路径不变，仅内部实现切换到 blocks.json。

---

## 三、前端 — `AuditResult.vue`（无需变更）

当前 `AuditResult.vue` 的原文渲染逻辑为：

```html
<template v-for="(b, i) in data?.originalText || []" :key="i">
  <h2 v-if="b.type === 'h2'">{{ b.text }}</h2>
  <h3 v-else-if="b.type === 'h3'">{{ b.text }}</h3>
  <p v-else-if="b.type === 'highlight'" class="hl">{{ b.text }}</p>
  <p v-else>{{ b.text }}</p>
</template>
```

后端 `_original_text_for_contract` 返回的 `originalText` 结构不变（仍然是 `[{type, text}]`），前端无需修改。`h2` 对应章节标题（rank≤5），`h3` 对应条款标题（rank≤15），`highlight` 对应命中条款正文，`p` 对应普通正文。

---

## 四、rank → 渲染层级映射

| rank 范围 | type | 含义 |
|-----------|------|------|
| `None` | `p` | 无编号正文 |
| 0–5 | `h2` | 第X章、第X部分、附件X |
| 10–15 | `h3` | 第X条、标题(heading)、一、 |
| 20–40 | `p` | 1、/ 1.1 /（一）等子条款正文 |

---

## 五、变更文件清单

| # | 文件 | 动作 | 内容 |
|----|------|------|------|
| 1 | `services/block_builder.py` | 修改 | `_build_docx_blocks` 和 `_build_pdf_blocks` 写入 kind/rank |
| 2 | `api/contracts.py` | 修改 | `_original_text_for_contract` 改为读 blocks.json，新增 `_load_blocks_json` |

**前端无需变更**（`originalText` 结构不变）。

---

## 六、验证

```
上传 DOCX → 解析 → blocks.json 包含 kind/rank 字段
  → GET /contracts/:id/result → originalText 来自 blocks.json
  → 左栏原文：章节号为 h2 大标题，条款为 h3，正文为 p
```
