# 合同分类 & 条款召回 — 评测方案与 API 设计

| 项目 | 内容 |
| ---- | ---- |
| 文档主题 | 合同分类评测效果 + 合同条款召回（原文/位置/页码）+ 对应 API 设计 |
| 缘起 | PR #2 评审意见：补充「合同分类的评测效果」与「对应的 API 设计」；条款召回环节需与见晓东/见老师对齐，**返回合同原文、合同原文位置信息、对应 PDF 页码** |
| 对齐依据 | `方案设计-合同审核系统.md`（§2.2 分类、§2.4 召回）、`design/审核详情页技术设计.md`（`blocks.json` 坐标方案）、`design/配置中心技术设计.md`（合同类型/规则数据模型）、`Parser选型-六框架对比.md`（解析与章节切分实测） |
| 日期 | 2026-06-30 |
| 版本 | v1.0 |
| 关联项目 | 北航课题 · 合同 AI 分析系统 |

---

## 〇、本文档要解决的三个问题

1. **合同分类的评测效果**：分类怎么做、用什么数据集与指标评、各方案对比结论（§一、§二）。
2. **合同条款召回**：召回链路如何产出「**合同原文 + 原文位置信息 + PDF 页码**」，与审核详情页 `blocks.json` 坐标方案对齐（§三）。
3. **对应的 API 设计**：分类 API、召回/审核结果 API 的请求/响应契约（§四）。

> 关键对齐结论（与见老师确认口径）：召回的每条命中结果**必须可回溯到 PDF**，即同时返回 ① 命中的**合同原文文本**、② **位置信息**（PDF user space bbox，原点左下，与 pdf.js viewport 一致）、③ **PDF 页码**。一条风险可能跨多行/多块，故位置信息用 `locations[]` 数组承载，并保留一个主定位 `primary_location` 兼容旧前端。

---

## 一、合同分类：方法与链路（评测对象）

延续 `方案设计-合同审核系统.md` §2.2 的结论：**关键词预筛 + LLM few-shot 主判 + 置信度**，类型与审核点解耦，分类仅用于「识别 / 归档 / 检索 / 推荐审核点」。

```text
合同首段 + 关键段（标题、抬头、第一条、签署页）
  → ① 关键词规则预筛：命中「采购/供货/价款」「服务/技术支持/维保」等 → 候选类型集合（缩小范围、加速、可解释）
  → ② LLM few-shot 主判：输入「候选类型定义 + 识别关键词示例 + 抽取的关键段」
        输出 { type, confidence, candidates[], evidence }
  → ③ 置信度判定：
        confidence ≥ 阈值(τ=0.75) 且 唯一高分 → 直接采用
        confidence < τ 或 多类接近          → need_confirm=true，前端高亮可改
```

分类候选体系（与 `配置中心技术设计.md` 内置类型 + `custom_contract_type` 自定义类型对齐）：

| 类型编码 | 类型名称 | 识别关键词（示例） |
| ---- | ---- | ---- |
| PURCHASE | 采购合同 | 采购、供货、货物、验收、价款 |
| SERVICE | 服务合同 | 服务、技术支持、维保、交付成果 |
| SALE | 销售合同 | 销售、出售、回款、买受人 |
| LEASE | 租赁合同 | 租赁、租金、押金、承租方 |
| COOP | 合作协议 | 合作、共建、分成、共同投入 |
| OTHER | 其他/通用合同 | （兜底，未命中上述特征） |

> 自定义类型由配置中心维护，参与候选集与 few-shot 提示词构造，无需改代码。

---

## 二、合同分类评测方案与结果

> 目的：用统一数据集与指标，量化「分类准确率、置信度可靠性、易混类型」，并对比候选方案，支撑选型与上线门槛。

### 2.1 评测数据集

| 项 | 说明 |
| ---- | ---- |
| 来源 | 项目 `backend/uploads/` 真实合同 + 业务方补充脱敏样本 |
| 规模（目标） | ≥ 300 份，6 类各 ≥ 40 份；含边界/混合类型 ≥ 30 份 |
| 标注 | 双人独立标注类型标签，冲突由第三人仲裁；记录「主类型 + 可接受次类型」 |
| 切分 | 按类型分层抽样：dev 20% 调阈值/提示词，test 80% 仅评测一次 |
| 难度分桶 | 易（标题/抬头明确）/ 中（需读正文）/ 难（混合业务、改写标题） |

> 注：当前仓库样本仅 3 份（2 PDF + 1 DOCX），不足以出统计显著结论。下表为**评测协议 + 结果表模板**，数值待按本协议跑批后回填；§2.4 给出当前小样本的冒烟结果与预期区间，已明确标注「实测/预期」。

### 2.2 评测指标

| 指标 | 定义 | 用途 |
| ---- | ---- | ---- |
| Accuracy | 预测主类型 == 标注主类型 的比例 | 总体效果 |
| Macro-P / R / F1 | 各类 P/R/F1 的宏平均 | 抗类别不平衡 |
| 混淆矩阵 | 6×6 真实 × 预测 | 定位易混类型 |
| Top-2 命中率 | 真值落在候选 candidates 前 2 | 评估「可改」体验下限 |
| 置信度校准 ECE | 预测置信度与真实正确率的偏差 | 阈值 τ 是否可信 |
| 待人工确认率 | need_confirm=true 占比 | 人工成本 |
| 误确认率 | need_confirm=false 但分类错误 | 自动通过的风险 |
| 平均延迟 | 端到端分类耗时 P50/P95 | 性能 |

上线门槛（建议）：Accuracy ≥ 0.90、Macro-F1 ≥ 0.88、误确认率 ≤ 0.03、P95 延迟 ≤ 3s。

### 2.3 候选方案对比（评测维度）

| 方案 | 原理 | 预期优点 | 预期短板 |
| ---- | ---- | ---- | ---- |
| A 纯关键词规则 | 命中词表 | 极快、零成本、可解释 | 改写/混合类型漏判，召回低 |
| B 纯向量相似度 | 合同 embedding 比类型中心 | 无需 LLM、快 | 边界类型易混，需 embedding |
| C 纯 LLM few-shot | 关键段直接喂 LLM | 可解释、易扩类 | 候选过宽时略慢、依赖提示词 |
| **D 关键词预筛 + LLM（主路）** | A 缩候选 → C 定夺 | 快且准、可解释、可扩展 | 依赖提示词质量 |

### 2.4 评测结果

**（1）方案对比（test 集，数值待回填）**

| 方案 | Accuracy | Macro-F1 | Top-2 | 待确认率 | 误确认率 | P95 延迟 |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| A 纯关键词 | _待测_ | _待测_ | _待测_ | — | _待测_ | <50ms |
| B 纯向量 | _待测_ | _待测_ | _待测_ | — | _待测_ | _待测_ |
| C 纯 LLM | _待测_ | _待测_ | _待测_ | _待测_ | _待测_ | _待测_ |
| **D 关键词+LLM** | _待测_ | _待测_ | _待测_ | _待测_ | _待测_ | _待测_ |

**（2）当前小样本冒烟（实测，n=3，仅验证链路可跑，不具统计意义）**

| 文件 | 标注类型 | 预测类型 | 置信度 | 是否正确 |
| ---- | ---- | ---- | ---- | ---- |
| 9449befe….pdf | 待标注 | 待跑 | — | — |
| 946755b7….pdf | 待标注 | 待跑 | — | — |
| e8c9b400….docx | 待标注 | 待跑 | — | — |

**（3）预期结论（设计推断，非实测，待数据验证）**

- 方案 D 预期 Accuracy 落在 0.90~0.95：关键词预筛压缩候选后，LLM few-shot 在「采购/服务/销售/租赁/合作」主类上区分度高。
- 主要易混对：**采购 ↔ 服务**（含实施服务的采购）、**合作 ↔ 服务**（联合运营 vs 受托服务）、**销售 ↔ 采购**（立场视角相反）。建议在提示词中加入「以买方/卖方立场 + 主要交易标的」区分规则，并在配置中心补充这几类的差异化关键词。
- 置信度阈值 τ 用 dev 集按 ECE + 误确认率联合标定，初值 0.75。

### 2.5 复现方式

```text
1. 准备数据：data/eval/classify/{type}/*.{pdf,docx} + labels.csv(file, label, accept_alt)
2. 解析：Word→python-docx / PDF→docling（见 Parser 选型），抽取关键段
3. 跑分类：对 A/B/C/D 各方案输出 prediction.csv(file, pred, confidence, candidates)
4. 算指标：scripts/eval_classify.py → metrics.json + confusion.png
5. 回填本节表格，归档到 docs/
```

---

## 三、合同条款召回（核心：原文 + 位置 + 页码）

对应原型「审核点 → 命中合同条款 → 风险研判 → 定位原文」。本节重点是**与见老师对齐的输出契约**：召回结果可回溯到 PDF 原文与坐标。

### 3.1 召回链路

```text
预处理：Word→python-docx / PDF→docling 解析 → blocks.json（块文本 + page + bbox）
        章节切分（docling 模型标题为主）→ 条款级切片，切片携带其覆盖的 block_no 集合

for 每个用户勾选的审核点:
    query  = 审核点描述 + 原文示例 + 风险点说明
    corpus = 当前合同的条款/章节切片
    ① 混合检索 BM25 + 向量(Qwen3-Embedding) → Top-N 候选切片
    ② Qwen3-Reranker 精排 → Top-K
    ③ 立场化 LLM 研判（甲方/乙方）：是否命中风险 + 等级 + 修改建议 + 命中 block_no[]
    ④ 后端按 block_no[] 回查 blocks.json → 组装 原文文本 + page + bbox（见 3.3）
    → 输出风险卡片（含可回溯定位）
```

### 3.2 与 `blocks.json` 对齐（数据底座）

完全复用 `design/审核详情页技术设计.md` 的 `blocks.json`：docling 解析后每个文本块输出 PDF user space 坐标（points，原点左下角，与 pdf.js viewport 一致）。

```json
{
  "total_pages": 18,
  "blocks": [
    { "no": 10, "page": 4, "text": "若甲方在十个工作日内未提出书面异议，则视为项目自动验收通过。",
      "bbox": { "x": 90, "y": 600, "width": 400, "height": 16 } }
  ]
}
```

- 构造 LLM Prompt 时只传 `no + text`（不含坐标），LLM 回 `hit_block_no[]`；
- 后端用 `hit_block_no[]` 回查 `page + bbox`，落库并下发前端高亮。

### 3.3 召回命中结果结构（对齐见老师要求）★

一条命中可能跨多行/多块、甚至跨页，故用 `locations[]` 承载完整位置信息，并提供 `primary_location` 作主定位（兼容现有 `audit_result_item` 的单 bbox 字段）。

```json
{
  "audit_point": "交付计划与验收机制",
  "title": "默示验收风险",
  "risk_level": 1,
  "risk_summary": "存在「逾期未提书面异议即视为自动验收」的默示验收条款。",
  "modify_suggestion": ["删除自动验收表述，改为双方签署书面验收单后方视为验收完成"],
  "clause_name": "第四条 项目交付与验收",

  "hit_text": "若甲方在十个工作日内未提出书面异议，则视为项目自动验收通过。",
  "primary_location": { "block_no": 10, "page": 4, "bbox": { "x": 90, "y": 600, "width": 400, "height": 16 } },
  "locations": [
    { "block_no": 10, "page": 4, "bbox": { "x": 90, "y": 600, "width": 400, "height": 16 },
      "text": "若甲方在十个工作日内未提出书面异议，", "char_start": 0,  "char_end": 18 },
    { "block_no": 11, "page": 4, "bbox": { "x": 90, "y": 582, "width": 220, "height": 16 },
      "text": "则视为项目自动验收通过。",                 "char_start": 18, "char_end": 30 }
  ],
  "retrieval": { "score": 0.83, "rerank_score": 0.91, "recall_rank": 1 }
}
```

字段对齐说明（三项必返）：

| 见老师要求 | 字段 | 坐标系/口径 |
| ---- | ---- | ---- |
| 合同原文 | `hit_text`（整体）、`locations[].text`（分块） | 与 `blocks.json` 文本一致 |
| 原文位置信息 | `primary_location.bbox` / `locations[].bbox`（含 `char_start/char_end` 字符级 span） | PDF user space，points，原点左下，pdf.js 直接用 |
| PDF 页码 | `primary_location.page` / `locations[].page` | 1-based，docling `page` |

> 兼容性：现有 `audit_result_item` 的 `hit_block_no / hit_page / hit_bbox_x/y/w/h` 即 `primary_location` 的拍平存储；`locations[]` 多块定位以 JSON 列扩展存储（见 §四存储增量）。

### 3.4 召回质量评测（简版，与分类评测同范式）

| 指标 | 定义 |
| ---- | ---- |
| Recall@K | 审核点对应「真值条款」是否落在 Top-K |
| MRR | 真值条款的平均倒数排名 |
| 定位准确率 | 返回 bbox 与真值条款 bbox 的 IoU ≥ 0.5 比例 |
| 页码准确率 | `page` 与真值页码一致比例 |

数据：对若干合同，人工标注「每个审核点应命中的条款 + 其 block_no/page/bbox」为 golden set；阶段一可先用 BM25 出基线，阶段二接入 embedding + reranker 对比提升。

---

## 四、API 设计

> 基础路径：`/api/v1/audit`（与 `审核详情页技术设计.md` 一致），新增分类与召回相关契约；统一响应 `{ code, data, msg }`，`code=0` 为成功。

### 4.1 合同分类 API

#### （1）触发/获取分类结果

上传后随解析自动触发分类，结果可单独查询；也支持用户手动改类。

```
GET /api/v1/audit/tasks/:task_id/classification
```

```json
{
  "code": 0,
  "data": {
    "type": "采购合同",
    "type_code": "PURCHASE",
    "confidence": 0.93,
    "need_confirm": false,
    "candidates": [
      { "type": "采购合同", "type_code": "PURCHASE", "confidence": 0.93 },
      { "type": "服务合同", "type_code": "SERVICE", "confidence": 0.41 }
    ],
    "evidence": ["标题含「采购」", "第二条出现「供货与验收」", "存在「价款支付」条款"],
    "source": "keyword+llm",
    "elapsed_ms": 1280
  }
}
```

- `need_confirm=true` 时前端高亮提示「请确认合同类型」。
- `candidates` 供前端下拉「可改」。

#### （2）用户确认/修改分类

```
PUT /api/v1/audit/tasks/:task_id/classification
```

```json
// 请求
{ "type_code": "SERVICE", "type": "服务合同" }
// 响应
{ "code": 0, "data": { "type": "服务合同", "type_code": "SERVICE", "confirmed": true } }
```

> 合同类型仅用于识别/归档/检索/推荐审核点，**不强绑定**审核规则（保持解耦），修改后仅更新推荐审核点集合。

#### （3）分类候选体系（供前端/引擎读取，来自配置中心）

```
GET /api/v1/config/contract-types          # 内置 + 自定义类型（见配置中心设计 §5.4）
```

### 4.2 条款召回 / 审核结果 API

召回结果落地在审核结果中。沿用 `审核详情页技术设计.md` 的结果接口，**扩展位置信息为可回溯结构**。

#### （1）获取风险结果列表（含原文/位置/页码）

```
GET /api/v1/audit/tasks/:task_id/results
```

Query：`category_id`（维度 Tab 过滤）、`risk_level`（1 重大 / 2 一般，不传返回全部）

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": 1,
        "sort_order": 1,
        "category_id": 2,
        "category_name": "法务风险",
        "audit_point": "交付计划与验收机制",
        "title": "默示验收风险",
        "risk_level": 1,
        "risk_summary": "存在默示验收条款……",
        "modify_suggestion": ["删除自动验收表述，改为书面验收单"],
        "clause_name": "第四条 项目交付与验收",

        "hit_text": "若甲方在十个工作日内未提出书面异议，则视为项目自动验收通过。",
        "primary_location": {
          "block_no": 10, "page": 4,
          "bbox": { "x": 90, "y": 600, "width": 400, "height": 16 }
        },
        "locations": [
          { "block_no": 10, "page": 4, "bbox": { "x": 90, "y": 600, "width": 400, "height": 16 },
            "text": "若甲方在十个工作日内未提出书面异议，", "char_start": 0, "char_end": 18 },
          { "block_no": 11, "page": 4, "bbox": { "x": 90, "y": 582, "width": 220, "height": 16 },
            "text": "则视为项目自动验收通过。", "char_start": 18, "char_end": 30 }
        ],
        "retrieval": { "score": 0.83, "rerank_score": 0.91, "recall_rank": 1 }
      }
    ]
  }
}
```

前端「定位原文」：取 `primary_location.page` 跳页，按 `locations[].bbox` 逐块高亮（pdf.js viewport 坐标，无需换算）。

#### （2）召回调试接口（可选，开发期定位用）

返回某审核点的 Top-K 召回切片与定位，便于评测召回质量、排查漏召回。

```
POST /api/v1/audit/tasks/:task_id/retrieve
```

```json
// 请求
{ "audit_point_id": 4, "top_k": 5 }
// 响应
{
  "code": 0,
  "data": {
    "audit_point": "交付计划与验收机制",
    "hits": [
      {
        "chunk_id": "c4-2",
        "clause_name": "第四条 项目交付与验收",
        "text": "……视为项目自动验收通过。",
        "page": 4,
        "block_nos": [10, 11],
        "bbox_list": [
          { "page": 4, "bbox": { "x": 90, "y": 600, "width": 400, "height": 16 } },
          { "page": 4, "bbox": { "x": 90, "y": 582, "width": 220, "height": 16 } }
        ],
        "score": 0.83, "rerank_score": 0.91
      }
    ]
  }
}
```

#### （3）PDF 地址（左栏渲染，沿用既有接口）

```
GET /api/v1/audit/tasks/:task_id/pdf-url   →  { "url": "/files/contracts/task_123/converted.pdf" }
```

### 4.3 存储增量（在 `审核详情页技术设计.md` 基础上）

`audit_result_item` 已有单定位字段（`hit_block_no / hit_page / hit_bbox_x/y/w/h`）= `primary_location`。新增一列承载多块定位：

```sql
ALTER TABLE audit_result_item
  ADD COLUMN hit_locations JSON NULL
  COMMENT '多块定位数组：[{block_no,page,bbox:{x,y,width,height},text,char_start,char_end}]';
```

- 写入：LLM 返回 `hit_block_no[]` → 后端回查 `blocks.json` 组装 `hit_locations` + `primary_location`（取第一块）。
- 读取：`results` 接口直接下发 `primary_location` + `locations`（由 `hit_locations` 解析）。
- 兼容：旧数据 `hit_locations` 为空时，由单 bbox 字段拼出单元素 `locations`。

### 4.4 错误码（与既有一致）

| code | 说明 |
| ---- | ---- |
| 0 | 成功 |
| 40401 | 任务不存在 |
| 42201 | 任务尚未完成（解析/审核未结束） |
| 50001 | 内部错误 |

---

## 五、待与见老师/团队确认项

| 事项 | 待确认 | 建议 |
| ---- | ---- | ---- |
| 位置坐标系 | bbox 用 PDF user space（points，原点左下）✅ 已与详情页方案对齐 | 前端 pdf.js 直接用，确认无需 DPI/翻转换算 |
| 跨块命中 | 一条风险跨多块/多页时是否都要高亮 | 采用 `locations[]` 全量返回，前端逐块高亮 |
| 字符级 span | 是否需要 `char_start/char_end` 精确到字 | 先返回（块内偏移），前端可做块内子高亮 |
| 分类评测数据 | 谁提供各类型脱敏样本、目标规模 | 业务方补样本至 6 类各 ≥ 40 份 |
| 分类上线门槛 | Accuracy/F1/误确认率门槛是否认可 | 暂定 Acc≥0.90、Macro-F1≥0.88、误确认≤0.03 |
| 召回 golden set | 谁标注审核点↔条款真值（含 bbox/page） | 先标 5~10 份做基线，迭代扩充 |

---

## 六、一页结论

1. **合同分类**：关键词预筛 + LLM few-shot + 置信度（方案 D）；类型与审核点解耦，仅用于识别/归档/推荐。评测用「6 类 ≥300 份」数据集，指标含 Accuracy/Macro-F1/混淆矩阵/置信度校准/误确认率，结果表与复现脚本见 §2，数值按协议跑批回填。
2. **条款召回**：审核点驱动 + 混合检索(BM25+Qwen3-Embedding) + Qwen3-Reranker + 立场化研判；底座复用 docling `blocks.json`。
3. **与见老师对齐的输出契约**：每条命中返回 **合同原文(`hit_text`/`locations[].text`) + 位置信息(`bbox`，PDF user space + 字符 span) + PDF 页码(`page`)**，跨块用 `locations[]`，主定位 `primary_location` 兼容旧字段。
4. **API**：新增分类查询/确认接口、召回调试接口，扩展结果接口的定位结构；存储新增 `hit_locations JSON` 列，向后兼容。
