from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.responses import ERR_CONFLICT, ERR_NOTFOUND, ERR_PARAM, ERR_SERVER, tmp_error, tmp_ok
from src.services.audit_point_store import audit_point_repository
from src.services.contract_type_store import contract_type_repository


router = APIRouter()


@router.get("")
async def list_contract_types(
    keyword: str = Query(default=""),
    enabled: int | None = Query(default=None),
) -> JSONResponse:
    try:
        records = contract_type_repository.find_all_tmp({"keyword": keyword, "enabled": enabled})
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型列表读取失败")
    return tmp_ok(records)


@router.get("/{type_id}/audit-points/description")
async def get_audit_point_descriptions(
    type_id: int,
    dimId: int | None = Query(default=None),
) -> JSONResponse:
    try:
        contract_type = contract_type_repository.find_by_id_tmp(type_id)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型读取失败")

    if contract_type is None or not contract_type.get("enabled"):
        return tmp_error(404, ERR_NOTFOUND, "合同类型不存在或已停用")

    try:
        rows = audit_point_repository.find_descriptions_by_contract_type(type_id, dim_id=dimId)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "审查点说明读取失败")

    dimensions: dict[int, dict[str, Any]] = {}
    for row in rows:
        dim_id = int(row["dim_id"])
        if dim_id not in dimensions:
            dimensions[dim_id] = {
                "dimId": dim_id,
                "dimName": row.get("dim_name") or "",
                "auditPoints": [],
            }
        dimensions[dim_id]["auditPoints"].append(
            {
                "id": int(row["id"]),
                "name": row.get("name") or "",
                "description": row.get("description") or "",
                "instruction": row.get("instruction") or "",
                "riskPoints": _json_value(row.get("risk_points"), []),
            }
        )

    return tmp_ok(
        {
            "contractType": {"id": int(contract_type["id"]), "name": contract_type.get("name") or ""},
            "dimensions": list(dimensions.values()),
        }
    )


@router.get("/{type_id}")
async def get_contract_type(type_id: int) -> JSONResponse:
    try:
        record = contract_type_repository.find_by_id_tmp(type_id)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型读取失败")
    if record is None:
        return tmp_error(404, ERR_NOTFOUND, "合同类型不存在")
    return tmp_ok(record)


@router.post("")
async def create_contract_type(payload: dict) -> JSONResponse:
    if not str(payload.get("name") or "").strip() or not str(payload.get("stance") or "").strip():
        return tmp_error(400, ERR_PARAM, "name 和 stance 不能为空")
    try:
        type_id = contract_type_repository.insert_from_tmp(payload)
    except ValueError as exc:
        return tmp_error(409, ERR_CONFLICT, str(exc))
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型创建失败")
    return tmp_ok({"id": type_id}, status_code=201)


@router.put("/{type_id}")
async def update_contract_type(type_id: int, payload: dict) -> JSONResponse:
    try:
        record = contract_type_repository.update_from_tmp(type_id, payload)
    except ValueError as exc:
        return tmp_error(409, ERR_CONFLICT, str(exc))
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型更新失败")
    if record is None:
        return tmp_error(404, ERR_NOTFOUND, "合同类型不存在")
    return tmp_ok()


@router.delete("/{type_id}")
async def delete_contract_type(type_id: int) -> JSONResponse:
    try:
        deleted = contract_type_repository.delete_by_id(type_id)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型删除失败")
    if not deleted:
        return tmp_error(404, ERR_NOTFOUND, "合同类型不存在")
    return tmp_ok()


@router.put("/{type_id}/audit-points")
async def save_audit_points(type_id: int, payload: dict[str, Any]) -> JSONResponse:
    try:
        ids = [int(value) for value in payload.get("auditPointIds") or []]
    except (TypeError, ValueError):
        return tmp_error(400, ERR_PARAM, "auditPointIds 格式错误")
    try:
        contract_type_repository.replace_associations(type_id, ids)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型审查点保存失败")
    return tmp_ok()


@router.patch("/{type_id}/audit-points/{point_id}/enabled")
async def toggle_contract_type_audit_point(
    type_id: int,
    point_id: int,
    payload: dict[str, Any],
) -> JSONResponse:
    if "enabled" not in payload:
        return tmp_error(400, ERR_PARAM, "enabled 不能为空")
    try:
        contract_type_repository.toggle_association(
            type_id,
            point_id,
            bool(int(payload.get("enabled", 1))),
        )
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "合同类型审查点状态更新失败")
    return tmp_ok()


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return fallback
