from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.responses import ERR_CONFLICT, ERR_NOTFOUND, ERR_PARAM, ERR_SERVER, tmp_error, tmp_ok
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
