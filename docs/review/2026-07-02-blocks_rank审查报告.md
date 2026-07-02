# blocks.json rank + 原文改用 blocks 渲染 — 审查报告

**审查日期**：2026-07-02  
**审查范围**：`block_builder.py`、`contracts.py`

---

## 一、总体结论

**通过**。设计说明书全部要求已实现。70 tests passed，前端构建 7.89s。

---

## 二、逐项审查

### 2.1 `block_builder.py` — kind/rank 写入

| 路径 | 实现 | 结果 |
|------|------|------|
| DOCX | `_build_docx_blocks` 中 `line.token.kind` / `line.token.rank` 写入每个 block | ✅ `_parse_markdown_lines` 已调用 `parse_number_token`，直接复用 |
| PDF | `_build_pdf_blocks` 中 `parse_number_token(unit.text)` 解析每个文本单元的编号 | ✅ |

### 2.2 `contracts.py` — 原文渲染改用 blocks.json

| 函数 | 行为 | 结果 |
|------|------|------|
| `_original_text_for_contract` | 先尝试 `blocks.json`，失败降级 `document.json` 的 `contract_structure` 树，再降级 fallback | ✅ 三层降级 |
| `_load_blocks_json` | 读取 `storage/parsing/{file_id}/blocks.json` | ✅ |
| `_original_text_from_blocks` | 遍历 blocks，根据 rank 决定 type | ✅ |
| `_block_rank` | 安全转换 rank 为 int，`None`/异常返回 `None` | ✅ |

### 2.3 rank → type 映射

| rank | type | 覆盖的编号类型 | 结果 |
|------|------|--------------|------|
| `None` | `p` | 无编号正文 | ✅ |
| 0–5 | `h2` | chapter, part, attachment | ✅ |
| 10–15 | `h3` | article, chinese（一、）, heading（定义/总则） | ✅ |
| 20–40 | `p` | arabic（1、）, dotted（1.1）, parenthesized（（一）） | ✅ |

### 2.4 降级链

```
blocks.json 存在且有内容 → 使用 blocks.json 渲染
  ↓ 不存在或为空
document.json contract_structure 树 → 使用原有结构渲染
  ↓ 读取失败或为空
_fallback_original_text → 合同名称 + 甲乙方
```

### 2.5 测试与构建

| 检查项 | 结果 |
|--------|------|
| pytest | ✅ 70 passed |
| 前端构建 | ✅ 7.89s |

---

## 三、无问题
