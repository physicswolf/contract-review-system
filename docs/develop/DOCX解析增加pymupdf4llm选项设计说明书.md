# DOCX 解析增加 pymupdf4llm 选项设计说明书

**项目**：contract-review-system  
**日期**：2026-07-01  
**版本**：v1.0  
**对应计划书**：`docs/planning/DOCX解析增加pymupdf4llm选项计划书.md`

---

## 一、改动文件

**仅 `services/document_parser.py`** 一个文件，4 处改动。

### 1.1 错误提示更新（line 28）

```python
# 改前
"UNSUPPORTED_DOCX_PARSER_ENGINE": "DOCX_PARSER_ENGINE 仅支持 docling 或 python-docx",

# 改后
"UNSUPPORTED_DOCX_PARSER_ENGINE": "DOCX_PARSER_ENGINE 仅支持 docling、python-docx 或 pymupdf4llm",
```

### 1.2 pdf_path 条件扩展（lines 76-79）

```python
# 改前
pdf_path = (
    parsing_dir / CONVERTED_PDF_FILENAME
    if extension == ".docx" and docx_parser_engine == "docling"
    else None
)

# 改后
pdf_path = (
    parsing_dir / CONVERTED_PDF_FILENAME
    if extension == ".docx" and docx_parser_engine in ("docling", "pymupdf4llm")
    else None
)
```

`pdf_path` 非空意味着"需要先用 LibreOffice 将 DOCX 转为 PDF"，后续解析的是转换后的 PDF 而非原始 DOCX。此条件原来只对 `docling` 成立，现扩展为 `docling` 或 `pymupdf4llm`。

### 1.3 解析路由新增分支（lines 97-107）

```python
# 改前
try:
    if extension == ".pdf" and pdf_parser_engine == "pymupdf4llm":
        json_data = convert_pdf_to_pymupdf4llm_json_data(source_path, file_id)
    else:
        json_data = convert_to_json_data(conversion_input_path)
        if extension == ".pdf":
            json_data = add_docling_pdf_contract_structure(
                json_data,
                source_path,
                file_id,
            )
except Exception as exc:
    raise ParsingError("DOCUMENT_PARSING_ERROR", status_code=422) from exc

# 改后
try:
    if extension == ".pdf" and pdf_parser_engine == "pymupdf4llm":
        json_data = convert_pdf_to_pymupdf4llm_json_data(source_path, file_id)
    elif extension == ".docx" and docx_parser_engine == "pymupdf4llm":
        json_data = convert_pdf_to_pymupdf4llm_json_data(conversion_input_path, file_id)
    else:
        json_data = convert_to_json_data(conversion_input_path)
        if extension == ".pdf":
            json_data = add_docling_pdf_contract_structure(
                json_data,
                source_path,
                file_id,
            )
except Exception as exc:
    raise ParsingError("DOCUMENT_PARSING_ERROR", status_code=422) from exc
```

新增的 `elif` 分支：当扩展名是 `.docx` 且 docx 解析引擎为 `pymupdf4llm` 时，使用 `conversion_input_path`（即 LibreOffice 转换后的 PDF 路径）调用 `convert_pdf_to_pymupdf4llm_json_data`。

> 注意：此时 `source_path` 仍是原始 `.docx` 文件路径，`conversion_input_path` 是转换后的 PDF。传给 pymupdf4llm 的必须是 PDF 路径。

### 1.4 normalize_docx_parser_engine 扩展（lines 298-301）

```python
# 改前
def normalize_docx_parser_engine(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    if normalized not in {"docling", "python-docx"}:
        raise ParsingError("UNSUPPORTED_DOCX_PARSER_ENGINE", status_code=500)
    return normalized

# 改后
def normalize_docx_parser_engine(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    if normalized not in {"docling", "python-docx", "pymupdf4llm"}:
        raise ParsingError("UNSUPPORTED_DOCX_PARSER_ENGINE", status_code=500)
    return normalized
```

---

## 二、解析流程对比

### 改前

```
DOCX
  ├─ python-docx → python_docx_contract_parser → document.json
  └─ docling → LibreOffice→PDF → docling 解析 → document.json
```

### 改后

```
DOCX
  ├─ python-docx → python_docx_contract_parser → document.json
  ├─ docling     → LibreOffice→PDF → docling 解析 → document.json
  └─ pymupdf4llm → LibreOffice→PDF → pymupdf4llm 解析 → document.json  ← 新增
```

---

## 三、产物差异

| 引擎 | `document.json` schema | `contract_structure` | `texts[]` 定位 |
|------|-----------------------|---------------------|---------------|
| python-docx | `PythonDocxContractDocument` | ✅ 基于段落样式+编号 | `paragraph_index` |
| docling | `DoclingDocument` | ✅ docling 模型识别标题 | `page_no` + `prov[].bbox` |
| pymupdf4llm | `PyMuPDF4LLMContractDocument` | ✅ 基于编号+heading | `page_no` + `line_index` |

三种引擎都输出 `contract_structure` 树，但 `texts` 数组结构不同（`prov` 字段内容因引擎而异）。上层读取 `contract_structure` 的逻辑（`llm_classifier._extract_preamble`、`contracts._original_text_for_contract`）已兼容三种 schema。

---

## 四、前置依赖

- LibreOffice（`libreoffice` 或 `soffice`）已安装且可执行
- `pymupdf4llm` 已在 `pyproject.toml` 依赖中（`pymupdf4llm>=1.27.2.3`）✅

---

## 五、验证路径

```
1. 设置 DOCX_PARSER_ENGINE=pymupdf4llm
2. 上传 .docx 文件
3. 检查 storage/parsing/{file_id}/ 目录：
   └── document.pdf     ← LibreOffice 转换产物
   └── document.json    ← pymupdf4llm 解析产物
4. document.json 中 schema_name = "PyMuPDF4LLMContractDocument"
5. contract_structure 树有正确的章节结构
```
