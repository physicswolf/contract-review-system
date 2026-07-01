# DOCX 解析增加 pymupdf4llm 引擎选项计划书

**项目**：contract-review-system  
**日期**：2026-07-01  
**版本**：v1.0  
**状态**：待开发  
**设计说明书**：`docs/develop/DOCX解析增加pymupdf4llm选项设计说明书.md`

---

## 一、背景

当前 `DOCX_PARSER_ENGINE` 支持 `docling` 和 `python-docx` 两个选项。需要增加 `pymupdf4llm`，与 docling 一样先通过 LibreOffice 将 DOCX 转为同排版 PDF，再使用 pymupdf4llm 引擎解析生成的 PDF。

## 二、现状

`document_parser.py` 中 DOCX 的解析路由：

```
.docx + python-docx → 直接解析 DOCX（python-docx）
.docx + docling     → LibreOffice 转 PDF → docling 解析 PDF
```

PDF 已有的 pymupdf4llm 路由：

```
.pdf + pymupdf4llm  → pymupdf4llm 直接解析 PDF
```

## 三、目标

新增路由：`.docx + pymupdf4llm → LibreOffice 转 PDF → pymupdf4llm 解析 PDF`

```
.docx + python-docx → 直接解析 DOCX（python-docx）
.docx + docling     → LibreOffice 转 PDF → docling 解析 PDF      ← 已有
.docx + pymupdf4llm → LibreOffice 转 PDF → pymupdf4llm 解析 PDF  ← 新增
```

## 四、改动范围

**仅修改 1 个文件**：`services/document_parser.py`。

关键改动点：

| 行号 | 改动 |
|------|------|
| 28 | `ERROR_MESSAGES` 更新允许值提示 |
| 76-79 | `pdf_path` 条件扩展（`docling` → `docling, pymupdf4llm`） |
| 97-107 | 解析路由新增 `.docx + pymupdf4llm` 分支 |
| 298-301 | `normalize_docx_parser_engine` 增加 `pymupdf4llm` |

**工作量**：极小（~15min），只改 1 个文件。

## 五、配置

`.env` 中使用方式：

```bash
DOCX_PARSER_ENGINE=pymupdf4llm
```

要求本机已安装 LibreOffice（`libreoffice` 或 `soffice` 在 PATH 中），与 docling 的 DOCX 路径要求一致。
