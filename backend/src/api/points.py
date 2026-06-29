from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.adapters import point_from_frontend, point_to_frontend
from src.api.responses import error_response, flat_list, flat_object, ok_deleted
from src.services.audit_point_store import audit_point_repository


router = APIRouter()


@router.get("")
async def list_points(keyword: str = Query(default="")) -> JSONResponse:
    try:
        records = audit_point_repository.find_all({"keyword": keyword})
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "审查点列表读取失败")
    return flat_list([point_to_frontend(record) for record in records], len(records))


@router.get("/{point_id}")
async def get_point(point_id: int) -> JSONResponse:
    try:
        record = audit_point_repository.find_by_id(point_id)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "审查点读取失败")
    if record is None:
        return error_response(404, "POINT_NOT_FOUND", "审查点不存在")
    return flat_object(point_to_frontend(record, detail=True))


@router.post("")
async def create_point(payload: dict[str, Any]) -> JSONResponse:
    if not str(payload.get("name") or "").strip():
        return error_response(422, "POINT_NAME_REQUIRED", "请填写审查点名称")
    try:
        point_id = audit_point_repository.insert(point_from_frontend(payload))
        record = audit_point_repository.find_by_id(point_id)
    except ValueError as exc:
        return error_response(422, "POINT_DIMENSION_REQUIRED", str(exc))
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "审查点创建失败")
    return flat_object(point_to_frontend(record, detail=True), status_code=201)


@router.put("/{point_id}")
async def update_point(point_id: int, payload: dict[str, Any]) -> JSONResponse:
    try:
        record = audit_point_repository.update_by_id(point_id, point_from_frontend(payload))
    except ValueError as exc:
        return error_response(422, "POINT_DIMENSION_REQUIRED", str(exc))
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "审查点更新失败")
    if record is None:
        return error_response(404, "POINT_NOT_FOUND", "审查点不存在")
    return flat_object(point_to_frontend(record, detail=True))


@router.delete("/{point_id}")
async def delete_point(point_id: int) -> JSONResponse:
    try:
        deleted = audit_point_repository.delete_by_id(point_id)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "审查点删除失败")
    if not deleted:
        return error_response(404, "POINT_NOT_FOUND", "审查点不存在")
    return ok_deleted()
