# worktree 7a3bf50 改动融合计划书

**项目**：contract-review-system  
**日期**：2026-06-30  
**版本**：v1.0  
**状态**：待开发  
**设计说明书**：`docs/develop/worktree改动融合设计说明书.md`  
**来源**：`~/download/github/worktree/origin/contract-review-system` 分支 `ff0bf9c`，commit `7a3bf50`

---

## 一、背景

`7a3bf50` 提交在两个文件中做了改动：

| 文件 | 改动 | 本地当前状态 |
|------|------|-------------|
| `backend/routes/contract_type.py` | 新增 `GET /contract-types/{ct_id}/audit-points/description?dimId=` 端点 | **缺失** |
| `frontend/src/services/config.js` | 新增 `_base` 自动探测（localhost/远程服务器），API_BASE 默认值变更 | **部分有**（已有 `USE_MOCK` 环境变量和 `ENABLE_STRUCTURE_EDITOR`，但无 `_base` 自动探测） |

---

## 二、待融合内容

### 2.1 后端：审查点说明接口（新端点）

worktree 在 `contract_type.py` 新增了 `GET /contract-types/<int:ct_id>/audit-points/description` 端点，功能为：

- 按合同类型 ID 查询其下所有已启用审查点的说明信息
- 按维度分组返回
- 支持可选的 `dimId` 筛选参数
- 校验合同类型存在且已启用

这是 `teach_design/审查点说明接口设计.md` 中描述的前端"审核前预览审查点"功能的对应接口。

### 2.2 前端：API_BASE 自动探测

worktree 将 `config.js` 从硬编码默认值改为运行时自动探测：

```javascript
const _base = location.hostname === 'localhost' ? 'http://localhost:5002' : 'http://180.76.53.236:5002'
export const API_BASE = import.meta.env.VITE_API_BASE || `${_base}/api/v1/config`
```

本地适配时需要改为我们的端口和前缀。

---

## 三、融合方案

### 3.1 后端新端点

**位置**：`api/contract_types.py`

**端点**：`GET /api/contract-types/{type_id}/audit-points/description?dimId=`

**响应格式**（`{code:0, msg, data}`）：
```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "contractType": { "id": 1, "name": "采购合同" },
    "dimensions": [
      {
        "dimId": 1,
        "dimName": "基础核查",
        "auditPoints": [
          { "id": 1, "name": "主体信息与签署授权", "description": "...", "instruction": "...", "riskPoints": [...] }
        ]
      }
    ]
  }
}
```

### 3.2 前端 config.js 自动探测

在当前 `config.js` 基础上增加 `_base` 自动探测逻辑：

```javascript
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const _base = location.hostname === 'localhost' ? 'http://localhost:8000' : ''
export const API_BASE = import.meta.env.VITE_API_BASE || `${_base}/api`

export const ENABLE_STRUCTURE_EDITOR = import.meta.env.VITE_ENABLE_STRUCTURE_EDITOR === 'true'
```

远程部署时 `_base` 为空字符串（同源请求），本地开发时通过 Vite proxy 或直连 `localhost:8000`。

---

## 四、任务分解

| # | 任务 | 工作量 | 涉及文件 |
|----|------|--------|----------|
| 1 | 后端新增审查点说明端点 | 中（~0.5h） | `api/contract_types.py` |
| 2 | 前端 config.js 增加 `_base` 探测 | 极小（~5min） | `frontend/src/services/config.js` |
| 3 | 验证 | 小（~1h） | 路由检查 + 构建 |
| **合计** | | **~0.5h** | |
