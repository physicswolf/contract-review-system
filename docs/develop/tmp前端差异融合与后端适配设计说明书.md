# tmp 前端差异融合与后端适配设计说明书

**项目**：contract-review-system  
**日期**：2026-06-29  
**版本**：v1.0  
**对应计划书**：`docs/planning/tmp前端差异融合与后端适配计划书.md`

---

## 一、前端融合方案

### 1.1 融合流程

```
Step 1: 以 tmp 版本覆盖 13 个差异文件
Step 2: 在覆盖后的文件上补回本次新增代码
Step 3: config.js 保留当前的 API_BASE + USE_MOCK 环境变量 + ENABLE_STRUCTURE_EDITOR
```

### 1.2 各文件融合细节

#### config.js

```javascript
// 融合后（保留 USE_MOCK 环境变量 + API_BASE /api + ENABLE_STRUCTURE_EDITOR）
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'
export const ENABLE_STRUCTURE_EDITOR = import.meta.env.VITE_ENABLE_STRUCTURE_EDITOR === 'true'
```

#### http.js

直接用 tmp 版本（多了 `data.msg` 容错）。

#### AppSidebar.vue

tmp 版本 + 补回 structureEditor 高亮：
```javascript
if (item.name === 'review') return route.name === 'review' || route.name === 'structureEditor'
```

#### router/index.js

tmp 版本 + 补回 structureEditor 路由：
```javascript
{ path: 'editor/:fileId', name: 'structureEditor', component: () => import('../views/contract/StructureEditor.vue') },
```

#### stores/review.js

tmp 版本 + 补回 fileId：
```javascript
export const reviewStore = reactive({
  contractId: '',
  fileId: '',        // ← 补回
  fileName: '',
  // ...
  reset() {
    this.contractId = ''
    this.fileId = ''   // ← 补回
    // ...
  },
})
```

#### ReviewWizard.vue

tmp 版本 + 补回结构编辑跳转和 resume 流程：
```javascript
import { ENABLE_STRUCTURE_EDITOR } from '../../services/config'

async function onUploaded(file) {
  const [res] = await Promise.all([uploadContract(file), overlay.value.start()])
  reviewStore.contractId = String(res.id || '')
  reviewStore.fileId = String(res.fileId || '')
  // ...
  if (res.enableStructureEditor && ENABLE_STRUCTURE_EDITOR && reviewStore.fileId) {
    router.push({ name: 'structureEditor', params: { fileId: reviewStore.fileId }, query: { ... } })
    return
  }
  step.value = 2
}

function initializeReviewState() { /* resume 流程 */ }
function backToUpload() { /* 清空 + 回到上传 */ }
```

#### contract.service.js

tmp 版本 + mock 中生成 fileId 和 enableStructureEditor（从本次新增代码合并）。

#### 其他 service/component 文件

直接使用 tmp 版本（auth/point/dimension/type service，ConfigCenter/PointEdit view）。

---

## 二、后端新增 `/api/audit-points` 路由

### 2.1 新建 `api/audit_points.py`

> 独立于现有 `api/points.py`，返回 tmp 兼容格式 `{code:0, msg:"ok", data:...}`

**列表 GET /api/audit-points**

查询参数：`keyword` (str)、`dimId` (int)、`enabled` (int: 0/1)

```python
@router.get("")
async def list_audit_points(
    keyword: str = Query(default=""),
    dimId: int | None = Query(default=None),
    enabled: int | None = Query(default=None),
):
    records = audit_point_repository.find_all_tmp_format({
        "keyword": keyword,
        "dim_id": dimId,
        "enabled": enabled,
    })
    return JSONResponse(content={"code": 0, "msg": "ok", "data": records})
```

返回 `data` 数组中每项字段（匹配 tmp `adaptPoint()` 期望）：
```json
{
  "id": 1,
  "name": "主体信息与签署授权",
  "description": "核查甲乙方名称...",
  "dimId": 1,
  "dimName": "基础核查",
  "riskPoints": ["主体信息缺失"],
  "enabled": 1,
  "updatedAt": "2026-06-29T10:00:00"
}
```

`riskPoints` 字段从 `risk_points` JSON 列提取 `title` 数组（非数量）。

**详情 GET /api/audit-points/:id**

```python
@router.get("/{point_id}")
async def get_audit_point(point_id: int):
    record = audit_point_repository.find_by_id_tmp_format(point_id)
    if record is None:
        return JSONResponse(status_code=404, content={"code": 40401, "msg": "审查点不存在"})
    return JSONResponse(content={"code": 0, "msg": "ok", "data": record})
```

返回完整 JSON 字段：`riskPoints`(原始JSON数组), `examples`, `defaultResult`。

**创建 POST /api/audit-points**

```python
@router.post("")
async def create_audit_point(payload: dict):
    point_id = audit_point_repository.insert_from_tmp(payload)
    return JSONResponse(status_code=201, content={"code": 0, "msg": "ok", "data": {"id": point_id}})
```

**更新 PUT /api/audit-points/:id**

```python
@router.put("/{point_id}")
async def update_audit_point(point_id: int, payload: dict):
    audit_point_repository.update_from_tmp(point_id, payload)
    return JSONResponse(content={"code": 0, "msg": "ok"})
```

**启停 PATCH /api/audit-points/:id/enabled**

```python
@router.patch("/{point_id}/enabled")
async def toggle_audit_point(point_id: int, payload: dict):
    enabled = payload.get("enabled", 1)
    audit_point_repository.toggle_enabled(point_id, bool(enabled))
    return JSONResponse(content={"code": 0, "msg": "ok"})
```

**删除 DELETE /api/audit-points/:id**

```python
@router.delete("/{point_id}")
async def delete_audit_point(point_id: int):
    deleted = audit_point_repository.delete_by_id(point_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"code": 40401, "msg": "审查点不存在"})
    return JSONResponse(content={"code": 0, "msg": "ok"})
```

### 2.2 `services/audit_point_store.py` 新增 tmp 格式方法

```python
def find_all_tmp_format(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """查询审查点列表，返回 tmp 前端兼容格式。"""
    filters = filters or {}
    keyword = str(filters.get("keyword") or "").strip()
    dim_id = filters.get("dim_id")
    enabled = filters.get("enabled")

    # SQL: 按 keyword/dim_id/enabled 筛选
    rows = [...]  # 查询 audit_point JOIN dimension

    result = []
    for r in rows:
        risk_points = _parse_json(r.get("risk_points"), [])
        result.append({
            "id": r["id"],
            "name": r["name"],
            "description": r.get("desc") or "",
            "dimId": r["dim_id"],
            "dimName": r.get("dim_name") or "",
            "riskPoints": [rp.get("title", "") for rp in risk_points if isinstance(rp, dict)],
            "enabled": 1 if r.get("status") == "已启用" else 0,
            "updatedAt": _format_iso(r.get("updated_at")),
        })
    return result

def find_by_id_tmp_format(self, point_id: int) -> dict[str, Any] | None:
    """查询审查点详情，返回 tmp 前端兼容格式。"""
    row = self.find_by_id(point_id)  # 复用现有方法
    if row is None:
        return None
    return {
        "id": row["id"],
        "dimId": row["dim_id"],
        "dimName": row.get("dim_name") or "",
        "name": row["name"],
        "description": row.get("desc") or "",
        "instruction": row.get("instruction") or "",
        "riskPoints": _parse_json(row.get("risk_points"), []),
        "examples": _parse_json(row.get("examples"), []),
        "defaultResult": _parse_json(row.get("default_result"), {}),
        "enabled": 1 if row.get("status") == "已启用" else 0,
        "updatedAt": _format_iso(row.get("updated_at")),
    }

def insert_from_tmp(self, payload: dict) -> int:
    """从 tmp 格式创建审查点。字段映射：dimId→dim_id, description→desc, enabled→status, riskPoints→risk_points, defaultResult→default_result"""
    mapped = {
        "dim_id": payload["dimId"],
        "name": payload.get("name", "").strip(),
        "desc": payload.get("description", ""),
        "instruction": payload.get("instruction", ""),
        "risk_points": payload.get("riskPoints"),
        "examples": payload.get("examples"),
        "default_result": payload.get("defaultResult"),
        "status": "已启用" if payload.get("enabled", 1) else "已停用",
    }
    return self.insert(mapped)

def update_from_tmp(self, point_id: int, payload: dict) -> None:
    """从 tmp 格式更新审查点。"""
    mapped = {}
    if "dimId" in payload: mapped["dim_id"] = payload["dimId"]
    if "name" in payload: mapped["name"] = payload["name"]
    if "description" in payload: mapped["desc"] = payload["description"]
    if "instruction" in payload: mapped["instruction"] = payload["instruction"]
    if "enabled" in payload: mapped["status"] = "已启用" if payload["enabled"] else "已停用"
    if "riskPoints" in payload: mapped["risk_points"] = payload["riskPoints"]
    if "examples" in payload: mapped["examples"] = payload["examples"]
    if "defaultResult" in payload: mapped["default_result"] = payload["defaultResult"]
    self.update_by_id(point_id, mapped)

def toggle_enabled(self, point_id: int, enabled: bool) -> None:
    """切换审查点启停状态。"""
    self.update_by_id(point_id, {"status": "已启用" if enabled else "已停用"})
```

---

## 三、后端修改 `/api/dimensions` 适配 tmp

### 3.1 `api/dimensions.py`

增加 `enabled` 查询参数，列表和创建/更新返回 `{code:0, msg:"ok", data:...}`：

```python
@router.get("")
async def list_dimensions(enabled: int | None = Query(default=None)):
    records = dimension_repository.find_all(enabled=enabled)
    data = [{
        "id": r["id"], "name": r["name"], "description": r.get("desc") or "",
        "sortOrder": r.get("sort_order", 0),
        "enabled": 1 if r.get("status") == "已启用" else 0,
        "updatedAt": _format_iso(r.get("updated_at")),
    } for r in records]
    return JSONResponse(content={"code": 0, "msg": "ok", "data": data})
```

### 3.2 `services/dimension_store.py`

`find_all` 增加 `enabled` 参数筛选。

---

## 四、后端修改 `/api/contract-types` 适配 tmp

### 4.1 `api/contract_types.py`

列表返回 tmp 格式（`description`, `enabled`, `linkedPointCount`）：

```python
@router.get("")
async def list_contract_types(
    keyword: str = Query(default=""),
    enabled: int | None = Query(default=None),
):
    records = contract_type_repository.find_all_tmp({"keyword": keyword, "enabled": enabled})
    return JSONResponse(content={"code": 0, "msg": "ok", "data": records})
```

详情返回 tmp 格式（含 `linkedAuditPoints`）：

```python
@router.get("/{type_id}")
async def get_contract_type(type_id: int):
    record = contract_type_repository.find_by_id_tmp(type_id)
    if record is None:
        return JSONResponse(status_code=404, content={"code": 40401, "msg": "合同类型不存在"})
    return JSONResponse(content={"code": 0, "msg": "ok", "data": record})
```

创建/更新接受 tmp 字段名（`description`, `enabled`, `keywords`），内部映射到当前列名（`desc`, `status`）。

### 4.2 `services/contract_type_store.py`

新增 tmp 格式查询方法和 `replace_associations` 方法。

---

## 五、后端新增关联端点

### 5.1 PUT /api/contract-types/:id/audit-points

```python
@router.put("/{type_id}/audit-points")
async def save_audit_points(type_id: int, payload: dict):
    ids = payload.get("auditPointIds") or []
    contract_type_repository.replace_associations(type_id, [int(i) for i in ids])
    return JSONResponse(content={"code": 0, "msg": "ok"})
```

### 5.2 PATCH /api/contract-types/:id/audit-points/:apid/enabled

```python
@router.patch("/{type_id}/audit-points/{ap_id}/enabled")
async def toggle_ct_audit_point(type_id: int, ap_id: int, payload: dict):
    enabled = payload.get("enabled", 1)
    contract_type_repository.toggle_association(type_id, ap_id, bool(enabled))
    return JSONResponse(content={"code": 0, "msg": "ok"})
```

---

## 六、main.py 注册新路由

```python
from src.api.audit_points import router as audit_points_router

app.include_router(audit_points_router, prefix="/api/audit-points", tags=["审查点(tmp兼容)"])
```

---

## 七、字段映射速查表

### tmp 前端 ↔ 当前 DB 列

| tmp 前端字段 | DB 列 | 类型转换 |
|-------------|-------|----------|
| `description` | `desc` | — |
| `enabled: 0\|1` | `status: '已启用'\|'已停用'` | `enabled==1` ↔ `status=='已启用'` |
| `dimId` | `dim_id` | — |
| `dimName` | JOIN `dimension.name` | — |
| `riskPoints` (数组) | `risk_points` (JSON) | 列表模式提取 `title` 数组 |
| `defaultResult` | `default_result` (JSON) | — |
| `linkedPointCount` | JOIN COUNT | 每次查询实时计算 |
| `sortOrder` | `sort_order` | — |
| `updatedAt` | `updated_at` | datetime → ISO 字符串 |

### 错误响应

| tmp 格式 | 当前格式 | HTTP |
|----------|----------|------|
| `{code: 0, msg: "ok"}` | 成功 | 200/201 |
| `{code: 40001, msg: "..."}` | `{"detail": "..."}` | 400 |
| `{code: 40401, msg: "..."}` | `{"detail": "..."}` | 404 |
| `{code: 40901, msg: "..."}` | `{"detail": "..."}` | 409 |
| `{code: 50001, msg: "内部服务错误"}` | `{"detail": "..."}` | 500 |

---

## 八、验证路径

```
[审查点管理]
  GET /api/audit-points?keyword=验收&dimId=2&enabled=1
  → 返回 {code:0, data:[{id, name, description, dimName, riskPoints:[], enabled:1}]}
  POST /api/audit-points → 创建成功 → PATCH .../enabled → 启停

[维度管理]
  GET /api/dimensions?enabled=1
  → 返回 {code:0, data:[{id, name, description, sortOrder, enabled:1}]}

[合同类型管理]
  GET /api/contract-types → 列表含 linkedPointCount
  GET /api/contract-types/:id → 详情含 linkedAuditPoints
  PUT /api/contract-types/:id/audit-points → 关联保存

[前端构建]
  npm run build → 通过
```
