from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.responses import ERR_NOTFOUND, ERR_PARAM, ERR_SERVER, tmp_error, tmp_ok
from src.services.audit_point_store import audit_point_repository


router = APIRouter()


@router.get("")
async def list_audit_points(
    keyword: str = Query(default=""),
    dimId: int | None = Query(default=None),
    enabled: int | None = Query(default=None),
) -> JSONResponse:
    try:
        records = audit_point_repository.find_all_tmp_format(
            {"keyword": keyword, "dim_id": dimId, "enabled": enabled}
        )
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "审查点列表读取失败")
    return tmp_ok(records)


@router.get("/{point_id}")
async def get_audit_point(point_id: int) -> JSONResponse:
    try:
        record = audit_point_repository.find_by_id_tmp_format(point_id)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "审查点读取失败")
    if record is None:
        return tmp_error(404, ERR_NOTFOUND, "审查点不存在")
    return tmp_ok(record)


@router.post("")
async def create_audit_point(payload: dict[str, Any]) -> JSONResponse:
    if not payload.get("dimId") or not str(payload.get("name") or "").strip():
        return tmp_error(400, ERR_PARAM, "dimId 和 name 不能为空")
    try:
        point_id = audit_point_repository.insert_from_tmp(payload)
    except ValueError as exc:
        return tmp_error(400, ERR_PARAM, str(exc))
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "审查点创建失败")
    return tmp_ok({"id": point_id}, status_code=201)


@router.put("/{point_id}")
async def update_audit_point(point_id: int, payload: dict[str, Any]) -> JSONResponse:
    try:
        record = audit_point_repository.update_from_tmp(point_id, payload)
    except ValueError as exc:
        return tmp_error(400, ERR_PARAM, str(exc))
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "审查点更新失败")
    if record is None:
        return tmp_error(404, ERR_NOTFOUND, "审查点不存在")
    return tmp_ok()


@router.patch("/{point_id}/enabled")
async def toggle_audit_point(point_id: int, payload: dict[str, Any]) -> JSONResponse:
    if "enabled" not in payload:
        return tmp_error(400, ERR_PARAM, "enabled 不能为空")
    try:
        record = audit_point_repository.toggle_enabled(point_id, bool(int(payload.get("enabled", 1))))
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "审查点状态更新失败")
    if record is None:
        return tmp_error(404, ERR_NOTFOUND, "审查点不存在")
    return tmp_ok()


@router.delete("/{point_id}")
async def delete_audit_point(point_id: int) -> JSONResponse:
    try:
        deleted = audit_point_repository.delete_by_id(point_id)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "审查点删除失败")
    if not deleted:
        return tmp_error(404, ERR_NOTFOUND, "审查点不存在")
    return tmp_ok()
