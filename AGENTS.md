# Codex 开发规范与约束

**项目**：contract-review-system  
**适用对象**：Codex（及后续 AI 开发 Agent）  
**最后更新**：2026-06-29

---

## 1. 项目概述

合同 AI 审核系统，包含：
- `backend/`：FastAPI 后端（Python 3.11+），负责文件上传解析、合同管理、审查点配置、审核执行
- `frontend/`：Vue 3 + Element Plus SPA，负责用户界面

---

## 2. 关键约定（本次会话积累，必须遵守）

### 2.1 目录与包名

- 后端源码目录：`backend/src/`（不是 `app/`）
- 包引用使用 `src.*` 前缀，如 `from src.api.adapters import ...`
- 启动命令：`uvicorn src.main:app`

### 2.2 API 规范

- **前缀**：统一使用 `/api`（不是 `/api/v1`）
- **响应格式**：扁平化，不使用 `{success, data}` 信封
  - 列表：`{items: [], total: N}`
  - 单对象：直接返回对象本身
  - 删除：`{ok: true}`
  - 错误：`{"detail": "错误描述"}` + 对应 HTTP 状态码
- **字段命名**：数据库用 snake_case，返回前端时通过 `api/adapters.py` 转为 camelCase
  - `contract_name` → `name`
  - `party_a` → `partyA`
  - `contract_type` → `type`
  - `review_time` → `updatedAt`
- **状态值**：数据库存中文 `'已启用'` / `'已停用'`（VARCHAR，非 TINYINT），与前端 mock 数据一致

### 2.3 认证

- JWT (HS256)，8 小时过期
- 中间件白名单：`/api/health`, `/api/auth/login`, `/docs`, `/redoc`, `/openapi.json`
- 种子管理员：account=`yilu@company.com`，密码 bcrypt 哈希
- 前端 `http.js` 自动带 `Authorization: Bearer`，401 自动跳 `/login`

### 2.4 数据库

- 数据库名：`aizhiqi`，字符集 `utf8mb4`
- 迁移脚本放在 `src/db/migrations/`，按文件名排序执行
- 迁移在 `lifecycle.py` 启动时自动执行，`CREATE TABLE IF NOT EXISTS` 保证幂等
- 种子数据用 `INSERT IGNORE`
- 状态列用 `VARCHAR(20)` 存中文
- 审查点使用软删除（`deleted_at` 字段）

### 2.5 JSON 列规范

审查点表 (`audit_point`) 有三个 JSON 列，**以前端表单字段名为规范**：

**`risk_points`**：
```json
[{"title": "风险点名称", "clauseNote": "条文说明", "low": "低风险说明", "high": "高风险说明"}]
```

**`default_result`**：
```json
{"clause": "合同原文", "model": "风险模型", "overview": "风险说明", "solution": "修改建议"}
```

**`examples`**：
```json
[{"clause": "合同原文", "model": "风险模型", "overview": "风险说明", "solution": "修改建议"}]
```

### 2.6 结构编辑

- 环境变量 `ENABLE_STRUCTURE_EDITOR` 控制（默认 `false`）
- 为 `true` 时：上传 → 结构编辑页 → 审核设置
- 为 `false` 时：上传 → 直接审核设置
- 前端 `VITE_ENABLE_STRUCTURE_EDITOR` 和后端 `ENABLE_STRUCTURE_EDITOR` 需同时开启

### 2.7 审查点编辑表单

PointEdit.vue 含 5 个数据区域，保存时必须全部提交：
- `name`, `dimension` → DB 标量列
- `note` → DB `instruction`
- `desc` → DB `desc`
- `risks` → DB `risk_points` (JSON)
- `def` → DB `default_result` (JSON)
- `examples` → DB `examples` (JSON)

编辑加载时需从后端响应恢复全部字段。

### 2.8 解析管线保护

以下模块的解析逻辑**不可修改**（只能修改 API 层的响应格式）：
- `services/document_parser.py`
- `services/contract_structure_parser.py`
- `services/pdf_contract_parser.py`
- `services/python_docx_contract_parser.py`
- `services/file_storage.py`
- `pipelines/document_upload.py`
- `pipelines/document_tasks.py`

### 2.9 审核引擎

- v1 阶段使用降级方案：读取审查点的 `default_result` 和 `risk_points` 生成结果，不调用真实 LLM
- 审核结果需匹配 `frontend/src/api/mock/db.js` 中 `buildAuditResult()` 的返回结构

### 2.10 Mock 模式

- 前端 `VITE_USE_MOCK=true` 使用 mock 数据，`false` 连接真实后端
- 默认 `false`
- `mock/db.js` 是 API 数据契约的参考，不可修改

---

## 3. 目录结构

```
contract-review-system/
├── AGENTS.md                    ← 本文件
├── docs/
│   ├── planning/                ← Claude Code 编写的计划书
│   │   ├── 后端迁移与API适配计划书.md
│   │   └── 审查点编辑表单对接计划书.md
│   ├── develop/                 ← Claude Code 编写的设计说明书
│   │   ├── 后端迁移与API适配设计说明书.md
│   │   └── 审查点编辑表单-前后端数据对接设计.md
│   └── review/                  ← Claude Code 的评审意见
├── .status/
│   └── codex-status.md          ← Codex 运行状态记录
├── backend/
│   └── src/                     ← 后端源码
│       ├── main.py
│       ├── config.py
│       ├── middleware.py
│       ├── lifecycle.py
│       ├── api/                 ← 路由层
│       ├── services/            ← 业务逻辑 + Repository
│       ├── pipelines/           ← 上传管线
│       └── db/migrations/       ← SQL 迁移
└── frontend/
    └── src/                     ← 前端源码
        ├── api/                 ← axios + mock
        ├── services/            ← API 调用封装
        ├── views/               ← 页面组件
        ├── components/          ← 通用组件
        ├── stores/              ← 状态管理
        └── router/              ← 路由
```

---

## 4. 数据库表清单

| 表名 | 用途 | 状态 |
|------|------|------|
| `contracts` | 合同记录（已有，含 risk/risk_count/risk_level 扩展列） | 已存在 |
| `user` | 系统用户 | 新建 |
| `dimension` | 审查维度 | 新建 |
| `audit_point` | 审查点（含 JSON 列） | 新建 |
| `contract_type` | 合同类型 | 新建 |
| `contract_type_audit_point` | 合同类型-审查点关联 | 新建 |
| `audit_task` | 审核任务 | 新建 |
| `audit_result_item` | 审核结果条目 | 新建 |
| `audit_dimension_stat` | 审核维度统计 | 新建 |

---

## 5. API 路由一览

前缀统一为 `/api`。

| 前缀 | 模块 | 主要端点 |
|------|------|----------|
| `/api` | health | `GET /health` |
| `/api/auth` | auth | `POST /login`, `GET/PUT /profile` |
| `/api/files` | files | `POST /upload`, `GET /tasks/{id}`, `GET /{id}` |
| `/api/documents` | documents | `GET /{fileId}`, `GET /{fileId}/structure`, `PUT /{fileId}/structure` |
| `/api/contracts` | contracts | `GET`, `POST /upload`, `POST /{id}/audit`, `GET /{id}/result`, `DELETE /{id}` |
| `/api/points` | points | CRUD 审查点 |
| `/api/dimensions` | dimensions | CRUD + `/names` + `/selectable` + `/relations` |
| `/api/contract-types` | contract_types | CRUD 合同类型 |
| `/api/review` | review | `GET /purposes` |

---

## 6. 开发规范

### 6.1 通用规则

1. 保持变更小而清晰
2. 不覆盖已有计划书、设计说明书、评审意见、状态记录
3. 每步操作追加到 `.status/codex-status.md`
4. 修改文件前先 Read 确认当前内容
5. 后端代码放 `backend/`，前端放 `frontend/`

### 6.2 Python 后端

1. FastAPI 路由用 APIRouter，`main.py` 统一注册
2. 数据库操作用 Repository 模式（参考 `services/contract_store.py`）
3. 响应用 `api/responses.py` 的 `flat_list()`, `flat_object()`, `ok_deleted()`, `error_response()`
4. 字段映射用 `api/adapters.py`
5. 错误响应：`{"detail": "描述"}` + HTTP 状态码
6. 环境变量：`pydantic-settings`，`.env` 在 `backend/` 根

### 6.3 Vue 前端

1. 页面放 `src/views/`，组件放 `src/components/`，API 调用放 `src/services/`
2. axios 实例：`src/api/http.js`（自动注入 token + 401 跳转）
3. 状态用 Vue reactive（`src/stores/`），不用 Pinia
4. UI 库：Element Plus（按需导入）
5. Mock 通过 `VITE_USE_MOCK` 环境变量控制

---

## 7. 禁止事项

1. ❌ 不要修改 `docs/planning/` 和 `docs/develop/` 中的现有文档
2. ❌ 不要修改解析管线代码（`services/document_parser.py` 等）
3. ❌ 不要修改 `frontend/src/api/mock/db.js`
4. ❌ 不要在项目根目录创建源码文件
5. ❌ 不要使用 `{success, data}` 信封格式
6. ❌ 不要硬编码数据库密码
7. ❌ 不要修改 JSON 列的内部字段命名规范
