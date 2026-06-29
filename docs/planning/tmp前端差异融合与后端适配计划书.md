# tmp 前端差异融合与后端适配计划书

**项目**：contract-review-system  
**日期**：2026-06-29  
**版本**：v1.0  
**状态**：待开发  
**设计说明书**：`docs/develop/tmp前端差异融合与后端适配设计说明书.md`

---

## 一、背景

对比 `~/download/github/tmp/contract-review-system/frontend`（下称 **tmp**）与当前 `frontend/`，识别出：

- **本次新增代码**（2 个文件，workspace 独有，必须保留）：`StructureEditor.vue`、`document.service.js`
- **差异文件**（13 个文件，以 tmp 版本为准融合）：涉及 config、service、view、router、store、component
- **无差异文件**：`Login.vue`、`Profile.vue`、`AuditResult.vue`、`ContractList.vue`、`StepUpload.vue`、`StepSetup.vue`、`mock/db.js`、`mock/delay.js`、`App.vue`、`main.js` 等 — 不需要变更

---

## 二、融合原则

1. **tmp 版本为准**：除本次新增代码外，差异文件以 tmp 版本覆盖
2. **后端适配前端**：前端 service 层的 API 调用模式不变，后端新增/修改端点以匹配
3. **保留本次新增**：StructureEditor.vue、document.service.js、结构编辑流程、ENABLE_STRUCTURE_EDITOR 开关
4. **API_BASE 不变**：保持 `/api`（当前 Vite proxy 配置）

---

## 三、前端融合清单

### 3.1 直接覆盖（不修改后端）

| 文件 | tmp 差异 | 融合动作 |
|------|----------|----------|
| `http.js` | `data.msg \|\| data.detail` | 直接覆盖 |
| `auth.service.js` | tmp 用 `data.data` 解构 | 直接覆盖（后端 `/auth/profile` 返回直接对象，`data.data` 为 undefined → 降级返回 `data`） |
| `AppSidebar.vue` | tmp 无 `structureEditor` 高亮 | 覆盖后补回 structureEditor 高亮 |
| `stores/review.js` | tmp 无 `fileId` 字段 | 覆盖后补回 fileId 字段 |

### 3.2 覆盖 + 后端适配

| 文件 | tmp 差异 | 需要的后端变更 |
|------|----------|---------------|
| `config.js` | `USE_MOCK=false`, `API_BASE='/api/v1/config'` | 无需（保留当前的 API_BASE 和 USE_MOCK 环境变量，追加 `ENABLE_STRUCTURE_EDITOR`） |
| `point.service.js` | 调用 `/audit-points`，`adaptPoint()` 适配，PATCH 启停 | 新增 `/api/audit-points` 路由 + `PATCH /api/audit-points/:id/enabled` |
| `dimension.service.js` | `adapt()` 适配，`?enabled=1` 查可选 | 修改 `/api/dimensions` 支持 `status` 参数，返回字段匹配 adapter |
| `type.service.js` | `adaptType()` 适配，`saveAuditPoints()` | 新增 `PUT /api/contract-types/:id/audit-points` |
| `contract.service.js` | mock 中生成 `fileId` + `enableStructureEditor` | 后端已返回这些字段，mock 数据对齐即可 |
| `ConfigCenter.vue` | 合同类型 Tab 分栏布局 | 需要后端返回 `linkedAuditPoints`、`sortOrder` 等字段 |
| `PointEdit.vue` | `dimId`、`noneStd`、`level` 选择器 | 后端返回字段需匹配 `adaptPoint(detail)` 的映射 |
| `ReviewWizard.vue` | 无结构编辑流程 | 覆盖后补回结构编辑跳转 + resume 流程 |
| `router/index.js` | 无 `structureEditor` 路由 | 覆盖后补回 structureEditor 路由 |

---

## 四、后端变更清单

### 4.1 新增路由 `/api/audit-points`

> 对应 tmp `point.service.js` 的 `/audit-points` 调用

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/audit-points` | 查询参数 `keyword`, `dimId`, `enabled`(TINYINT) |
| POST | `/api/audit-points` | 创建 |
| GET | `/api/audit-points/:id` | 详情 |
| PUT | `/api/audit-points/:id` | 更新 |
| PATCH | `/api/audit-points/:id/enabled` | 启停（body: `{enabled: 0\|1}`） |
| DELETE | `/api/audit-points/:id` | 软删除 |

响应格式（匹配 tmp adapter 期望）：

```json
// 列表
{ "code": 0, "msg": "ok", "data": [{ "id": 1, "name": "...", "description": "...", "dimId": 1, "dimName": "基础核查", "riskPoints": ["名称1","名称2"], "enabled": 1, "updatedAt": "2026-06-29", ... }] }

// 详情
{ "code": 0, "msg": "ok", "data": { "id": 1, ..., "riskPoints": [{...}], "examples": [{...}], "defaultResult": {...} } }
```

### 4.2 修改现有 `/api/dimensions`

增加 `enabled` 查询参数（TINYINT），返回字段增加 `sortOrder`、`description`（别名）。

```json
{ "code": 0, "msg": "ok", "data": [{ "id": 1, "name": "基础核查", "description": "...", "sortOrder": 10, "enabled": 1, "updatedAt": "..." }] }
```

### 4.3 修改现有 `/api/contract-types`

增加 `enabled`、`keyword` 查询参数，返回字段增加 `description`（别名）、`linkedPointCount`。

详情增加 `linkedAuditPoints: [{auditPointId, enabled}]`。

```json
// 列表
{ "code": 0, "msg": "ok", "data": [{ "id": 1, "code": "PURCHASE", "name": "采购合同", "stance": "甲方立场", "description": "...", "enabled": 1, "linkedPointCount": 3 }] }

// 详情
{ "code": 0, "msg": "ok", "data": { "id": 1, ..., "linkedAuditPoints": [{"auditPointId":1,"enabled":1}, ...] } }
```

### 4.4 新增端点

| Method | Path | 说明 |
|--------|------|------|
| PUT | `/api/contract-types/:id/audit-points` | 全量替换关联，body: `{auditPointIds: [1,2,3]}` |
| PATCH | `/api/contract-types/:id/audit-points/:apid/enabled` | 类型级启停，body: `{enabled: 0\|1}` |

### 4.5 config.js 保留的本次新增项

```javascript
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'
export const ENABLE_STRUCTURE_EDITOR = import.meta.env.VITE_ENABLE_STRUCTURE_EDITOR === 'true'
```

---

## 五、任务分解

| # | 任务 | 工作量 | 涉及文件 |
|----|------|--------|----------|
| 1 | 前端 13 个差异文件以 tmp 覆盖 + 补回本次新增代码 | 大（~3h） | 13 个差异文件 |
| 2 | 后端新增 `/api/audit-points` 路由 | 大（~2h） | `api/audit_points.py`, `services/audit_point_store.py` |
| 3 | 后端修改 `/api/dimensions` 适配 tmp | 小（~0.5h） | `api/dimensions.py`, `services/dimension_store.py` |
| 4 | 后端修改 `/api/contract-types` 适配 tmp | 中（~1h） | `api/contract_types.py`, `services/contract_type_store.py` |
| 5 | 后端新增关联端点 | 小（~0.5h） | `api/contract_types.py`, `services/contract_type_store.py` |
| 6 | 集成验证（测试+构建） | 小（~0.5h） | — |
| **合计** | | **~7.5h** | |

---

## 六、不融合的内容

| 内容 | 说明 |
|------|------|
| tmp 的 Flask 后端（`app.py`/`db.py`/`routes/`） | 我们已有完整的 FastAPI 后端 |
| tmp 的 `API_BASE = '/api/v1/config'` | 我们使用 `/api` 前缀 |
| tmp 的 `init_db.sql` | 我们的 migration 脚本更完整 |
| tmp 的硬编码 `USE_MOCK = false` | 我们改为环境变量控制 |
