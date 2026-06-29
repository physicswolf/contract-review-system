# 后端配置服务对齐 tmp 规范改造计划书

**项目**：contract-review-system  
**日期**：2026-06-30  
**版本**：v1.0  
**状态**：待开发  
**设计说明书**：`docs/develop/后端配置服务对齐tmp规范改造设计说明书.md`

---

## 一、目标

将本地 FastAPI 后端的配置服务部分（维度、审查点、合同类型）全面对齐 tmp Flask 版本的接口规范，同时增加 AI 引擎内部接口。改造后 tmp 前端代码可零修改直接对接本地后端。

---

## 二、改造范围

| 包含 | 不包含 |
|------|--------|
| DB schema：重建 4 张配置表（dimension/audit_point/contract_type/contract_type_audit_point） | contracts 表（保持不变） |
| 配置 API：请求/响应字段名、响应格式对齐 tmp | auth/files/documents/contracts/points 端点（保持不变） |
| 新增端点：PATCH 启停、PUT 关联、AI 内部接口 | 解析管线、审核引擎 |
| 前端 mock 数据更新 | 前端 UI（已是 tmp 版本，不需改动） |

---

## 三、改造要点

### 3.1 数据库 Schema（以 tmp 为准重建）

| 表 | 变更 |
|----|------|
| `dimension` | `desc` → `description`、`status` VARCHAR → `enabled` TINYINT |
| `audit_point` | `desc` → `description`、`status` VARCHAR → `enabled` TINYINT；JSON 内部字段改为 tmp 格式 |
| `contract_type` | `desc` → `description`、`status` VARCHAR → `enabled` TINYINT；增加 `name`+`stance` 唯一约束；删除 `related_points` 缓存列 |
| `contract_type_audit_point` | 不变 |

**重建方式**：编写新 migration 脚本 `008_rebuild_config_tables.sql`，DROP + CREATE + 重新播种。

### 3.2 请求字段名（以 tmp 为准）

| 当前字段 | tmp 字段 | 适用端点 |
|----------|----------|----------|
| `desc` | `description` | 维度/审查点/合同类型 |
| `status` | `enabled` (0/1) | 维度/审查点/合同类型 |
| `dimension`（名称） | `dimId` (int) | 审查点 |
| `risks` | `riskPoints` | 审查点 |
| `def` | `defaultResult` | 审查点 |

### 3.3 JSON 内部字段（以 tmp 为准）

```json
// risk_points（当前）
[{"title": "xxx", "clauseNote": "", "low": "...", "high": "..."}]

// risk_points（tmp — 改造后）
[{"name": "xxx", "highStd": "...", "lowStd": "...", "noneStd": "..."}]

// default_result（当前）
{"clause": "", "model": "", "overview": "...", "solution": "..."}

// default_result（tmp — 改造后）
{"level": "高风险", "analysis": "...", "suggestion": "..."}

// examples（当前）
[{"clause": "", "model": "", "overview": "...", "solution": "..."}]

// examples（tmp — 改造后）
[{"original": "...", "level": "高风险", "analysis": "...", "suggestion": "..."}]
```

### 3.4 审查点端点（对齐 tmp）

| 端点 | 变更 |
|------|------|
| `GET /api/audit-points` | 保持 `keyword`、`dimId`、`enabled` 参数；返回 `{code:0, data:[{riskPoints:[名称数组], enabled, ...}]}` |
| `POST /api/audit-points` | 请求体字段改为 `dimId`、`description`、`riskPoints`、`defaultResult`、`enabled` |
| `GET /api/audit-points/:id` | 返回 detail 含完整 JSON |
| `PUT /api/audit-points/:id` | 同上字段映射 |
| `PATCH /api/audit-points/:id/enabled` | ✅ 已实现 |
| `DELETE /api/audit-points/:id` | ✅ 已实现 |

### 3.5 合同类型端点（对齐 tmp）

| 端点 | 变更 |
|------|------|
| `GET /api/contract-types` | 增加 `enabled`、`keyword` 参数；返回 `linkedPointCount`（JOIN 实时计算） |
| `GET /api/contract-types/:id` | 返回含 `linkedAuditPoints: [{auditPointId, enabled}]` |
| `POST /api/contract-types` | 请求体 `description`、`enabled`、`name`+`stance` 联合唯一 |
| `PUT /api/contract-types/:id` | 同上 |
| `PUT /api/contract-types/:id/audit-points` | ✅ 已实现 — 全量替换关联 |
| `PATCH /api/contract-types/:id/audit-points/:apid/enabled` | ✅ 已实现 — 类型级启停 |
| `DELETE /api/contract-types/:id` | ✅ 已实现 — 软删除 + 删关联 |

### 3.6 维度端点（对齐 tmp）

| 端点 | 变更 |
|------|------|
| `GET /api/dimensions` | 增加 `enabled` 参数；返回 `{code:0, data:[{description, sortOrder, enabled, ...}]}` |
| `POST /api/dimensions` | 请求体 `description`、`sortOrder`、`enabled` |
| `PUT /api/dimensions/:id` | 同上 |
| `DELETE /api/dimensions/:id` | 保留引用检查 |

### 3.7 AI 引擎内部接口（新增）

| Method | Path | 用途 |
|--------|------|------|
| GET | `/api/internal/contract-types/match?name=&stance=` | 按名称+立场精确匹配合同类型 |
| GET | `/api/internal/contract-types/:id/audit-points` | 加载某合同类型下所有已启用审查点（含完整 JSON 规则） |

**LLM 配置**：在 `.env` 中增加：
```bash
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_API_KEY=ollama
LLM_MODEL_NAME=qwen3:32b
```

当前 v1 阶段 `/internal` 接口返回数据库中的配置数据，不实际调用 LLM。LLM 调用逻辑在后续版本接入。

### 3.8 响应格式统一

配置服务所有端点统一使用 tmp 格式：

```json
// 成功列表
{ "code": 0, "msg": "ok", "data": [...] }

// 成功详情 / 创建返回 ID
{ "code": 0, "msg": "ok", "data": { "id": 1 } }

// 成功操作（无返回数据）
{ "code": 0, "msg": "ok" }

// 错误
{ "code": 40001, "msg": "参数描述" }
{ "code": 40401, "msg": "资源描述" }
{ "code": 40901, "msg": "冲突描述" }
{ "code": 50001, "msg": "内部服务错误" }
```

---

## 四、任务分解

| # | 任务 | 工作量 | 涉及文件 |
|----|------|--------|----------|
| 1 | 数据库 Schema 重建 | 中（~1h） | `008_rebuild_config_tables.sql`、`lifecycle.py` |
| 2 | `audit_point_store.py` 改造 | 大（~2h） | 列名映射 + JSON 字段名映射 + tmp 格式查询方法 |
| 3 | `dimension_store.py` 改造 | 中（~0.5h） | 列名映射 + `enabled` 筛选 |
| 4 | `contract_type_store.py` 改造 | 中（~1h） | 列名映射 + `linkedPointCount` + `linkedAuditPoints` |
| 5 | `api/audit_points.py` 请求字段适配 | 中（~0.5h） | 请求体字段名对齐 |
| 6 | `api/dimensions.py` 完整 tmp 化 | 小（~0.5h） | 请求/返回字段名对齐 |
| 7 | `api/contract_types.py` 完整 tmp 化 | 中（~1h） | 请求/返回字段名对齐 + 关联端点 |
| 8 | `api/internal.py` AI 引擎接口 | 中（~1h） | 新增 2 个端点 + LLM 配置 |
| 9 | `.env` / `config.py` LLM 配置 | 小（~0.25h） | 新增 LLM 相关配置项 |
| 10 | 种子数据 + mock 数据更新 | 中（~0.5h） | JSON 字段名改为 tmp 格式 |
| 11 | `api/adapters.py` / `contracts.py` 适配 | 中（~0.5h） | 审核引擎读取字段名更新 |
| 12 | 前端 mock 数据对齐 | 小（~0.25h） | `mock/db.js` JSON 字段更新 |
| 13 | 集成验证（测试+构建） | 小（~0.5h） | — |
| **合计** | | **~9.5h** | |

---

## 五、风险评估

1. **DB 重建导致数据丢失**：重建会清空现有配置数据，需先导出再导入（或接受开发阶段数据丢失）
2. **`/api/points` 旧端点兼容**：`/api/points`（旧格式）与 `/api/audit-points`（tmp 格式）并存，调用方需明确使用哪个
3. **审核引擎 `_build_audit_items` 依赖 JSON 字段名**：改造后字段名变更，需同步更新
4. **种子数据格式**：旧种子数据 JSON 字段名与新格式不兼容，需全部重写
5. **前端 `point.service.js` 的 `adaptPoint`**：前端的 adapter 已按 tmp 格式编写，后端对齐后前端零修改
