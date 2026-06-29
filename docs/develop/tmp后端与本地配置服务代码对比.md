# tmp 后端与本地配置服务代码对比文档

**日期**：2026-06-29

---

## 一、两套后端概况

| 项目 | tmp 后端 | 本地后端 |
|------|---------|---------|
| 路径 | `~/download/github/tmp/contract-review-system/backend/` | `contract-review-system/backend/src/` |
| 框架 | Flask | FastAPI |
| 服务范围 | **仅配置中心**（维度、审查点、合同类型） | 全栈（配置中心 + 合同管理 + 上传解析 + 审核执行 + 认证） |
| 端口 | 5001 | 8000 |
| DB 连接 | `pymysql` 直连 + `dotenv` | `pymysql` 通过 `db_pool` 单例 + `pydantic-settings` |
| 目录结构 | 扁平：`app.py` + `db.py` + `routes/` | 分层：`main.py` + `api/` + `services/` + `pipelines/` + `db/migrations/` |

---

## 二、整体架构对比

```
┌── tmp 后端 (Flask) ──┐          ┌── 本地后端 (FastAPI) ──┐
│ app.py (入口+路由)     │          │ main.py (入口+路由注册)   │
│ db.py (连接+辅助)      │          │ config.py (配置)          │
│ routes/               │          │ middleware.py (认证)      │
│   dimension.py        │          │ lifecycle.py (启动迁移)   │
│   audit_point.py      │          │ api/                     │
│   contract_type.py    │          │   auth.py                │
│   internal.py (AI引擎) │          │   contracts.py           │
│ init_db.sql (手动执行) │          │   dimensions.py          │
│ .env (手动管理)        │          │   points.py              │
│                        │          │   contract_types.py      │
│                        │          │   files.py / documents.py│
│                        │          │ services/                │
│                        │          │   db_base.py             │
│                        │          │   dimension_store.py     │
│                        │          │   audit_point_store.py   │
│                        │          │   contract_type_store.py │
│                        │          │   contract_store.py ...  │
│                        │          │ db/migrations/ (自动执行) │
└────────────────────────┘          └──────────────────────────┘
```

---

## 三、数据库 Schema 对比

### 3.1 dimension 表

| 列 | tmp | 本地 | 差异 |
|----|-----|------|------|
| 列名-说明 | `description` | `desc` | **不同** |
| 状态 | `enabled` TINYINT (0/1) | `status` VARCHAR ('已启用'/'已停用') | **不同** |
| 排序 | `sort_order` | `sort_order` | 相同 |
| 唯一约束 | `uk_name` | `uk_name` | 相同 |

### 3.2 audit_point 表

| 列 | tmp | 本地 | 差异 |
|----|-----|------|------|
| 列名-说明 | `description` | `desc` | **不同** |
| 状态 | `enabled` TINYINT | `status` VARCHAR | **不同** |
| 其他列 | `name`, `dim_id`, `instruction`, `risk_points`(JSON), `examples`(JSON), `default_result`(JSON), `sort_order`, `deleted_at` | 同 tmp + `category`, `default_checked` | 本地多2列 |

### 3.3 contract_type 表

| 列 | tmp | 本地 | 差异 |
|----|-----|------|------|
| 列名-说明 | `description` | `desc` | **不同** |
| 状态 | `enabled` TINYINT | `status` VARCHAR | **不同** |
| 审查点计数 | JOIN 实时计算 (`linked_point_count`) | `related_points` 缓存列 | 机制不同 |
| 唯一约束 | `uk_name_stance` (name+stance) | 无 | **tmp 有约束** |

### 3.4 contract_type_audit_point 表

两种后端结构一致。

### 3.5 tmp 独有的表

无。本地后端多出 `user`, `contracts`(扩展), `audit_task`, `audit_result_item`, `audit_dimension_stat` — 这些是配置中心之外的功能模块。

---

## 四、API 端点逐项对比

### 4.1 维度 (dimension)

| 操作 | tmp 端点 | 本地端点 | 差异 |
|------|---------|---------|------|
| 列表 | `GET /api/v1/config/dimensions?enabled=` | `GET /api/dimensions` | 参数不同；返回字段不同 |
| 创建 | `POST /api/v1/config/dimensions` | `POST /api/dimensions` | 请求字段名不同 |
| 更新 | `PUT /api/v1/config/dimensions/:id` | `PUT /api/dimensions/:id` | 请求字段名不同 |
| 删除 | `DELETE /api/v1/config/dimensions/:id` | `DELETE /api/dimensions/:id` | 一致 |
| — | — | `GET /api/dimensions/names` | 本地独有 |
| — | — | `GET /api/dimensions/selectable` | 本地独有（tmp用`?enabled=1`代替） |
| — | — | `POST /api/dimensions/relations` | 本地独有（占位） |

**请求字段名差异示例**：

```
tmp POST:   { name, description, sortOrder, enabled }
本地 POST:  { name, desc, sort_order, status }
```

**返回格式差异**：

```
tmp:   { code: 0, msg: "ok", data: [{ id, name, description, sortOrder, enabled, updatedAt }] }
本地:  { items: [{ id, name, desc, sortOrder, status, updatedAt }], total: N }
```

### 4.2 审查点 (audit_point)

| 操作 | tmp 端点 | 本地端点 | 差异 |
|------|---------|---------|------|
| 列表 | `GET /api/v1/config/audit-points?dimId=&keyword=&enabled=` | `GET /api/points?keyword=` | **路径不同**；参数不同；返回不同 |
| 详情 | `GET /api/v1/config/audit-points/:id` | `GET /api/points/:id` | **路径不同** |
| 创建 | `POST /api/v1/config/audit-points` | `POST /api/points` | **路径不同** |
| 更新 | `PUT /api/v1/config/audit-points/:id` | `PUT /api/points/:id` | **路径不同** |
| 启停 | `PATCH /api/v1/config/audit-points/:id/enabled` | **无独立端点** | **tmp 独有**（本地走 PUT 含 status 字段） |
| 删除 | `DELETE /api/v1/config/audit-points/:id` | `DELETE /api/points/:id` | 路径不同 |

**返回字段差异**（列表）：

```
tmp 返回:
{ code: 0, data: [{
    id, name, description, dimId, dimName,
    riskPoints: ["名称1","名称2"],   // ← 名称数组
    enabled: 1, updatedAt
}]}

本地返回:
{ items: [{
    id:"1", name, category, dimension, desc,
    riskPoints: 2,                  // ← JSON_LENGTH 数量
    status:"已启用", updatedAt
}], total: 18 }
```

**JSON 字段名差异**（创建/更新）：

```
tmp POST body:
{ dimId, name, description, instruction,
  riskPoints: [{ name, highStd, lowStd, noneStd }],
  examples: [{ original, level, analysis, suggestion }],
  defaultResult: { level, analysis, suggestion },
  enabled: 1, sortOrder }

本地 POST body:
{ dim_id, name, desc, instruction,
  risks: [{ title, clauseNote, low, high }],
  examples: [{ clause, model, overview, solution }],
  def: { clause, model, overview, solution },
  status: "已启用", sort_order }
```

> **关键**：两种后端对 JSON 列的**内部字段命名完全不同**。tmp 沿用设计文档的 `{name, highStd, lowStd, noneStd}` / `{level, analysis, suggestion}`；本地改为了与前端表单对齐的 `{title, clauseNote, low, high}` / `{clause, model, overview, solution}`。

### 4.3 合同类型 (contract_type)

| 操作 | tmp 端点 | 本地端点 | 差异 |
|------|---------|---------|------|
| 列表 | `GET /api/v1/config/contract-types?enabled=&keyword=` | `GET /api/contract-types?keyword=` | 参数不同 |
| 详情 | `GET /api/v1/config/contract-types/:id` | `GET /api/contract-types/:id` | 返回字段不同 |
| 创建 | `POST /api/v1/config/contract-types` | `POST /api/contract-types` | 请求字段不同；tmp 有唯一约束 |
| 更新 | `PUT /api/v1/config/contract-types/:id` | `PUT /api/contract-types/:id` | 请求字段不同 |
| 删除 | `DELETE /api/v1/config/contract-types/:id` | `DELETE /api/contract-types/:id` | 一致 |
| **关联保存** | `PUT /api/v1/config/contract-types/:id/audit-points` | **缺失** | **本地无此端点** |
| **类型级启停** | `PATCH /api/v1/config/contract-types/:id/audit-points/:apid/enabled` | **缺失** | **本地无此端点** |

**返回字段差异**（列表）：

```
tmp:  { id, code, name, stance, description, keywords, enabled, linkedPointCount }
本地: { id:"1", code, name, stance, desc, keywords, relatedPoints, status:"已启用", updatedAt }
```

**返回字段差异**（详情）：

```
tmp:  { id, ..., keywords, linkedAuditPoints: [{ auditPointId, enabled }] }
本地: { id, ..., pointIds: [1,2,3] }
```

### 4.4 tmp 独有的 AI 引擎内部接口

| Method | Path | 用途 | 本地对应 |
|--------|------|------|----------|
| GET | `/internal/contract-types/match?name=&stance=` | AI 引擎匹配合同类型 | **无**（审核引擎 v1 未接入 LLM） |
| GET | `/internal/contract-types/:id/audit-points` | AI 引擎加载审查点规则 | `GET /contracts/:id/audit` 中内联查询 |

### 4.5 本地独有的端点（配置中心之外）

| Method | Path | 用途 |
|--------|------|------|
| POST | `/api/auth/login` | JWT 登录 |
| GET/PUT | `/api/auth/profile` | 用户信息 |
| POST | `/api/files/upload` | 文件上传解析 |
| GET/PUT | `/api/documents/:id/structure` | 文档结构编辑 |
| GET | `/api/contracts` | 合同列表 |
| POST | `/api/contracts/upload` | 合同上传 |
| POST | `/api/contracts/:id/audit` | 审核执行 |
| GET | `/api/contracts/:id/result` | 审核结果 |

---

## 五、响应格式对比

| 场景 | tmp 格式 | 本地格式 |
|------|---------|---------|
| 成功列表 | `{code:0, msg:"ok", data:[...]}` | `{items:[...], total:N}` |
| 成功详情 | `{code:0, msg:"ok", data:{...}}` | 直接返回对象 `{...}` |
| 成功操作 | `{code:0, msg:"ok"}` / `{code:0, msg:"ok", data:{id:N}}` | `{ok:true}` / `{...}` |
| 参数错误 | `{code:40001, msg:"..."}` | `{"detail":"..."}` |
| 未找到 | `{code:40401, msg:"..."}` | `{"detail":"..."}` |
| 冲突 | `{code:40901, msg:"..."}` | `{"detail":"..."}` |
| 服务错误 | `{code:50001, msg:"内部服务错误"}` | `{"detail":"..."}` |

---

## 六、认证对比

| 项目 | tmp | 本地 |
|------|-----|------|
| 机制 | 占位 dev-token（`/auth/login` 返回固定 `"dev-token"`） | JWT (HS256) + bcrypt 密码验证 |
| 中间件 | 无（CORS after_request） | JWT 验证中间件 + 上传大小守卫 |
| 白名单 | 无（全部开放） | `/health`, `/auth/login`, `/docs`, `/openapi.json` |

---

## 七、差异汇总

### 7.1 tmp 有而本地无

| 差异 | 影响 |
|------|------|
| `PATCH /audit-points/:id/enabled` 独立启停端点 | 前端 `point.service.js` 调用此端点切换状态 |
| `PUT /contract-types/:id/audit-points` 关联全量替换 | 前端 ConfigCenter 分栏布局保存审查点关联 |
| `PATCH /contract-types/:id/audit-points/:apid/enabled` 类型级启停 | 前端在某类型下单独启停审查点 |
| `GET /internal/contract-types/match` | AI 引擎匹配（v1 暂不需要） |
| `GET /internal/contract-types/:id/audit-points` | AI 引擎加载规则（v1 暂不需要） |
| `name`+`stance` 唯一约束 | 防止重复合同类型 |

### 7.2 本地有而 tmp 无

| 差异 | 说明 |
|------|------|
| 完整的认证系统（JWT + bcrypt） | tmp 只是占位 |
| 合同管理、上传解析、审核执行 | 配置中心之外的完整后端 |
| 文档结构编辑 API | 本次新增功能 |
| `GET /dimensions/names` / `GET /dimensions/selectable` | 拆分路径解决冲突（tmp 用 `?enabled=1`） |
| 数据库迁移自动执行 | tmp 需手动执行 `init_db.sql` |

### 7.3 双方都有但实现不同

| 差异 | tmp | 本地 | 对齐方向 |
|------|-----|------|----------|
| API 路径 | `/api/v1/config/audit-points` | `/api/points` | 以 tmp 为准新增路由 |
| 状态类型 | `enabled` TINYINT | `status` VARCHAR 中文 | 需双向转换 |
| 描述列名 | `description` | `desc` | 需双向转换 |
| JSON 内部字段 | `{name,highStd,lowStd,noneStd}` | `{title,clauseNote,low,high}` | 需统一（以 tmp 前端为准） |
| 审查点列表 riskPoints | 名称数组 | 数量 | 以 tmp 为准 |
| 合同类型审查点计数 | JOIN 实时 | 缓存列 | 均可 |
| 响应格式 | `{code:0,data}` | `{items,total}` | tmp 前端 adapter 期望 `{code:0,data}` |

---

## 八、结论

tmp 后端是一套**独立的、专为配置中心设计的 Flask 服务**，与本地 FastAPI 后端在以下层面存在根本性差异：

1. **API 路径不兼容**：`/audit-points` vs `/points`
2. **字段命名不兼容**：DB 列名 (`description` vs `desc`)、JSON 内部字段名、状态值类型
3. **响应格式不兼容**：`{code:0, data}` vs `{items, total}`
4. **功能范围不同**：tmp 仅配置中心，本地覆盖全栈
5. **缺失端点**：关联保存、启停专用、AI 内部接口

**前端以此 tmp 版本为准**，因此本地后端需要新增 tmp 兼容的端点路由（返回 `{code:0, data}` 格式，使用 tmp 的字段名约定），与现有端点并存。
