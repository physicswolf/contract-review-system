# 后端迁移与 API 适配计划书

**项目**：contract-review-system  
**阶段**：后端迁移 + 前端 API 对接  
**日期**：2026-06-29  
**版本**：v1.0  
**状态**：待开发

---

## 一、目标与范围

### 1.1 目标

将 `/home/wolfsoft/my_code/contract/homepage/backend` 中已有的 FastAPI 后端代码迁移至 `contract-review-system/backend`，并使其全部 API 与 `contract-review-system/frontend` 中的 Vue 3 SPA 前端完全对接。迁移完成后，前端关闭 Mock 模式即可直接与真实后端通信。

### 1.2 范围

| 包含 | 不包含 |
|------|--------|
| 现有代码迁移（文件上传、文档解析、合同 CRUD、结构编辑） | 新功能开发 |
| API 适配（前缀、响应格式、字段映射） | LLM 审查引擎完整实现 |
| 新增模块（认证、审查点、维度、合同类型、审核执行/结果） | CI/CD 部署 |
| 数据库表扩展与种子数据 | — |
| 结构编辑可选化（环境变量控制） | — |

### 1.3 前置依赖

- 现有后端代码位于 `/home/wolfsoft/my_code/contract/homepage/backend/`
- 前端代码位于 `contract-review-system/frontend/`，当前以 `USE_MOCK=true` 运行
- 目标 MySQL 数据库 `aizhiqi` 需可访问

---

## 二、现有资产梳理

### 2.1 后端已有能力

| 模块 | 端点 | 状态 | 说明 |
|------|------|------|------|
| 文件上传 | `POST /api/v1/files/upload` | ✅ 完成 | 安全校验、原子落盘、格式签名验证 |
| 解析任务 | `GET /api/v1/files/tasks/{id}` | ✅ 完成 | 异步线程池解析，状态轮询 |
| 文档结构 | `GET /api/v1/documents/{id}` | ✅ 完成 | 读取 document.json 概要 |
| 章节树 | `GET/PUT /api/v1/documents/{id}/structure` | ✅ 完成 | 读取/编辑合同章节树 |
| 合同 CRUD | `GET/POST/PUT/DELETE /api/v1/contracts` | ✅ 完成 | MySQL 存储，模糊搜索 |
| 结构编辑器 | `GET /editor/{id}` | ✅ 完成 | 服务端渲染的编辑器页面 |
| 健康检查 | `GET /api/v1/health` | ✅ 完成 | |

### 2.2 后端解析管线（核心，需完全保留）

```
文件上传 → file_storage.py（校验+落盘）
         → document_upload.py（编排）
         → document_tasks.py（异步任务队列）
           → document_parser.py（引擎路由）
             ├─ python-docx → python_docx_contract_parser.py
             ├─ docling → LibreOffice 转 PDF → Docling 解析
             └─ pymupdf4llm → pdf_contract_parser.py
           → contract_structure_parser.py（统一章节树构建）
         → contract_extractor.py（元信息抽取）
         → contract_store.py（MySQL 入库）
```

### 2.3 前端期望的 API

| 服务文件 | API 路径 | 方法 | 请求/响应格式 |
|----------|----------|------|---------------|
| auth.service.js | `/auth/login` | POST | `{account,password}` → `{token,user}` |
| auth.service.js | `/auth/profile` | GET | → user 对象 |
| auth.service.js | `/auth/profile` | PUT | partial user → 完整 user |
| contract.service.js | `/contracts` | GET | `?name=&partyA=&partyB=` → `{items,total}` |
| contract.service.js | `/contracts/upload` | POST | multipart `file` → `{id,name,detectedType,matchConfidence}` |
| contract.service.js | `/contracts/:id/audit` | POST | `{role,points}` → `{id,status}` |
| contract.service.js | `/contracts/:id/result` | GET | → AuditResult 对象 |
| contract.service.js | `/contracts/:id` | DELETE | → `{ok:true}` |
| point.service.js | `/points` | GET | `?keyword=` → `{items,total}` |
| point.service.js | `/points/:id` | GET | → point 对象 |
| point.service.js | `/points` | POST/PUT | point payload → point 对象 |
| point.service.js | `/points/:id` | DELETE | → `{ok:true}` |
| point.service.js | `/dimensions` | GET | → `["基础核查","法务风险",...]` 字符串数组 |
| dimension.service.js | `/dimensions` | GET | → `{items,total}` |
| dimension.service.js | `/dimensions` | POST/PUT | → dimension 对象 |
| dimension.service.js | `/dimensions/:id` | DELETE | → `{ok:true}` |
| dimension.service.js | `/dimensions/selectable` | GET | → `[{name,desc}]` |
| dimension.service.js | `/dimensions/relations` | POST | → `{ok:true}` |
| type.service.js | `/contract-types` | GET | `?keyword=` → `{items,total}` |
| type.service.js | `/contract-types/:id` | GET | → type 对象 |
| type.service.js | `/contract-types` | POST/PUT | → type 对象 |
| type.service.js | `/contract-types/:id` | DELETE | → `{ok:true}` |

---

## 三、核心差异与适配方案

### 3.1 API 前缀

| 项目 | 值 |
|------|-----|
| 前端期望 | `/api`（来自 `config.js: API_BASE = '/api'`） |
| 后端现有 | `/api/v1`（来自 `config.py: api_prefix = "/api/v1"`） |
| **方案** | **改为 `/api`**，删除 compat 兼容路由 |

### 3.2 响应格式

前端 service 层直接对 `http.get/post/put/delete` 的 `data` 进行解构（如 `const { items } = await listContracts()`），不接受嵌套信封。

| 场景 | 后端现有格式 | 前端期望格式 |
|------|-------------|-------------|
| 列表 | `{success:true, data:{contracts:[], total:N}}` | `{items:[], total:N}` |
| 详情 | `{success:true, data:{contract:{...}}}` | 直接返回对象 |
| 删除 | `{success:true, message:"已删除"}` | `{ok:true}` |

**方案**：在 `api/responses.py` 增加扁平化适配函数，所有端点直接返回前端期望格式。

### 3.3 字段命名

| 后端（snake_case） | 前端（camelCase） |
|---------------------|-------------------|
| `contract_name` | `name` |
| `party_a` | `partyA` |
| `party_b` | `partyB` |
| `contract_type` | `type` |
| `review_time` | `updatedAt` |

**方案**：创建 `api/adapters.py`，提供 `contract_to_frontend()` 等映射函数。

### 3.4 维度路径冲突

`point.service.js` 调用 `GET /dimensions` 期望返回字符串数组。  
`dimension.service.js` 也调用 `GET /dimensions` 但期望返回 `{items:[], total:N}`。

**方案**：`point.service.js` 改为 `GET /dimensions/names`，后端分离两个端点。

---

## 四、结构编辑可选化方案

### 4.1 配置

```bash
# .env
ENABLE_STRUCTURE_EDITOR=true   # 启用（上传后跳转结构编辑页）
ENABLE_STRUCTURE_EDITOR=false  # 关闭（上传后直接进审核设置，默认值）
```

### 4.2 前后端交互

1. `POST /api/contracts/upload` 返回 `{ id, name, detectedType, matchConfidence, fileId, enableStructureEditor }`
2. 前端根据 `enableStructureEditor` 决定：`true` → `/editor/{fileId}`；`false` → 审核设置 Step2
3. 保留 `api/documents.py` 的结构读取/保存端点

---

## 五、数据库设计

### 5.1 新增表（8 张）

- **`user`** — 系统用户（account, password/bcrypt, name, company, role, phone, email）
- **`dimension`** — 审查维度（name, desc, sort_order, status）
- **`audit_point`** — 审查点（dim_id, name, category, desc, instruction, risk_points/JSON, examples/JSON, default_result/JSON, default_checked, status, deleted_at）
- **`contract_type`** — 合同类型（code, name, stance, desc, keywords/JSON, related_points, status, deleted_at）
- **`contract_type_audit_point`** — 合同类型-审查点关联
- **`audit_task`** — 审核任务（contract_id, stance, status, risk counts）
- **`audit_result_item`** — 审核结果条目（task_id, dim_id, title, risk_level, risk_summary 等）
- **`audit_dimension_stat`** — 审核维度统计（task_id, dim_id, total/major/general counts）

### 5.2 扩展 contracts 表

新增列：`risk`、`risk_count`、`risk_level`（审核摘要缓存）。

### 5.3 种子数据

从 `frontend/src/api/mock/db.js` 提取：1 个管理员、5 个维度、18 个审查点、6 个合同类型。

---

## 六、任务分解

### 任务 1：代码迁移与目录重构
- **产出**：`contract-review-system/backend/` 完整目录结构
- **工作量**：中
- **依赖**：无

1. 复制现有 `app/` 全部代码到目标目录
2. 创建 `api/adapters.py`、`api/auth.py`、`api/points.py`、`api/dimensions.py`、`api/contract_types.py`、`api/audit.py`
3. 创建 `services/db_base.py`、`services/auth_service.py`、`services/dimension_store.py`、`services/audit_point_store.py`、`services/contract_type_store.py`、`services/audit_result_store.py`
4. 创建 `db/migrations/` 目录下的 SQL 脚本
5. 删除 `api/compat.py`、`api/web.py`

### 任务 2：数据库迁移
- **产出**：6 张新表 + 1 张扩展表 + 种子数据
- **工作量**：小
- **依赖**：任务 1

1. 编写 `001_create_auth_tables.sql`
2. 编写 `002_create_config_tables.sql`
3. 编写 `003_create_audit_tables.sql`
4. 编写 `004_seed_default_data.sql`
5. 编写 `005_extend_contracts_table.sql`
6. 在 `lifecycle.py` 中添加自动迁移执行

### 任务 3：config.py 修改
- **产出**：更新后的配置文件
- **工作量**：小
- **依赖**：任务 1

1. `api_prefix` 改为 `/api`
2. 增加 JWT 配置（`jwt_secret_key`, `jwt_algorithm`, `jwt_expire_minutes`）
3. 增加 `enable_structure_editor: bool = False`

### 任务 4：API 适配层
- **产出**：`api/adapters.py` + `api/responses.py` 修改
- **工作量**：小

1. 字段映射函数（contract、point、dimension 等）
2. 扁平化响应辅助函数（`flat_list`, `ok_deleted`, `flat_object`）

### 任务 5：认证模块
- **产出**：`api/auth.py` + `services/auth_service.py` + JWT 中间件
- **工作量**：中
- **依赖**：任务 3、4

1. 用户登录（bcrypt 验证 + JWT 签发）
2. 用户信息读取/修改
3. JWT 中间件注入（白名单：`/health`, `/auth/login`）
4. 种子管理员用户

### 任务 6：配置中心 API
- **产出**：`api/points.py` + `api/dimensions.py` + `api/contract_types.py` + 对应 Repository
- **工作量**：大
- **依赖**：任务 2、4

1. 审查点 CRUD（列表/详情/创建/更新/软删除、启停切换）
2. 维度 CRUD（列表/名称列表/可选维度/创建/更新/删除/关联保存）
3. 合同类型 CRUD（列表/详情/创建/更新/删除）
4. 所有端点返回前端期望的扁平格式

### 任务 7：合同 API 适配与上传端点
- **产出**：`api/contracts.py` 重构
- **工作量**：中
- **依赖**：任务 4

1. 列表接口：`contract_to_frontend` 映射 + 审核统计填充
2. 上传接口：`POST /contracts/upload` 包装解析管线 + 返回前端格式
3. 上传响应中包含 `enableStructureEditor` 字段
4. 删除接口：返回 `{ok:true}`

### 任务 8：审核执行与结果 API
- **产出**：`api/contracts.py` 增加审核端点
- **工作量**：中
- **依赖**：任务 7

1. `POST /contracts/:id/audit`：接收 `{role, points}` → 创建审核任务 → 生成结果 → 返回 `{id, status}`
2. `GET /contracts/:id/result`：返回匹配 `mock/db.js buildAuditResult()` 结构的审核结果
3. v1 阶段使用基于配置规则的降级方案（读取审查点的 `default_result`，不调用 LLM）

### 任务 9：main.py 整合
- **产出**：更新后的 `main.py`
- **工作量**：小
- **依赖**：任务 1-8

1. 注册所有新路由
2. 移除 web_router、compat_router、StaticFiles
3. 入口文件更新

### 任务 10：前端适配
- **产出**：`config.js` 变更 + `point.service.js` 路径修复
- **工作量**：极小

1. `USE_MOCK` 改为环境变量控制（默认 false）
2. `point.service.js` 中 `GET /dimensions` 改为 `GET /dimensions/names`
3. 环境变量 `VITE_ENABLE_STRUCTURE_EDITOR` 控制是否跳转结构编辑

### 任务 11：AGENTS.md 编写
- **产出**：`contract-review-system/AGENTS.md`
- **工作量**：小

---

## 七、完整 API 路由表

### 系统
| Method | Path | Auth | 说明 |
|--------|------|------|------|
| GET | `/api/health` | No | 健康检查 |

### 认证
| Method | Path | Auth | 请求 | 响应 |
|--------|------|------|------|------|
| POST | `/api/auth/login` | No | `{account, password}` | `{token, user}` |
| GET | `/api/auth/profile` | Yes | - | 用户对象 |
| PUT | `/api/auth/profile` | Yes | partial user | 更新后对象 |

### 合同管理
| Method | Path | Auth | 请求 | 响应 |
|--------|------|------|------|------|
| GET | `/api/contracts` | Yes | `?name=&partyA=&partyB=` | `{items, total}` |
| POST | `/api/contracts/upload` | Yes | multipart `file` | `{id, name, detectedType, matchConfidence, fileId, enableStructureEditor}` |
| POST | `/api/contracts/:id/audit` | Yes | `{role, points}` | `{id, status}` |
| GET | `/api/contracts/:id/result` | Yes | - | AuditResult |
| DELETE | `/api/contracts/:id` | Yes | - | `{ok:true}` |

### 审查点
| Method | Path | Auth | 响应 |
|--------|------|------|------|
| GET | `/api/points` | Yes | `{items, total}` |
| GET | `/api/points/:id` | Yes | 审查点详情 |
| POST | `/api/points` | Yes | 创建的审查点 |
| PUT | `/api/points/:id` | Yes | 更新后的审查点 |
| DELETE | `/api/points/:id` | Yes | `{ok:true}` |

### 审查维度
| Method | Path | Auth | 响应 |
|--------|------|------|------|
| GET | `/api/dimensions` | Yes | `{items, total}` |
| GET | `/api/dimensions/names` | Yes | `["基础核查","法务风险",...]` |
| GET | `/api/dimensions/selectable` | Yes | `[{name, desc}]` |
| POST | `/api/dimensions` | Yes | 创建的维度 |
| PUT | `/api/dimensions/:id` | Yes | 更新后的维度 |
| DELETE | `/api/dimensions/:id` | Yes | `{ok:true}` |
| POST | `/api/dimensions/relations` | Yes | `{ok:true}` |

### 合同类型
| Method | Path | Auth | 响应 |
|--------|------|------|------|
| GET | `/api/contract-types` | Yes | `{items, total}` |
| GET | `/api/contract-types/:id` | Yes | 合同类型详情 |
| POST | `/api/contract-types` | Yes | 创建的类型 |
| PUT | `/api/contract-types/:id` | Yes | 更新后的类型 |
| DELETE | `/api/contract-types/:id` | Yes | `{ok:true}` |

### 文件服务（内部使用）
| Method | Path | Auth | 说明 |
|--------|------|------|------|
| POST | `/api/files/upload` | Yes | 原始上传管线入口 |
| GET | `/api/files/tasks/:id` | Yes | 解析任务状态 |
| GET | `/api/files/:id` | Yes | 文件元信息 |

### 文档结构（结构编辑用）
| Method | Path | Auth | 说明 |
|--------|------|------|------|
| GET | `/api/documents/:fileId` | Yes | 文档信息 |
| GET | `/api/documents/:fileId/structure` | Yes | 章节树 |
| PUT | `/api/documents/:fileId/structure` | Yes | 保存章节树 |

---

## 八、里程碑与工作量估算

| 阶段 | 任务 | 预估工作量 | 产出 |
|------|------|-----------|------|
| 1 | 代码迁移 + 目录重构 | 中（~1h） | 完整目录结构 |
| 2 | 数据库迁移脚本 | 小（~0.5h） | SQL 文件 |
| 3 | config.py 修改 | 小（~0.25h） | 更新后配置 |
| 4 | API 适配层 | 小（~0.5h） | adapters.py |
| 5 | 认证模块 | 中（~1h） | JWT + login API |
| 6 | 配置中心 API | 大（~2h） | points/dimensions/types CRUD |
| 7 | 合同 API 适配 | 中（~1h） | 适配后 contracts API |
| 8 | 审核执行/结果 API | 中（~1h） | audit API |
| 9 | main.py 整合 | 小（~0.5h） | 最终 main.py |
| 10 | 前端适配 | 极小（~0.25h） | config.js 修改 |
| 11 | AGENTS.md | 小（~0.5h） | 开发规范文档 |
| **合计** | | **~8h** | |

---

## 九、风险与注意事项

1. **解析管线稳定性**：迁移过程中不修改 `services/` 和 `pipelines/` 中的解析逻辑
2. **MySQL 连接**：迁移脚本使用 `CREATE TABLE IF NOT EXISTS`，确保幂等执行
3. **种子数据不可重复插入**：使用 `INSERT IGNORE`
4. **审核引擎降级**：v1 不接入真实 LLM，使用审查点配置的 `default_result` 生成结果
5. **结构编辑前端页面**：需后续迭代实现 Vue 组件
6. **密码安全**：种子管理员密码 bcrypt 哈希，JWT secret 通过环境变量配置
