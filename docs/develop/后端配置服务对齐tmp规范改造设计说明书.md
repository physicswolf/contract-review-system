# 后端配置服务对齐 tmp 规范改造设计说明书

**项目**：contract-review-system  
**日期**：2026-06-30  
**版本**：v1.0  
**对应计划书**：`docs/planning/后端配置服务对齐tmp规范改造计划书.md`

---

## 一、数据库 Schema 重建

### 1.1 迁移脚本 `008_rebuild_config_tables.sql`

```sql
-- 重建配置表以对齐 tmp 规范
DROP TABLE IF EXISTS contract_type_audit_point;
DROP TABLE IF EXISTS audit_point;
DROP TABLE IF EXISTS contract_type;
DROP TABLE IF EXISTS dimension;

-- dimension: description + enabled TINYINT
CREATE TABLE dimension (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100)    NOT NULL,
    description TEXT,
    sort_order  INT             NOT NULL DEFAULT 0,
    enabled     TINYINT         NOT NULL DEFAULT 1,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_name (name),
    KEY idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审查维度';

-- audit_point: description + enabled TINYINT
CREATE TABLE audit_point (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    dim_id         BIGINT UNSIGNED NOT NULL,
    name           VARCHAR(200)    NOT NULL,
    description    VARCHAR(500)    DEFAULT '',
    instruction    TEXT,
    risk_points    JSON,
    examples       JSON,
    default_result JSON,
    enabled        TINYINT         NOT NULL DEFAULT 1,
    sort_order     INT             NOT NULL DEFAULT 0,
    created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at     DATETIME        DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_dim (dim_id, deleted_at, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审查点';

-- contract_type: description + enabled TINYINT + 唯一约束
CREATE TABLE contract_type (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    code        VARCHAR(50),
    name        VARCHAR(100)    NOT NULL,
    stance      VARCHAR(50)     NOT NULL,
    description TEXT,
    keywords    JSON,
    enabled     TINYINT         NOT NULL DEFAULT 1,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at  DATETIME        DEFAULT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_name_stance (name, stance),
    KEY idx_enabled (enabled, deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同类型';

-- contract_type_audit_point: 不变
CREATE TABLE contract_type_audit_point (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    contract_type_id BIGINT UNSIGNED NOT NULL,
    audit_point_id   BIGINT UNSIGNED NOT NULL,
    enabled          TINYINT         NOT NULL DEFAULT 1,
    sort_order       INT             NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_ct_ap (contract_type_id, audit_point_id),
    KEY idx_ct (contract_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同类型-审查点关联';
```

### 1.2 种子数据更新

所有 JSON 字段改为 tmp 格式：

**risk_points**：
```json
[{"name":"主体信息缺失","highStd":"主体信息或授权材料缺失将导致责任主体难以确认。","lowStd":"主体信息表述不完整，建议补充核对。","noneStd":""}]
```

**default_result**：
```json
{"level":"高风险","analysis":"主体信息或签署授权不完整，可能影响合同效力与追责。","suggestion":"补充双方主体信息、统一社会信用代码、法定代表人和授权文件。"}
```

**examples**：
```json
[]
```

### 1.3 列名映射

| 当前列名 | 新列名 | 说明 |
|----------|--------|------|
| `desc` | `description` | 维度、审查点、合同类型 |
| `status` VARCHAR | `enabled` TINYINT | `'已启用'`→1, `'已停用'`→0 |
| `category` | — | 删除此列（tmp 无此字段） |
| `default_checked` | — | 删除此列（tmp 无此字段） |
| `related_points` | — | 删除此列（改用 JOIN COUNT） |

---

## 二、Repository 改造

### 2.1 `dimension_store.py`

```python
class DimensionRepository:
    def find_all(self, enabled: int | None = None) -> list[dict]:
        sql = "SELECT id, name, description, sort_order, enabled, updated_at FROM dimension"
        params = []
        if enabled is not None:
            sql += " WHERE enabled = %s"
            params.append(enabled)
        sql += " ORDER BY sort_order, id"
        # ...

    def find_names(self) -> list[str]:
        """仅返回已启用维度名称"""
        # WHERE enabled = 1

    def find_selectable(self) -> list[dict]:
        """返回已启用维度的 {name, description}"""
        # WHERE enabled = 1

    def insert(self, payload: dict) -> int:
        # INSERT: name, description, sort_order, enabled

    def update_by_id(self, dim_id: int, updates: dict) -> dict | None:
        # 允许字段: name, description, sort_order, enabled

    def delete_by_id(self, dim_id: int) -> bool:
        # 检查 audit_point 引用 (WHERE deleted_at IS NULL)
```

### 2.2 `audit_point_store.py`

**核心方法**：

```python
class AuditPointRepository:
    def find_all(self, filters: dict | None = None) -> list[dict]:
        """tmp 格式列表查询。
        参数: keyword, dim_id, enabled
        返回: [{id, name, description, dimId, dimName, riskPoints:[], enabled, updatedAt}]"""
        keyword = str((filters or {}).get("keyword", "")).strip()
        dim_id = (filters or {}).get("dim_id")
        enabled = (filters or {}).get("enabled")

        sql = """
            SELECT ap.*, d.name AS dim_name
            FROM audit_point ap
            JOIN dimension d ON d.id = ap.dim_id
            WHERE ap.deleted_at IS NULL
        """
        if keyword:
            sql += " AND ap.name LIKE %s"
        if dim_id is not None:
            sql += " AND ap.dim_id = %s"
        if enabled is not None:
            sql += " AND ap.enabled = %s"
        sql += " ORDER BY ap.sort_order, ap.id"

        result = []
        for r in rows:
            rp = _parse_json(r.get("risk_points"), [])
            result.append({
                "id": r["id"], "name": r["name"],
                "description": r.get("description") or "",
                "dimId": r["dim_id"], "dimName": r.get("dim_name", ""),
                "riskPoints": [x.get("name", "") for x in rp if isinstance(x, dict)],
                "enabled": r["enabled"], "updatedAt": _format_iso(r.get("updated_at")),
            })
        return result

    def find_by_id(self, point_id: int) -> dict | None:
        """tmp 格式详情。返回完整 JSON（riskPoints, examples, defaultResult 原始数组/对象）。"""
        # JOIN dimension → dim_name
        # 返回: {id, dimId, dimName, name, description, instruction,
        #         riskPoints: [{name,highStd,lowStd,noneStd}],
        #         examples: [{original,level,analysis,suggestion}],
        #         defaultResult: {level,analysis,suggestion},
        #         enabled, updatedAt}

    def insert(self, payload: dict) -> int:
        """tmp 格式创建。
        映射: dimId→dim_id, description→desc(这里需要中间映射),
              riskPoints→risk_points(JSON.dumps), 
              defaultResult→default_result(JSON.dumps),
              enabled→enabled"""
        # INSERT INTO audit_point (dim_id, name, description, instruction,
        #   risk_points, examples, default_result, enabled, sort_order) VALUES (...)

    def update_by_id(self, point_id: int, updates: dict) -> dict | None:
        """tmp 格式更新。允许字段: dim_id, name, description, instruction,
           risk_points, examples, default_result, enabled, sort_order"""

    def toggle_enabled(self, point_id: int, v: bool) -> dict | None:
        """启停"""
        self.update_by_id(point_id, {"enabled": 1 if v else 0})

    def delete_by_id(self, point_id: int) -> bool:
        """软删除: UPDATE SET deleted_at = NOW()"""
```

### 2.3 `contract_type_store.py`

```python
class ContractTypeRepository:
    def find_all(self, filters: dict | None = None) -> list[dict]:
        """tmp 格式列表。JOIN 实时计算 linkedPointCount"""
        sql = """
            SELECT ct.*, COUNT(ctap.id) AS linked_point_count
            FROM contract_type ct
            LEFT JOIN contract_type_audit_point ctap ON ctap.contract_type_id = ct.id
            WHERE ct.deleted_at IS NULL
        """
        # GROUP BY ct.id
        # 返回: {id, code, name, stance, description, keywords, enabled, linkedPointCount}

    def find_by_id(self, type_id: int) -> dict | None:
        """tmp 格式详情，含 linkedAuditPoints"""
        # SELECT ct.* + linkedAuditPoints = [{auditPointId, enabled}]

    def insert(self, payload: dict) -> int:
        """INSERT: code, name, stance, description, keywords, enabled"""

    def update_by_id(self, type_id: int, updates: dict) -> dict | None:
        """UPDATE: 允许字段 code, name, stance, description, keywords, enabled"""

    def delete_by_id(self, type_id: int) -> bool:
        """软删除 + DELETE 关联表"""

    def replace_associations(self, type_id: int, point_ids: list[int]):
        """事务内 DELETE + INSERT"""

    def toggle_association(self, type_id: int, ap_id: int, v: bool):
        """UPDATE contract_type_audit_point SET enabled = v"""
```

---

## 三、API 端点改造

### 3.1 统一响应辅助函数

在 `api/responses.py` 或各 API 文件中定义：

```python
def _ok(data=None, status_code=200) -> JSONResponse:
    content = {"code": 0, "msg": "ok"}
    if data is not None:
        content["data"] = data
    return JSONResponse(status_code=status_code, content=content)

def _err(code: int, msg: str, http: int = 400) -> JSONResponse:
    return JSONResponse(status_code=http, content={"code": code, "msg": msg})
```

错误码约定：
```python
ERR_PARAM    = 40001  # 参数错误
ERR_NOTFOUND = 40401  # 资源不存在
ERR_CONFLICT = 40901  # 冲突
ERR_SERVER   = 50001  # 内部错误
```

### 3.2 `api/audit_points.py`（完全重写为 tmp 格式）

```python
@router.get("")
async def list_audit_points(
    keyword: str = Query(default=""),
    dimId: int | None = Query(default=None),
    enabled: int | None = Query(default=None),
):
    records = audit_point_repository.find_all({"keyword": keyword, "dim_id": dimId, "enabled": enabled})
    return _ok(records)

@router.get("/{point_id}")
async def get_audit_point(point_id: int):
    record = audit_point_repository.find_by_id(point_id)
    if record is None:
        return _err(ERR_NOTFOUND, "审查点不存在", 404)
    return _ok(record)

@router.post("")
async def create_audit_point(payload: dict):
    if not str(payload.get("name") or "").strip():
        return _err(ERR_PARAM, "dimId 和 name 不能为空")
    point_id = audit_point_repository.insert(payload)
    return _ok({"id": point_id}, 201)

@router.put("/{point_id}")
async def update_audit_point(point_id: int, payload: dict):
    record = audit_point_repository.update_by_id(point_id, payload)
    if record is None:
        return _err(ERR_NOTFOUND, "审查点不存在", 404)
    return _ok()

@router.patch("/{point_id}/enabled")
async def toggle_audit_point(point_id: int, payload: dict):
    if "enabled" not in payload:
        return _err(ERR_PARAM, "enabled 不能为空")
    record = audit_point_repository.toggle_enabled(point_id, bool(payload["enabled"]))
    if record is None:
        return _err(ERR_NOTFOUND, "审查点不存在", 404)
    return _ok()

@router.delete("/{point_id}")
async def delete_audit_point(point_id: int):
    deleted = audit_point_repository.delete_by_id(point_id)
    if not deleted:
        return _err(ERR_NOTFOUND, "审查点不存在", 404)
    return _ok()
```

### 3.3 `api/dimensions.py`（完全重写为 tmp 格式）

```python
@router.get("")
async def list_dimensions(enabled: int | None = Query(default=None)):
    records = dimension_repository.find_all(enabled=enabled)
    data = [{
        "id": r["id"], "name": r["name"],
        "description": r.get("description") or "",
        "sortOrder": r.get("sort_order", 0),
        "enabled": r["enabled"],
        "updatedAt": _format_iso(r.get("updated_at")),
    } for r in records]
    return _ok(data)

@router.get("/names")
async def list_dimension_names():
    return dimension_repository.find_names()  # 返回 [str]

@router.get("/selectable")
async def list_selectable_dimensions():
    return [{"name": r["name"], "desc": r.get("description") or ""}
            for r in dimension_repository.find_selectable()]

@router.post("")
async def create_dimension(payload: dict):
    # name 必填 → insert → _ok({id})
    # 重复 → _err(40901, "维度名称已存在")

@router.put("/{dim_id}")
async def update_dimension(dim_id: int, payload: dict):
    # 重复 → _err(40901)
    # 不存在 → _err(40401)

@router.delete("/{dim_id}")
async def delete_dimension(dim_id: int):
    # 有引用 → _err(40901, "该维度下存在 N 个审查点，请先删除或迁移后再操作")
```

### 3.4 `api/contract_types.py`（完全重写为 tmp 格式）

```python
@router.get("")
async def list_contract_types(
    enabled: int | None = Query(default=None),
    keyword: str = Query(default=""),
):
    records = contract_type_repository.find_all({"enabled": enabled, "keyword": keyword})
    return _ok(records)

@router.get("/{type_id}")
async def get_contract_type(type_id: int):
    record = contract_type_repository.find_by_id(type_id)
    if record is None:
        return _err(ERR_NOTFOUND, "合同类型不存在", 404)
    return _ok(record)

@router.post("")
async def create_contract_type(payload: dict):
    # name+stance 必填 → insert
    # 重复 uk_name_stance → _err(40901, "该合同类型-立场已存在")

@router.put("/{type_id}")
async def update_contract_type(type_id: int, payload: dict):
    # 重复 → _err(40901)
    # 不存在 → _err(40401)

@router.delete("/{type_id}")
async def delete_contract_type(type_id: int):
    # 软删除 + DELETE 关联表

@router.put("/{type_id}/audit-points")
async def save_audit_points(type_id: int, payload: dict):
    ids = payload.get("auditPointIds") or []
    contract_type_repository.replace_associations(type_id, [int(i) for i in ids])
    return _ok()

@router.patch("/{type_id}/audit-points/{ap_id}/enabled")
async def toggle_ct_audit_point(type_id: int, ap_id: int, payload: dict):
    if "enabled" not in payload:
        return _err(ERR_PARAM, "enabled 不能为空")
    contract_type_repository.toggle_association(type_id, ap_id, bool(payload["enabled"]))
    return _ok()
```

---

## 四、AI 引擎内部接口

### 4.1 `api/internal.py`（新建）

```python
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from src.services.contract_type_store import contract_type_repository
from src.services.audit_point_store import audit_point_repository

router = APIRouter()

@router.get("/contract-types/match")
async def match_contract_type(
    name: str = Query(default=""),
    stance: str = Query(default=""),
):
    """按名称+立场精确匹配合同类型。"""
    if not name or not stance:
        return _err(40001, "name 和 stance 不能为空")
    
    record = contract_type_repository.find_by_name_stance(name.strip(), stance.strip())
    if record is None:
        return _err(40401, "合同类型不存在", 404)
    
    return _ok({
        "id": record["id"], "code": record.get("code"),
        "name": record["name"], "stance": record["stance"],
        "keywords": _parse_json(record.get("keywords"), []),
    })

@router.get("/contract-types/{type_id}/audit-points")
async def load_audit_points(type_id: int):
    """加载合同类型下全部已启用审查点规则（供 AI 引擎使用）。"""
    points = audit_point_repository.find_enabled_by_contract_type(type_id)
    for p in points:
        p["riskPoints"] = _parse_json(p.pop("risk_points", None), [])
        p["examples"] = _parse_json(p.pop("examples", None), [])
        p["defaultResult"] = _parse_json(p.pop("default_result", None), {})
    return _ok(points)
```

### 4.2 LLM 配置

**`.env`**：
```bash
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_API_KEY=ollama
LLM_MODEL_NAME=qwen3:32b
```

**`config.py`**：
```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    llm_api_url: str = "http://localhost:11434/v1/chat/completions"
    llm_api_key: str = "ollama"
    llm_model_name: str = "qwen3:32b"
```

当前 v1 阶段 `/internal` 接口仅返回数据库中的配置数据。LLM 配置被读取并暴露给 future 调用方，实际 LLM 调用在后续版本接入。

### 4.3 `audit_point_store.py` 新增方法

```python
def find_enabled_by_contract_type(self, type_id: int) -> list[dict]:
    """按合同类型查询已启用审查点（双层 enabled 过滤）。"""
    sql = """
        SELECT ap.id, ap.name, ap.instruction,
               ap.risk_points, ap.examples, ap.default_result
        FROM contract_type_audit_point ctap
        JOIN audit_point ap ON ap.id = ctap.audit_point_id
        WHERE ctap.contract_type_id = %s
          AND ctap.enabled = 1
          AND ap.enabled = 1
          AND ap.deleted_at IS NULL
        ORDER BY ctap.sort_order
    """
    # ...
```

### 4.4 `contract_type_store.py` 新增方法

```python
def find_by_name_stance(self, name: str, stance: str) -> dict | None:
    """精确匹配合同类型名称+立场。"""
    sql = """
        SELECT id, code, name, stance, keywords
        FROM contract_type
        WHERE name = %s AND stance = %s
          AND enabled = 1 AND deleted_at IS NULL
    """
    # ...
```

---

## 五、审核引擎 `contracts.py` 适配

`_build_audit_items()` 读取的 JSON 字段名改为 tmp 格式：

```python
def _build_audit_items(points, original_blocks):
    for point in points:
        default_result = _json_value(point.get("default_result"), {})
        risk_points = _json_value(point.get("risk_points"), [])
        level = _frontend_level(default_result)
        items.append({
            "title": str(point.get("name") or "合同风险"),
            "risk_level": 1 if level == "major" else 2,
            "risk_summary": str(default_result.get("analysis") or point.get("description") or ""),
            "risk_analysis": str(_risk_point_analysis(risk_points, level) or default_result.get("analysis") or ""),
            "modify_example": str(default_result.get("suggestion") or ""),
            "clause_name": str(point.get("name") or ""),
            # ...
        })

def _frontend_level(default_result):
    level = str(default_result.get("level") or "")
    return "major" if level in ("高风险", "重大风险") else "general"

def _risk_point_analysis(risk_points, level):
    key = "highStd" if level == "major" else "lowStd"
    for item in (risk_points or []):
        if isinstance(item, dict) and item.get(key):
            return str(item[key])
    return ""
```

---

## 六、前端 mock 数据更新

`mock/db.js` 中 `points` 数组的字段名更新：

```javascript
// 旧（当前）
{ id: 'p1', name: '主体信息与签署授权', category: '合规与权属风险', dimension: '基础核查',
  desc: '核查甲乙方名称...', riskPoints: 2, status: '已启用', defaultChecked: true }

// 新（tmp 格式）
{ id: 'p1', name: '主体信息与签署授权', description: '核查甲乙方名称...',
  dimId: 1, dimName: '基础核查',
  riskPoints: ['主体信息缺失'],
  enabled: 1 }
```

---

## 七、变更文件清单

| # | 文件 | 动作 | 内容 |
|----|------|------|------|
| 1 | `db/migrations/008_rebuild_config_tables.sql` | 新建 | DROP + CREATE 4 表 + 种子数据 |
| 2 | `db/migrations/009_seed_tmp_format.sql` | 新建 | tmp 格式种子数据（18 点 + 5 维度 + 6 类型） |
| 3 | `services/dimension_store.py` | 重写 | `description` + `enabled` TINYINT |
| 4 | `services/audit_point_store.py` | 重写 | 列名+JSON 字段名+tmp 格式方法 |
| 5 | `services/contract_type_store.py` | 重写 | 列名+linkedPointCount+关联方法 |
| 6 | `api/audit_points.py` | 重写 | 全 tmp 格式请求/响应 |
| 7 | `api/dimensions.py` | 重写 | 全 tmp 格式请求/响应 |
| 8 | `api/contract_types.py` | 重写 | 全 tmp 格式请求/响应 |
| 9 | `api/internal.py` | **新建** | AI 引擎 2 个端点 |
| 10 | `config.py` | 修改 | 新增 LLM 配置 |
| 11 | `.env.example` | 修改 | 新增 LLM 配置项 |
| 12 | `api/contracts.py` | 修改 | `_build_audit_items` 字段名适配 |
| 13 | `api/adapters.py` | 修改 | 删除 point 旧字段映射（由 `audit_points.py` 直接返回 tmp 格式） |
| 14 | `frontend/src/api/mock/db.js` | 修改 | mock 数据字段对齐 tmp |
| 15 | `main.py` | 修改 | 注册 `internal_router` |

---

## 八、验证路径

```
[DB 重建]
  DROP 旧表 → CREATE 新表（description/enabled） → 种子数据写入 → 查询验证列名

[审查点 CRUD]
  GET /api/audit-points?dimId=1&enabled=1 → {code:0, data:[{riskPoints:[名称数组], enabled:1}]}
  POST /api/audit-points  body:{dimId, name, description, riskPoints, defaultResult, enabled} → 201
  PATCH /api/audit-points/1/enabled  body:{enabled:0} → {code:0, msg:"ok"}

[合同类型关联]
  PUT /api/contract-types/1/audit-points  body:{auditPointIds:[1,2,3]} → ok
  PATCH /api/contract-types/1/audit-points/2/enabled  body:{enabled:0} → ok
  GET /api/contract-types/1 → data.linkedAuditPoints[...]

[AI 内部接口]
  GET /api/internal/contract-types/match?name=采购合同&stance=甲方立场 → {code:0, data:{id,code,...}}
  GET /api/internal/contract-types/1/audit-points → [{id, name, riskPoints:[...], defaultResult:{...}}]

[前端构建]
  npm run build → 通过
```
