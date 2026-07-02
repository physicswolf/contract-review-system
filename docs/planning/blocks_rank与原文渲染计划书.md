# blocks.json 增加 rank 信息 + 审核页原文改用 blocks 渲染计划书

**项目**：contract-review-system  
**日期**：2026-07-02  
**版本**：v1.0  
**状态**：待开发  
**设计说明书**：`docs/develop/blocks_rank与原文渲染设计说明书.md`

---

## 一、背景

当前 `blocks.json` 只包含 `{no, page, text, bbox}`，缺少章节层级信息。审核结果页左侧原文通过遍历 `document.json` 的 `contract_structure` 树来渲染，与 blocks.json 是两个独立的数据源。

## 二、目标

1. **blocks.json 增加 rank**：在生成 blocks.json 时，对每行文本调用 `parse_number_token` 解析编号，将 `kind` 和 `rank` 写入每个 block
2. **审核页原文改用 blocks.json**：用 blocks.json 渲染审核结果页左侧原文，根据 `rank` 值决定视觉层级（h2/h3/p）

## 三、rank 体系（来自 contract_structure_parser）

| kind | 示例 | rank | 原文渲染 |
|------|------|------|---------|
| part | 第一部分 | 0 | h2（居中标题） |
| chapter | 第一章 | 0 | h2 |
| attachment | 附件一 | 5 | h3 |
| article | 第一条 | 10 | h3 |
| chinese | 一、 | 10 | h3 |
| heading | 定义/总则 | 15 | h3 |
| arabic | 1、 | 20 | p（正文段落） |
| dotted | 1.1 / 1.1.1 | 21+ | p |
| parenthesized | （一） | 40 | p |
| 无编号 | （普通正文） | — | p |

## 四、改动范围

### 4.1 后端

| # | 任务 | 文件 | 工作量 |
|----|------|------|--------|
| 1 | `_build_docx_blocks` 中调用 `parse_number_token`，写入 kind/rank | `block_builder.py` | 小 |
| 2 | `_build_pdf_blocks` 中同样调用 `parse_number_token` | `block_builder.py` | 小 |
| 3 | `contracts.py` 的 `_original_text_for_contract` 改为读 blocks.json | `contracts.py` | 中 |

### 4.2 前端

| # | 任务 | 文件 | 工作量 |
|----|------|------|--------|
| 4 | `AuditResult.vue` 根据 rank 渲染原文层级 | `AuditResult.vue` | 中 |

**合计**：4 个文件，~3h。

## 五、blocks.json 新结构

```json
{
  "total_pages": 18,
  "blocks": [
    {
      "no": 1,
      "page": 1,
      "text": "第一章 协议总则",
      "kind": "chapter",
      "rank": 0,
      "bbox": {...}
    },
    {
      "no": 2,
      "page": 1,
      "text": "第一条 合同标的",
      "kind": "article",
      "rank": 10,
      "bbox": {...}
    },
    {
      "no": 3,
      "page": 1,
      "text": "甲方：华城数字建设有限公司",
      "kind": null,
      "rank": null,
      "bbox": {...}
    }
  ]
}
```
