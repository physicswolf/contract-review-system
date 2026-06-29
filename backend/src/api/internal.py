from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.responses import ERR_NOTFOUND, ERR_PARAM, ERR_SERVER, tmp_error, tmp_ok
from src.services.audit_point_store import audit_point_repository
from src.services.contract_type_store import contract_type_repository


router = APIRouter()


@router.get("/contract-types/match")
async def match_contract_type(
    name: str = Query(default=""),
    stance: str = Query(default=""),
) -> JSONResponse:
    if not name.strip() or not stance.strip():
        return tmp_error(400, ERR_PARAM, "name 和 stance 不能为空")
    try:
        record = contract_type_repository.find_by_name_stance(name.strip(), stance.strip())
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型匹配失败")
    if record is None:
        return tmp_error(404, ERR_NOTFOUND, "合同类型不存在")
    return tmp_ok(
        {
            "id": int(record["id"]),
            "code": record.get("code") or "",
            "name": record.get("name") or "",
            "stance": record.get("stance") or "",
            "keywords": _json_value(record.get("keywords"), []),
        }
    )


@router.get("/contract-types/{type_id}/audit-points")
async def load_audit_points(type_id: int) -> JSONResponse:
    try:
        rows = audit_point_repository.find_enabled_by_contract_type(type_id)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "审查点规则读取失败")
    return tmp_ok([_point_rule(row) for row in rows])


def _point_rule(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row.get("name") or "",
        "description": row.get("description") or "",
        "instruction": row.get("instruction") or "",
        "dimId": int(row.get("dim_id") or 0),
        "dimName": row.get("dim_name") or "",
        "riskPoints": _json_value(row.get("risk_points"), []),
        "examples": _json_value(row.get("examples"), []),
        "defaultResult": _json_value(row.get("default_result"), {}),
        "enabled": int(row.get("enabled") or 0),
        "sortOrder": int(row.get("sort_order") or 0),
    }


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return fallback
