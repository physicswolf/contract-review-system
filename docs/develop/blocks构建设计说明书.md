# blocks.json 构建设计说明书

**项目**：contract-review-system  
**日期**：2026-07-02  
**版本**：v1.0  
**对应计划书**：`docs/planning/blocks构建计划书.md`  
**参考代码**：`/home/wolfsoft/my_code/contract/check/check_docx/`

---

## 一、新建 `services/block_builder.py`

### 1.1 入口函数

```python
def build_blocks_json(file_id: str, source_path: Path, extension: str, settings: Settings) -> dict:
    """构建 blocks.json，作为 document.json 的并行产物。"""
    document = load_document_json(file_id, settings)
    
    if extension == ".docx":
        return _build_docx_blocks(file_id, source_path, document, settings)
    else:
        return _build_pdf_blocks(document)
```

返回的 dict 直接 `json.dumps` 写入 `storage/parsing/{file_id}/blocks.json`。

---

## 二、DOCX 路径

### 2.1 整体流程

```
source.docx
  → _clean_docx_headers_footers(docx_path) → clean.docx（临时文件）
  → _extract_markdown_lines(docx_path) → markdown_line[]
  → clean.docx → LibreOffice → PDF → docling/pymupdf4llm → document.json
  → _load_document_units(document.json) → DocumentUnit[]
  → _match_lines_to_units(md_lines, units) → blocks[]
```

### 2.2 清除页眉页脚

```python
def _clean_docx_headers_footers(docx_path: Path) -> Path:
    """用 python-docx 创建一份清除页眉页脚的临时副本。"""
    from docx import Document
    
    doc = Document(str(docx_path))
    for section in doc.sections:
        section.header.clear()
        section.footer.clear()
    
    clean_path = docx_path.with_stem(docx_path.stem + "_clean")
    doc.save(str(clean_path))
    return clean_path
```

清除页眉页脚的目的是避免 LibreOffice 转换 PDF 时页眉页脚文本混入正文，干扰后续文本匹配。

### 2.3 提取 Markdown 行

在 `python_docx_contract_parser.py` 中已有完整的段落遍历 (`iter_block_items`)、编号解析 (`NumberingResolver`) 和文本提取逻辑。服用这些逻辑，输出简化版的行列表：

```python
def _extract_markdown_lines(docx_path: Path) -> list[str]:
    """从 DOCX 段落提取带编号的 markdown 行。"""
    from docx import Document
    from src.services.python_docx_contract_parser import (
        NumberingResolver, iter_block_items,
        normalize_space, get_outline_level, is_heading_paragraph,
    )
    
    doc = Document(str(docx_path))
    numbering = NumberingResolver(doc)
    lines: list[str] = []
    
    for block in iter_block_items(doc):
        if not isinstance(block, Paragraph):
            continue
        text = normalize_space(block.text)
        if not text:
            continue
        
        autonum = numbering.next_label(block)
        label = autonum["label"] if autonum else ""
        lines.append(f"{label}{text}")
    
    return lines
```

### 2.4 从 document.json 提取定位单元

移植 `md_document_bboxes.py` 的 `load_document_units()`，从 document.json 的 `texts` 和 `tables` 数组中提取带 bbox 的定位单元：

```python
@dataclass
class DocumentUnit:
    order: int
    page: int
    line_index: int
    text: str
    bbox: dict[str, float]
    start: int = 0
    end: int = 0

def _load_document_units(document: dict) -> list[DocumentUnit]:
    """从 document.json 提取带 bbox 的定位单元列表。"""
    units = []
    order = 0
    for collection in ("texts", "tables"):
        for item in document.get(collection, []):
            page, line_index, bbox = _extract_bbox(item)
            text = str(item.get("text") or "").replace("<br>", "")
            if not text or page is None or bbox is None:
                continue
            units.append(DocumentUnit(
                order=order, page=int(page),
                line_index=int(line_index or 0),
                text=text,
                bbox={k: float(bbox[k]) for k in ("l", "t", "r", "b") if k in bbox},
            ))
            order += 1
    units.sort(key=lambda u: (u.page, u.line_index, u.order))
    return units
```

### 2.5 文本匹配

移植 `md_document_bboxes.py` 的匹配算法，将 markdown 行与 document units 进行文本逐行匹配：

```
markdown 行: "第四条 项目交付与验收"
document units: ["第四条", "项目交付与验收", "...", "第四条 项目交付与验收"]

匹配流程：
  1. normalize 标准化文本（全角→半角，去空格）
  2. 在 flat document 中查找 candidate
  3. 精确匹配优先，前缀匹配次之，loose 匹配兜底
  4. 匹配成功 → 记录 flat document 中的字符位置 → 映射到 units 范围
  5. 从覆盖的 units 中计算 bbox（合并多个 unit 的 bbox）
```

移植 `match_candidates()`, `find_line_start()`, `locate_markdown_lines()`, `units_for_range()`, `build_bbox()` 等函数。

### 2.6 生成 blocks

```python
def _build_docx_blocks(file_id, source_path, document, settings) -> dict:
    # 1. 提取 markdown 行
    md_lines = _extract_markdown_lines(source_path)
    
    # 2. 加载 document units
    units = _load_document_units(document)
    flat_text = _build_flat_document(units)
    
    # 3. 构建 markdown 行对象
    lines = _parse_markdown_lines(md_lines)
    
    # 4. 匹配定位
    _locate_markdown_lines(lines, flat_text, units)
    
    # 5. 生成 blocks
    blocks = []
    for line in lines:
        matched_units = _units_for_range(units, line.start, line.end)
        page, bbox = _build_bbox(matched_units)
        blocks.append({
            "no": line.no,
            "page": page,
            "text": line.text,
            "bbox": bbox,
        })
    
    total_pages = max((u.page for u in units), default=1)
    return {"total_pages": total_pages, "blocks": blocks}
```

---

## 三、PDF 路径

PDF 解析器（docling/pymupdf4llm）的 `document.json` 中 `texts[]` 数组已包含 `prov[].page_no` 和 `prov[].bbox`。无需 markdown 中间步骤，直接从中提取 blocks：

```python
def _build_pdf_blocks(document: dict) -> dict:
    """从 PDF 文档 JSON 直接提取 blocks。"""
    units = _load_document_units(document)
    blocks = []
    for i, unit in enumerate(units, 1):
        blocks.append({
            "no": i,
            "page": unit.page,
            "text": unit.text,
            "bbox": {
                "x": unit.bbox.get("l", 0),
                "y": unit.bbox.get("t", 0),
                "width": max(0, unit.bbox.get("r", 0) - unit.bbox.get("l", 0)),
                "height": max(0, unit.bbox.get("b", 0) - unit.bbox.get("t", 0)),
            },
        })
    total_pages = max((u.page for u in units), default=1)
    return {"total_pages": total_pages, "blocks": blocks}
```

---

## 四、集成到解析管线

### 4.1 `document_tasks.py` — 解析完成时生成

在 `_run_task()` 的 succeeded 阶段（写完 `document.json` 之后）调用 `build_blocks_json()`：

```python
# 现有：解析成功
self._update(task_id, status="succeeded", stage="completed",
             parsing_dir=parsing_artifacts.directory,
             document_json_path=parsing_artifacts.json_path)

# 新增：生成 blocks.json
try:
    from src.services.block_builder import build_blocks_json
    blocks_data = build_blocks_json(
        stored_upload.metadata.id,
        stored_upload.path,
        stored_upload.metadata.extension,
        settings,
    )
    blocks_path = parsing_artifacts.directory / "blocks.json"
    with open(blocks_path, "w", encoding="utf-8") as f:
        json.dump(blocks_data, f, ensure_ascii=False, indent=2)
except Exception:
    _LOGGER.exception("Failed to build blocks.json for file_id=%s",
                      stored_upload.metadata.id)
```

blocks.json 生成失败不影响解析成功状态（降级处理）。

### 4.2 `ParsingArtifacts` — 增加 blocks_json_path 字段（可选）

当前 `ParsingArtifacts` 有 `json_path` 和 `pdf_path`。可增加 `blocks_path` 方便统一管理，但不强制。

---

## 五、产物文件布局

```
storage/parsing/{file_id}/
├── document.json           ← 解析产物（已有）
├── document.pdf            ← DOCX 转换的 PDF（docling/pymupdf4llm 时）
└── blocks.json             ← 新增：段落级定位块
```

---

## 六、变更文件清单

| # | 文件 | 动作 |
|----|------|------|
| 1 | `services/block_builder.py` | **新建**（~350行） |
| 2 | `pipelines/document_tasks.py` | 修改：succeeded 阶段调用 block_builder |
| — | `services/document_parser.py` | **无需变更** |
| — | `services/python_docx_contract_parser.py` | 复用其 `NumberingResolver`、`iter_block_items` 等 |

---

## 七、验证路径

```
[DOCX + docling]
  上传 .docx → 解析完成 → blocks.json 存在
  → blocks[0] = {no:1, page:1, text:"第一章 ...", bbox:{x,y,width,height}}

[PDF + pymupdf4llm]
  上传 .pdf → 解析完成 → blocks.json 存在
  → 每个 text 项对应一个 block，page/bbox 直接来自 document.json

[blocks.json 缺失 bbox]
  部分块因文本无法匹配而 bbox 为空 → 不影响其他块生成
  → 前端定位时跳过 bbox 为空的块
```
