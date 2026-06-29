# 后端迁移与 API 适配设计说明书

**项目**：contract-review-system  
**文档类型**：设计说明书  
**日期**：2026-06-29  
**版本**：v1.0

---

## 一、概述

本文档是《后端迁移与 API 适配计划书》的设计说明部分，描述具体的实现方案、代码结构、文件清单、数据库 DDL 和 API 契约。开发人员应依据本文档完成编码工作，无需再参考其他设计来源。

### 1.1 关键设计决策

| 决策项 | 选择 | 原因 |
|--------|------|------|
| API 前缀 | `/api` | 与前端 Vite proxy 一致 |
| 响应格式 | 扁平化（去掉 `success/data` 信封） | 前端 service 层直接解构 `data` 字段 |
| 状态字段 | `VARCHAR(20)` 存储中文（`'已启用'/'已停用'`） | 与前端 mock 数据一致，无需翻译层 |
| 审核引擎 | v1 降级方案（基于配置规则，不调 LLM） | 先打通前后端闭环，LLM 引擎后续迭代 |
| 结构编辑 | 环境变量 `ENABLE_STRUCTURE_EDITOR` 控制 | 按用户要求设为可选项 |
| 数据库迁移 | 启动时自动执行，`IF NOT EXISTS` 幂等 | 开发阶段简化部署 |
| 认证方案 | JWT (HS256)，8 小时过期 | 轻量，无需外部服务 |

---

## 二、目录结构

迁移完成后的 `contract-review-system/backend/` 目录结构：

```
backend/
├── pyproject.toml
├── uv.lock
├── .env
├── .env.example
├── resolve.py
├── storage/
│   ├── uploads/.gitkeep
│   └── parsing/.gitkeep
├── tests/
│   └── (existing tests preserved)
└── app/
    ├── __init__.py
    ├── main.py              # [修改] 路由注册重构
    ├── config.py             # [修改] prefix + JWT 配置
    ├── schemas.py            # [修改] 扩展 schema
    ├── middleware.py          # [修改] 新增 JWT 中间件
    ├── lifecycle.py          # [修改] 新增迁移自动执行
    ├── exception_handlers.py # [保留]
    ├── api/
    │   ├── __init__.py
    │   ├── responses.py      # [修改] 新增扁平化适配器
    │   ├── adapters.py       # [新增] 字段映射函数
    │   ├── health.py         # [修改] 响应格式
    │   ├── files.py          # [修改] 响应格式
    │   ├── documents.py      # [保留] 结构编辑用
    │   ├── contracts.py      # [修改] 适配 + 新增 /upload + /audit 端点
    │   ├── review.py         # [保留]
    │   ├── auth.py           # [新增] 认证模块
    │   ├── points.py         # [新增] 审查点 CRUD
    │   ├── dimensions.py     # [新增] 维度 CRUD
    │   ├── contract_types.py # [新增] 合同类型 CRUD
    │   └── audit.py          # [新增] 审核执行/结果
    ├── services/
    │   ├── __init__.py
    │   ├── db_base.py               # [新增] 共享连接池
    │   ├── auth_service.py           # [新增] JWT + 用户管理
    │   ├── dimension_store.py        # [新增] 维度仓库
    │   ├── audit_point_store.py      # [新增] 审查点仓库
    │   ├── contract_type_store.py    # [新增] 合同类型仓库
    │   ├── audit_result_store.py     # [新增] 审核结果仓库
    │   ├── contract_store.py         # [修改] 连接池改造 + 表扩展
    │   ├── file_storage.py           # [保留]
    │   ├── document_parser.py        # [保留]
    │   ├── contract_structure_parser.py  # [保留]
    │   ├── pdf_contract_parser.py    # [保留]
    │   ├── python_docx_contract_parser.py # [保留]
    │   ├── contract_extractor.py     # [保留]
    │   └── structure_editor.py       # [保留]
    ├── pipelines/
    │   ├── __init__.py
    │   ├── document_upload.py        # [保留]
    │   └── document_tasks.py         # [保留]
    └── db/
        └── migrations/
            ├── 001_create_auth_tables.sql
            ├── 002_create_config_tables.sql
            ├── 003_create_audit_tables.sql
            ├── 004_seed_default_data.sql
            └── 005_extend_contracts_table.sql
```

---

## 三、config.py 修改

```python
# 新增配置项
class Settings(BaseSettings):
    # ... 保留现有配置 ...

    # API前缀
    api_prefix: str = "/api"  # 从 /api/v1 改为 /api

    # JWT 认证
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8小时

    # 结构编辑器开关
    enable_structure_editor: bool = False
```

---

## 四、数据库迁移脚本

### 4.1 001_create_auth_tables.sql

```sql
CREATE TABLE IF NOT EXISTS `user` (
    `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `account`    VARCHAR(128) NOT NULL COMMENT '登录账号/邮箱',
    `password`   VARCHAR(256) NOT NULL COMMENT 'bcrypt hash',
    `name`       VARCHAR(100) NOT NULL COMMENT '显示名称',
    `company`    VARCHAR(200) NOT NULL DEFAULT '' COMMENT '公司名称',
    `role`       VARCHAR(50)  NOT NULL DEFAULT '企业管理员' COMMENT '角色',
    `phone`      VARCHAR(20)  NOT NULL DEFAULT '' COMMENT '手机号',
    `email`      VARCHAR(128) NOT NULL DEFAULT '' COMMENT '邮箱',
    `status`     TINYINT      NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
    `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_account` (`account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户';
```

### 4.2 002_create_config_tables.sql

```sql
-- 审查维度
CREATE TABLE IF NOT EXISTS `dimension` (
    `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name`       VARCHAR(100) NOT NULL COMMENT '维度名称',
    `desc`       TEXT COMMENT '维度说明',
    `sort_order` INT NOT NULL DEFAULT 0,
    `status`     VARCHAR(20) NOT NULL DEFAULT '已启用' COMMENT '已启用/已停用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审查维度';

-- 审查点
CREATE TABLE IF NOT EXISTS `audit_point` (
    `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `dim_id`          BIGINT UNSIGNED NOT NULL COMMENT '所属维度ID',
    `name`            VARCHAR(200) NOT NULL COMMENT '审查点名称',
    `category`        VARCHAR(50)  NOT NULL DEFAULT '' COMMENT '后果类别',
    `desc`            VARCHAR(500) DEFAULT '' COMMENT '描述',
    `instruction`     TEXT COMMENT '审查说明',
    `risk_points`     JSON COMMENT '风险点列表',
    `examples`        JSON COMMENT '审查示例列表',
    `default_result`  JSON COMMENT '默认结论',
    `default_checked` TINYINT NOT NULL DEFAULT 1 COMMENT '默认勾选',
    `status`          VARCHAR(20) NOT NULL DEFAULT '已启用' COMMENT '已启用/已停用',
    `sort_order`      INT NOT NULL DEFAULT 0,
    `created_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at`      DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_dim` (`dim_id`, `deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审查点';

-- 合同类型
CREATE TABLE IF NOT EXISTS `contract_type` (
    `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `code`           VARCHAR(50) COMMENT '类型编码',
    `name`           VARCHAR(100) NOT NULL COMMENT '合同类型名称',
    `stance`         VARCHAR(50)  NOT NULL DEFAULT '' COMMENT '立场',
    `desc`           TEXT COMMENT '合同描述',
    `keywords`       JSON COMMENT '识别关键词列表',
    `related_points` INT NOT NULL DEFAULT 0 COMMENT '关联审查点数量',
    `status`         VARCHAR(20) NOT NULL DEFAULT '已启用' COMMENT '已启用/已停用',
    `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at`     DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='合同类型';

-- 合同类型-审查点关联
CREATE TABLE IF NOT EXISTS `contract_type_audit_point` (
    `id`               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `contract_type_id` BIGINT UNSIGNED NOT NULL,
    `audit_point_id`   BIGINT UNSIGNED NOT NULL,
    `enabled`          TINYINT NOT NULL DEFAULT 1 COMMENT '该合同类型下是否启用',
    `sort_order`       INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_ct_ap` (`contract_type_id`, `audit_point_id`),
    KEY `idx_ct` (`contract_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='合同类型-审查点关联';
```

### 4.3 003_create_audit_tables.sql

```sql
CREATE TABLE IF NOT EXISTS `audit_task` (
    `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `contract_id`       BIGINT UNSIGNED NOT NULL COMMENT '关联合同ID',
    `contract_type_id`  BIGINT UNSIGNED COMMENT '合同类型ID',
    `stance`            VARCHAR(50) NOT NULL DEFAULT '甲方' COMMENT '审核立场',
    `status`            VARCHAR(20) NOT NULL DEFAULT 'queued' COMMENT 'queued/running/succeeded/failed',
    `total_risk_count`  INT NOT NULL DEFAULT 0,
    `major_risk_count`  INT NOT NULL DEFAULT 0,
    `general_risk_count` INT NOT NULL DEFAULT 0,
    `created_at`        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_contract` (`contract_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审核任务';

CREATE TABLE IF NOT EXISTS `audit_result_item` (
    `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `task_id`         BIGINT UNSIGNED NOT NULL COMMENT '审核任务ID',
    `dim_id`          BIGINT UNSIGNED NOT NULL COMMENT '维度ID',
    `dim_name`        VARCHAR(100) NOT NULL COMMENT '维度名称',
    `audit_point_id`  BIGINT UNSIGNED COMMENT '审查点ID',
    `title`           VARCHAR(200) NOT NULL COMMENT '风险点标题',
    `risk_level`      TINYINT NOT NULL COMMENT '1=重大风险 2=一般风险',
    `risk_summary`    TEXT COMMENT '风险说明',
    `risk_analysis`   TEXT COMMENT '风险分析',
    `modify_example`  TEXT COMMENT '修改示例',
    `clause_name`     VARCHAR(200) COMMENT '所属条款',
    `hit_text`        TEXT COMMENT '命中原文',
    `display`         TINYINT NOT NULL DEFAULT 1 COMMENT '1显示 0用户忽略',
    `sort_order`      INT NOT NULL DEFAULT 0,
    `created_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_task_dim` (`task_id`, `dim_id`, `display`),
    KEY `idx_task_level` (`task_id`, `risk_level`, `display`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审核结果明细';

CREATE TABLE IF NOT EXISTS `audit_dimension_stat` (
    `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `task_id`        BIGINT UNSIGNED NOT NULL,
    `dim_id`         BIGINT UNSIGNED NOT NULL,
    `dim_name`       VARCHAR(100) NOT NULL COMMENT '维度名称',
    `total_count`    INT NOT NULL DEFAULT 0,
    `major_count`    INT NOT NULL DEFAULT 0,
    `general_count`  INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_dim` (`task_id`, `dim_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审核维度统计';
```

### 4.4 004_seed_default_data.sql

传入 `mock/db.js` 中的初始数据。关键数据映射：

| 前端 mock | DB 表 | 说明 |
|-----------|-------|------|
| `profile` | `user` | 默认管理员，bcrypt 加密密码 |
| `dimensionDetail` | `dimension` | 5 个维度 |
| `points` | `audit_point` | 18 个审查点，`risk_points` JSON 根据 name/category 生成 |
| `contractTypes` | `contract_type` | 6 个合同类型，`keywords` JSON 数组 |
| `selectableDimensions` | `dimension` | 复用 dimension 表，status='已启用' 即为可选 |

种子数据使用 `INSERT IGNORE` 保证幂等。

### 4.5 005_extend_contracts_table.sql

```sql
ALTER TABLE contracts
  ADD COLUMN IF NOT EXISTS `risk`       VARCHAR(20) NOT NULL DEFAULT '未审核',
  ADD COLUMN IF NOT EXISTS `risk_count` INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS `risk_level` VARCHAR(20) NOT NULL DEFAULT 'green';
```

> MySQL 不原生支持 `ADD COLUMN IF NOT EXISTS`，需在 Python 迁移执行器中用 try/except 处理 1060 错误。

---

## 五、数据访问层设计

### 5.1 共享连接池 (`services/db_base.py`)

```python
import pymysql
from pymysql.cursors import DictCursor
from app.config import get_settings

class DatabasePool:
    """MySQL 连接管理。与现有 contract_store.py 的连接方式兼容。"""

    def __init__(self):
        self._settings = get_settings()

    def get_connection(self) -> pymysql.Connection:
        return pymysql.connect(
            host=self._settings.mysql_host,
            port=self._settings.mysql_port,
            user=self._settings.mysql_user,
            password=self._settings.mysql_password,
            database=self._settings.mysql_database,
            charset="utf8mb4",
            cursorclass=DictCursor,
        )

    def get_server_connection(self) -> pymysql.Connection:
        """获取不指定 database 的连接（用于建库）。"""
        return pymysql.connect(
            host=self._settings.mysql_host,
            port=self._settings.mysql_port,
            user=self._settings.mysql_user,
            password=self._settings.mysql_password,
            charset="utf8mb4",
            cursorclass=DictCursor,
        )

db_pool = DatabasePool()
```

### 5.2 Repository 模式

所有新 Repository 类遵循与现有 `contract_store.py` 相同的接口模式：

| 方法 | 说明 |
|------|------|
| `initialize()` | 建表（幂等） |
| `find_all(filters)` | 多条件查询，返回 list[dict] |
| `find_by_id(id)` | 单条查询，返回 dict 或 None |
| `insert(payload)` | 插入，返回 id |
| `update_by_id(id, updates)` | 部分更新 |
| `delete_by_id(id)` | 物理或软删除 |
| `count(filters)` | 计数 |

新增 Repository 文件：

**`services/auth_store.py`** — `UserRepository`
- `find_by_account(account)` — 按账号查询
- `verify_password(plain, hashed)` — bcrypt 验证

**`services/dimension_store.py`** — `DimensionRepository`
- `find_selectable()` — 查询所有已启用维度（返回 `[{name, desc}]`）
- `find_names()` — 查询所有已启用维度的名称列表（返回 `[str]`）

**`services/audit_point_store.py`** — `AuditPointRepository`
- 软删除（设置 `deleted_at`）
- 列表查询包含 `riskPoints` 数量：`JSON_LENGTH(risk_points)`

**`services/contract_type_store.py`** — `ContractTypeRepository`
- 软删除
- 支持关键词搜索

**`services/audit_result_store.py`** — `AuditResultStore`
- `create_task(contract_id, stance)`  → task_id
- `insert_results(task_id, items[])` — 批量插入结果条目
- `insert_stats(task_id, stats[])` — 批量插入维度统计
- `get_results_by_contract(contract_id)` — 按合同查结果（用于 `/result` 端点）
- `get_stats_by_task(task_id)` — 查维度统计
- `update_display(item_id, display)` — 忽略/恢复条目

### 5.3 contract_store.py 的改造

1. 将直接 `pymysql.connect()` 替换为 `db_pool.get_connection()`
2. 在 `initialize()` 中增加 `contracts` 表扩展列的处理

---

## 六、API 适配层设计

### 6.1 扁平化响应函数 (`api/responses.py`)

在现有 `ok_response()` / `error_response()` 基础上新增：

```python
def flat_list(items: list[dict], total: int, status_code=200) -> JSONResponse:
    """前端期望的列表响应：{ items: [...], total: N }"""
    return JSONResponse(status_code=status_code, content={"items": items, "total": total})

def flat_object(obj: dict, status_code=200) -> JSONResponse:
    """前端期望的单对象响应：直接返回对象"""
    return JSONResponse(status_code=status_code, content=obj)

def ok_deleted() -> JSONResponse:
    """前端期望的删除响应：{ ok: true }"""
    return JSONResponse(status_code=200, content={"ok": True})
```

### 6.2 字段映射 (`api/adapters.py`)

```python
def contract_to_frontend(record: dict, audit_stats: dict | None = None) -> dict:
    """MySQL 合同记录 → 前端格式"""
    stats = audit_stats or {}
    return {
        "id": str(record["id"]),
        "name": record.get("contract_name", ""),
        "partyA": record.get("party_a", ""),
        "partyB": record.get("party_b", ""),
        "type": record.get("contract_type", "未分类"),
        "risk": stats.get("risk", record.get("risk", "未审核")),
        "riskCount": stats.get("riskCount", record.get("risk_count", 0)),
        "riskLevel": stats.get("riskLevel", record.get("risk_level", "green")),
        "updatedAt": record.get("review_time", record.get("updated_at", "")),
    }

def contract_from_frontend(payload: dict) -> dict:
    """前端 payload → MySQL 字段"""
    result = {}
    if "name" in payload: result["contract_name"] = payload["name"]
    if "partyA" in payload: result["party_a"] = payload["partyA"]
    if "partyB" in payload: result["party_b"] = payload["partyB"]
    if "type" in payload: result["contract_type"] = payload["type"]
    return result

def dimension_to_frontend(record: dict) -> dict:
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "desc": record.get("desc", ""),
        "status": record.get("status", "已启用"),
        "updatedAt": str(record.get("updated_at", "")),
    }

def point_to_frontend(record: dict) -> dict:
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "category": record.get("category", ""),
        "dimension": record.get("dim_name", ""),
        "desc": record.get("desc", ""),
        "riskPoints": record.get("risk_points_count", 0),
        "status": record.get("status", "已启用"),
        "defaultChecked": bool(record.get("default_checked", 1)),
        "updatedAt": str(record.get("updated_at", "")),
    }

def contract_type_to_frontend(record: dict) -> dict:
    return {
        "id": str(record["id"]),
        "code": record.get("code", ""),
        "name": record["name"],
        "stance": record.get("stance", ""),
        "desc": record.get("desc", ""),
        "keywords": record.get("keywords"),
        "relatedPoints": record.get("related_points", 0),
        "status": record.get("status", "已启用"),
        "updatedAt": str(record.get("updated_at", "")),
    }
```

---

## 七、认证模块设计

### 7.1 JWT 服务 (`services/auth_service.py`)

```python
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.config import get_settings

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(user_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> int:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    return int(payload["sub"])
```

### 7.2 JWT 中间件 (`middleware.py` 新增部分)

```python
# 白名单路径（无需认证）
AUTH_WHITELIST = {
    "/api/health",
    "/api/auth/login",
}

@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    # 白名单放行
    if request.url.path in AUTH_WHITELIST:
        return await call_next(request)

    # OPTIONS 预检请求放行
    if request.method == "OPTIONS":
        return await call_next(request)

    # 验证 JWT
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "未登录"})

    try:
        token = auth_header[7:]
        user_id = decode_token(token)
        request.state.user_id = user_id
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "令牌无效或已过期"})

    return await call_next(request)
```

### 7.3 认证 API (`api/auth.py`)

**POST /api/auth/login**
- 输入：`{ account: str, password: str }`
- 逻辑：查询 user 表 → bcrypt 验证 → 生成 JWT
- 输出：`{ token: str, user: { name, account, company, role, phone, email } }`

**GET /api/auth/profile**
- 输入：无（从 `request.state.user_id` 获取用户 ID）
- 输出：user 对象

**PUT /api/auth/profile**
- 输入：`{ name?, company?, phone?, email? }`
- 输出：更新后的 user 对象

---

## 八、配置中心 API 设计

### 8.1 审查点 (`api/points.py`)

| Method | Path | 实现要点 |
|--------|------|----------|
| GET | `/api/points` | Query: `keyword` → `WHERE name LIKE %keyword% AND deleted_at IS NULL`；列表中 `riskPoints` 字段为 `JSON_LENGTH(risk_points)` 的值；字段映射用 `point_to_frontend` |
| GET | `/api/points/:id` | 按 ID 查询，返回含 `risk_points`、`examples`、`default_result` JSON 字段的完整对象 |
| POST | `/api/points` | 接受所有字段，必填 `dimId`、`name`；`risk_points`/`examples`/`default_result` 从请求 JSON 直接写入 |
| PUT | `/api/points/:id` | 部分更新；`request_body.dict(exclude_unset=True)` |
| DELETE | `/api/points/:id` | 软删除：`UPDATE audit_point SET deleted_at = NOW() WHERE id = ?`；返回 `{ok:true}` |

### 8.2 维度 (`api/dimensions.py`)

| Method | Path | 实现要点 |
|--------|------|----------|
| GET | `/api/dimensions` | 返回全部维度（含已停用），`{items, total}` |
| GET | `/api/dimensions/names` | `SELECT name FROM dimension WHERE status='已启用' ORDER BY sort_order`，返回 `["基础核查","法务风险",...]` |
| GET | `/api/dimensions/selectable` | `SELECT name, desc FROM dimension WHERE status='已启用'`，返回 `[{name, desc}]` |
| POST | `/api/dimensions` | 创建，`name` 唯一 |
| PUT | `/api/dimensions/:id` | 更新（含状态切换） |
| DELETE | `/api/dimensions/:id` | 检查是否有审查点引用，有则拒绝（返回错误）；无则物理删除 |
| POST | `/api/dimensions/relations` | 保存关联关系（当前版本直接返回 `{ok:true}`，关系数据已通过审查点的 `dim_id` 维护） |

### 8.3 合同类型 (`api/contract_types.py`)

| Method | Path | 实现要点 |
|--------|------|----------|
| GET | `/api/contract-types` | Query: `keyword` → 搜索 name/code；软删除过滤 |
| GET | `/api/contract-types/:id` | 含关联审查点 ID 列表 |
| POST | `/api/contract-types` | 创建；`keywords` 直接写 JSON 数组 |
| PUT | `/api/contract-types/:id` | 部分更新；更新 `relatedPoints` 计数 |
| DELETE | `/api/contract-types/:id` | 软删除 + 物理删除关联记录（事务） |

---

## 九、合同上传与审核 API 设计

### 9.1 上传端点 (`POST /api/contracts/upload`)

**流程**：
```
1. 接收 multipart file
2. 调用 DocumentUploadPipeline.run(file) → stored_upload + task
3. 等待 task 完成（v1 同步模式：轮询 task 状态或阻塞等待线程完成）
4. 从 contract_extractor 获取合同类型检测结果
5. 从 contract_store 获取 upsert 后的合同记录 ID
6. 返回前端格式
```

**响应**：
```json
{
  "id": "5",
  "name": "智慧园区软件采购合同.docx",
  "detectedType": "采购合同",
  "matchConfidence": 96,
  "fileId": "8d68b3ee-5392-435b-a26a-f10aab24ecfe",
  "enableStructureEditor": false
}
```

其中 `enableStructureEditor` 来自 `settings.enable_structure_editor`。

### 9.2 审核执行 (`POST /api/contracts/:id/audit`)

**输入**：`{ role: "甲方", points: ["p1", "p2", "p3"] }`

**v1 降级方案流程**：
```
1. 通过 contract_id 查询合同记录，获取 file_id 和 contract_type
2. 创建 audit_task 记录（status='running'）
3. 加载 document.json，提取原文段落（用于 originalText）
4. 对每个选中的 point_id：
   a. 查询 audit_point 表获取 default_result
   b. 生成 audit_result_item（标题、风险等级、说明、分析、示例从 default_result + risk_points 中提取）
   c. 分配到对应维度
5. 按维度聚合统计 → 写入 audit_dimension_stat
6. 更新 contracts 表风险缓存（risk/risk_count/risk_level）
7. 标记 audit_task status='succeeded'
8. 返回 { id: str(contract_id), status: "done" }
```

**结果生成规则**：
- `title`：来自审查点 name
- `level`：来自 default_result.level（`'高风险'` → `'major'`，其他 → `'general'`）
- `desc`：来自 default_result.analysis
- `analysis`：来自 risk_points 中匹配 level 的标准描述
- `example`：来自 default_result.suggestion
- `clause`：来自审查点 name（作为条款标识）
- `dimension`：来自关联的 dimension.name
- `hit_text`：从 document 原文中取首段相关文本

### 9.3 审核结果查询 (`GET /api/contracts/:id/result`)

**响应格式**：必须匹配 `mock/db.js` 中 `buildAuditResult()` 返回的结构。

```json
{
  "contractId": "1",
  "contractName": "智慧园区软件采购合同",
  "partyA": "华城数字建设有限公司",
  "partyB": "云启科技有限公司",
  "docType": "Word",
  "originalText": [
    { "type": "h2", "text": "智慧园区软件采购合同" },
    { "type": "p", "text": "甲方：华城数字建设有限公司" },
    { "type": "h3", "text": "第四条 项目交付与验收" },
    { "type": "highlight", "text": "若甲方在十个工作日内未提出书面异议..." },
    ...
  ],
  "dimensions": ["基础核查", "法务风险", "财务风险", "形式核查"],
  "risks": [
    {
      "dimension": "基础核查",
      "title": "主体信息缺失风险",
      "level": "major",
      "desc": "甲方名称、地址、法定代表人均缺失...",
      "analysis": "主体信息不完整将导致责任主体难以确认...",
      "example": "甲方名称：XXX公司　地址：XXX市...",
      "clause": "主体信息条款"
    },
    ...
  ]
}
```

**`originalText` 构建逻辑**：
1. 从 `document.json` 的 `contract_structure` 中遍历节点
2. 根据 `kind` 映射 type：`chapter/heading` → `h2`，`article` → `h3`，`content` 文本 → `p`
3. 如有命中风险条款的 text，标记为 `highlight`

**`dimensions` 来源**：`SELECT dim_name FROM audit_dimension_stat WHERE task_id=? ORDER BY dim_id`
**`risks` 来源**：`audit_result_item` 映射到前端 risk 结构

---

## 十、结构编辑可选化

### 10.1 后端

`config.py` 中增加：
```python
enable_structure_editor: bool = False
```

`POST /api/contracts/upload` 响应中包含 `enableStructureEditor` 字段。

保留 `api/documents.py` 全部端点：
- `GET /api/documents/:fileId` — 文档信息
- `GET /api/documents/:fileId/structure` — 章节树
- `PUT /api/documents/:fileId/structure` — 保存章节树

### 10.2 前端

在 `StepUpload.vue` 的上传成功回调中，根据 `res.enableStructureEditor` 决定跳转：
```javascript
async function onUploaded(file) {
  const res = await uploadContract(file)
  reviewStore.contractId = res.id
  reviewStore.fileName = res.name
  reviewStore.detectedType = res.detectedType
  reviewStore.matchConfidence = res.matchConfidence
  
  if (res.enableStructureEditor) {
    // 跳转结构编辑页面
    router.push({ name: 'structureEditor', params: { fileId: res.fileId } })
  } else {
    // 直接进入审核设置
    step.value = 2
  }
}
```

结构编辑页面作为后续迭代任务，当前阶段只需后端 API 就绪。

---

## 十一、main.py 最终形态

```python
from fastapi import FastAPI
from app.api import (
    health, files, documents, contracts, review,
    auth, points, dimensions, contract_types, audit,
)
from app.config import get_settings
from app.exception_handlers import register_exception_handlers
from app.lifecycle import app_lifespan
from app.middleware import register_middlewares

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI智契合同审核 API",
        version="0.2.0",
        lifespan=app_lifespan,
    )
    register_middlewares(app)
    register_exception_handlers(app)

    # 系统
    app.include_router(health.router, prefix=settings.api_prefix, tags=["系统"])
    # 认证
    app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["认证"])
    # 文件上传与解析
    app.include_router(files.router, prefix=f"{settings.api_prefix}/files", tags=["文件服务"])
    app.include_router(documents.router, prefix=f"{settings.api_prefix}/documents", tags=["文档结构"])
    # 合同管理（含上传、审核）
    app.include_router(contracts.router, prefix=f"{settings.api_prefix}/contracts", tags=["合同管理"])
    # 审核配置
    app.include_router(review.router, prefix=f"{settings.api_prefix}/review", tags=["审核配置"])
    # 配置中心
    app.include_router(points.router, prefix=f"{settings.api_prefix}/points", tags=["审查点"])
    app.include_router(dimensions.router, prefix=f"{settings.api_prefix}/dimensions", tags=["审查维度"])
    app.include_router(contract_types.router, prefix=f"{settings.api_prefix}/contract-types", tags=["合同类型"])
    return app

app = create_app()
```

移除：`web_router`、`compat_router`、`StaticFiles` mount、`review_router` 的前缀挂载审核相关端点（审核端点合并到 contracts 和 audit 中）。

---

## 十二、前端变更清单

### 12.1 `src/services/config.js`
```javascript
// 修改前：
export const USE_MOCK = true

// 修改后：
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
```

### 12.2 `src/services/point.service.js`（第 51 行）
```javascript
// 修改前：
const { data } = await http.get('/dimensions')

// 修改后：
const { data } = await http.get('/dimensions/names')
```

### 12.3 `.env` 文件（新增）
```bash
VITE_API_BASE=/api
VITE_USE_MOCK=false
VITE_ENABLE_STRUCTURE_EDITOR=false
```

---

## 十三、迁移执行器 (`lifecycle.py` 修改)

在 `app_lifespan` 的 startup 阶段，增加自动迁移：

```python
from pathlib import Path
import pymysql

MIGRATIONS_DIR = Path(__file__).resolve().parent / "db" / "migrations"

def run_migrations():
    """按文件名顺序执行 SQL 迁移脚本。"""
    conn = db_pool.get_connection()
    try:
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = sql_file.read_text(encoding="utf-8")
            with conn.cursor() as cursor:
                for statement in sql.split(";"):
                    statement = statement.strip()
                    if statement:
                        try:
                            cursor.execute(statement)
                        except pymysql.err.OperationalError as e:
                            # 忽略重复建表/加列错误
                            if e.args[0] not in (1050, 1060):
                                raise
            conn.commit()
    finally:
        conn.close()
```

---

## 十四、错误处理规范

所有 API 端点遵循统一错误格式：

```json
{
  "detail": "错误描述"
}
```

HTTP 状态码约定：
| 状态码 | 场景 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 参数校验失败 |
| 401 | 未登录或 token 失效 |
| 404 | 资源不存在 |
| 409 | 冲突（名称重复、有关联无法删除） |
| 413 | 文件过大 |
| 415 | 文件格式不支持 |
| 422 | 请求参数校验失败 |
| 500 | 服务器内部错误 |

> 前端 `http.js` 的响应拦截器从 `error.response.data.detail` 读取错误信息，401 时自动跳转登录页。后端错误响应中的 `detail` 字段直接对应前端的提示文本。

---

## 十五、依赖变更

在现有 `pyproject.toml` 增加：
```toml
dependencies = [
    # ... 现有依赖 ...
    "bcrypt>=4.0.0",
    "pyjwt>=2.8.0",
]
```

---
