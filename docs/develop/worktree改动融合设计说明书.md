# worktree 改动融合设计说明书

**项目**：contract-review-system  
**日期**：2026-06-30  
**版本**：v1.0  
**对应计划书**：`docs/planning/worktree改动融合计划书.md`  
**来源 commit**：`7a3bf50`（`~/download/github/worktree/origin/contract-review-system`）

---

## 一、后端新增端点

### 1.1 `api/contract_types.py` 新增

在现有路由文件末尾新增：

```python
@router.get("/{type_id}/audit-points/description")
async def get_audit_point_descriptions(
    type_id: int,
    dimId: int | None = Query(default=None),
) -> JSONResponse:
    """按合同类型查询审查点说明，按维度分组返回。
    用于前端审核前预览审查点和审核结果辅助说明。"""
    try:
        ct = contract_type_repository.find_by_id(type_id)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型读取失败")

    if ct is None or not ct.get("enabled"):
        return tmp_error(404, ERR_NOTFOUND, "合同类型不存在或已停用")

    try:
        rows = audit_point_repository.find_descriptions_by_contract_type(
            type_id, dim_id=dimId,
        )
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "审查点说明读取失败")

    # 按维度分组
    dims: dict[int, dict] = {}
    for r in rows:
        did = int(r["dim_id"])
        if did not in dims:
            dims[did] = {
                "dimId": did,
                "dimName": r["dim_name"],
                "auditPoints": [],
            }
        dims[did]["auditPoints"].append({
            "id": int(r["id"]),
            "name": r["name"],
            "description": r.get("description") or "",
            "instruction": r.get("instruction") or "",
            "riskPoints": _json_value(r.get("risk_points"), []),
        })

    return tmp_ok({
        "contractType": {"id": int(ct["id"]), "name": ct["name"]},
        "dimensions": list(dims.values()),
    })
```

### 1.2 `audit_point_store.py` 新增查询方法

```python
def find_descriptions_by_contract_type(
    self, type_id: int, dim_id: int | None = None,
) -> list[dict[str, Any]]:
    """查询某合同类型下已启用审查点的说明信息（按维度分组用）。"""
    try:
        conn = db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT d.id AS dim_id, d.name AS dim_name, d.sort_order AS dim_sort,
                           ap.id, ap.name, ap.description, ap.instruction,
                           ap.risk_points, ap.sort_order
                      FROM contract_type_audit_point ctap
                      JOIN audit_point ap ON ap.id = ctap.audit_point_id
                      JOIN dimension d ON d.id = ap.dim_id
                     WHERE ctap.contract_type_id = %(type_id)s
                       AND ctap.enabled = 1
                       AND ap.enabled = 1
                       AND ap.deleted_at IS NULL
                """
                params = {"type_id": type_id}
                if dim_id is not None:
                    sql += " AND d.id = %(dim_id)s"
                    params["dim_id"] = dim_id
                sql += " ORDER BY d.sort_order, ap.sort_order"
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    except pymysql.err.DatabaseError as exc:
        raise RuntimeError(f"MySQL 审查点说明读取失败: {exc}") from exc
```

### 1.3 路由顺序注意事项

FastAPI 按注册顺序匹配路由。`GET /{type_id}/audit-points/description` 必须在 `GET /{type_id}` 之前注册，否则 `type_id` 会被 "audit-points" 字符串误匹配。

当前 `contract_types.py` 的路由顺序：
```python
@router.get("")                                    # /
@router.get("/{type_id}")                          # /{id}
@router.post("")                                   # /
@router.put("/{type_id}")                          # /{id}
@router.delete("/{type_id}")                       # /{id}
@router.put("/{type_id}/audit-points")             # /{id}/audit-points
@router.patch("/{type_id}/audit-points/{...}")     # /{id}/audit-points/{apid}/enabled
```

新增的 description 端点路径 `/{type_id}/audit-points/description` 与 `/{type_id}` 的匹配判断：FastAPI 会将 `audit-points` 视为 `type_id` 的值尝试匹配 `/{type_id}`，导致 422 类型错误。

**解决方案**：将 description 端点放在 `GET /{type_id}` **之前**：

```python
@router.get("")                                    # /
@router.get("/{type_id}/audit-points/description") # /{id}/audit-points/description ← 新增，在前
@router.get("/{type_id}")                          # /{id}
```

---

## 二、前端 config.js 自动探测

### 2.1 改动

```javascript
// 当前
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'
export const ENABLE_STRUCTURE_EDITOR = import.meta.env.VITE_ENABLE_STRUCTURE_EDITOR === 'true'

// 融合后
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const _base = location.hostname === 'localhost' ? 'http://localhost:8000' : ''
export const API_BASE = import.meta.env.VITE_API_BASE || `${_base}/api`

export const ENABLE_STRUCTURE_EDITOR = import.meta.env.VITE_ENABLE_STRUCTURE_EDITOR === 'true'
```

### 2.2 行为说明

| 部署环境 | `location.hostname` | `_base` | `API_BASE` 默认值 |
|----------|---------------------|---------|-------------------|
| 本地开发 | `localhost` | `http://localhost:8000` | `http://localhost:8000/api` |
| 远程部署 | `180.76.53.236` | `''` | `/api`（同源请求） |
| 自定义 | 任意 | 由 `VITE_API_BASE` 覆盖 | `VITE_API_BASE` 的值 |

worktree 版本中 `_base` 使用端口 5002 和前缀 `/api/v1/config`，本地适配为端口 8000 和前缀 `/api`。

---

## 三、变更文件清单

| # | 文件 | 动作 | 内容 |
|----|------|------|------|
| 1 | `api/contract_types.py` | 新增端点 | `GET /{type_id}/audit-points/description` + 调整路由顺序 |
| 2 | `services/audit_point_store.py` | 新增方法 | `find_descriptions_by_contract_type` |
| 3 | `frontend/src/services/config.js` | 修改 | 增加 `_base` 自动探测 |

---

## 四、验证路径

```
[审查点说明接口]
  GET /api/contract-types/1/audit-points/description
  → {code:0, data:{contractType:{id:1,name:"采购合同"}, dimensions:[...]}}
  
  已停用合同类型:
  GET /api/contract-types/6/audit-points/description
  → {code:40401, msg:"合同类型不存在或已停用"}

  按维度筛选:
  GET /api/contract-types/1/audit-points/description?dimId=2
  → 仅返回 dimId=2 的维度分组

[前端构建]
  npm run build → 通过
```
