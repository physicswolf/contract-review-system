from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api.adapters import dimension_to_frontend
from src.api.responses import error_response, flat_list, flat_object, ok_deleted
from src.services.dimension_store import dimension_repository


router = APIRouter()


@router.get("")
async def list_dimensions() -> JSONResponse:
    try:
        records = dimension_repository.find_all()
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "维度列表读取失败")
    return flat_list([dimension_to_frontend(record) for record in records], len(records))


@router.get("/names", response_model=None)
async def list_dimension_names() -> list[str] | JSONResponse:
    try:
        return dimension_repository.find_names()
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "维度名称读取失败")


@router.get("/selectable", response_model=None)
async def list_selectable_dimensions() -> list[dict[str, Any]] | JSONResponse:
    try:
        return [
            {"name": record.get("name", ""), "desc": record.get("desc") or ""}
            for record in dimension_repository.find_selectable()
        ]
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "可选维度读取失败")


@router.post("")
async def create_dimension(payload: dict[str, Any]) -> JSONResponse:
    if not str(payload.get("name") or "").strip():
        return error_response(422, "DIMENSION_NAME_REQUIRED", "请填写维度名称")
    try:
        dimension_id = dimension_repository.insert(payload)
        record = dimension_repository.find_by_id(dimension_id)
    except ValueError as exc:
        return error_response(409, "DIMENSION_CONFLICT", str(exc))
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "维度创建失败")
    return flat_object(dimension_to_frontend(record), status_code=201)


@router.put("/{dimension_id}")
async def update_dimension(dimension_id: int, payload: dict[str, Any]) -> JSONResponse:
    try:
        record = dimension_repository.update_by_id(dimension_id, payload)
    except ValueError as exc:
        return error_response(409, "DIMENSION_CONFLICT", str(exc))
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "维度更新失败")
    if record is None:
        return error_response(404, "DIMENSION_NOT_FOUND", "维度不存在")
    return flat_object(dimension_to_frontend(record))


@router.delete("/{dimension_id}")
async def delete_dimension(dimension_id: int) -> JSONResponse:
    try:
        deleted = dimension_repository.delete_by_id(dimension_id)
    except ValueError as exc:
        return error_response(409, "DIMENSION_IN_USE", str(exc))
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "维度删除失败")
    if not deleted:
        return error_response(404, "DIMENSION_NOT_FOUND", "维度不存在")
    return ok_deleted()


@router.post("/relations")
async def save_relations(payload: dict[str, Any]) -> JSONResponse:
    return ok_deleted()
