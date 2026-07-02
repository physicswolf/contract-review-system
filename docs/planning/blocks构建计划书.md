# blocks.json 生成功能计划书

**项目**：contract-review-system  
**日期**：2026-07-02  
**版本**：v1.0  
**状态**：待开发  
**设计说明书**：`docs/develop/blocks构建设计说明书.md`  
**参考代码**：`/home/wolfsoft/my_code/contract/check/check_docx/xml_paragra_to_md.py`、`md_document_bboxes.py`

---

## 一、背景

当前文档解析管线生成 `document.json`（含 `contract_structure` 章节树），但缺少供审核引擎使用的**段落级定位块**。后续审核引擎需要 `blocks.json`——每个段落带页码和 bbox 坐标的块数组——用于条款召回时的原文定位和高亮。

## 二、目标

在解析管线中增加 `blocks.json` 的生成步骤，无论输入的 DOCX 还是 PDF，解析完成后均生成统一结构的 `blocks.json`。

### 2.1 输出结构

```json
{
  "total_pages": 18,
  "blocks": [
    { "no": 1, "page": 1, "text": "第一章 协议总则", "bbox": { "x": 90, "y": 200, "width": 400, "height": 16 } },
    { "no": 2, "page": 1, "text": "甲方：XX公司",     "bbox": { "x": 90, "y": 230, "width": 200, "height": 14 } }
  ]
}
```

### 2.2 DOCX 输入流程

```
DOCX
  ├─ Step A: python-docx 清除页眉页脚 → 保存干净版 DOCX
  ├─ Step B: python-docx 提取段落 XML + 编号 → markdown 文本行列表
  ├─ Step C: 干净版 DOCX → LibreOffice → PDF → docling/pymupdf4llm → document.json
  └─ Step D: markdown 行 + document.json（texts+bbox）→ 文本匹配 → blocks.json
```

### 2.3 PDF 输入流程

```
PDF → docling/pymupdf4llm → document.json（texts 已含 page_no/bbox）
  → 直接从 texts/tables 数组提取 → blocks.json
```

PDF 路径更简单——解析器已经产出了带坐标的 texts 数组，无需 markdown 中间步骤。

## 三、集成点

`blocks.json` 的生成挂在解析任务完成之后（`document_tasks._run_task` 的 `succeeded` 阶段）。与 `document.json` 同级保存到 `storage/parsing/{file_id}/blocks.json`。

**不改变**现有 `document.json` 和 `contract_structure` 的生成逻辑，`blocks.json` 作为额外产物并行写入。

## 四、任务分解

| # | 任务 | 文件 | 工作量 |
|----|------|------|--------|
| 1 | 新建 `services/block_builder.py` — blocks.json 构建主逻辑 | 新建 | 大（~3h） |
| 2 | DOCX 页眉页脚清除 | `block_builder.py` 内 | 中 |
| 3 | DOCX 段落提取 + 编号 | 复用 `python_docx_contract_parser` 逻辑 | 中 |
| 4 | 文本匹配 + bbox 定位 | 移植 `md_document_bboxes.py` 算法 | 中 |
| 5 | PDF blocks 直接生成 | `block_builder.py` 内 | 小 |
| 6 | 集成到解析管线 | `document_tasks.py` + `document_parser.py` | 小 |
| 7 | 验证 | — | 小 |
| **合计** | | **~6h** | |

## 五、依赖

- `python-docx`（已有）
- `docling`（已有）
- `pymupdf4llm`（已有）
- LibreOffice（已有）
- 新增依赖：无（全部复用已有库）
