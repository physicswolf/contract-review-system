from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.responses import ERR_CONFLICT, ERR_NOTFOUND, ERR_PARAM, ERR_SERVER, tmp_error, tmp_ok
from src.services.dimension_store import dimension_repository


router = APIRouter()


@router.get("")
async def list_dimensions(enabled: int | None = Query(default=None)) -> JSONResponse:
    try:
        records = dimension_repository.find_all(enabled=enabled)
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "维度列表读取失败")
    return tmp_ok([_dimension_tmp(record) for record in records])


@router.get("/names", response_model=None)
async def list_dimension_names() -> list[str] | JSONResponse:
    try:
        return dimension_repository.find_names()
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "维度名称读取失败")


@router.get("/selectable", response_model=None)
async def list_selectable_dimensions() -> list[dict[str, Any]] | JSONResponse:
    try:
        return [
            {
                "name": record.get("name", ""),
                "desc": record.get("description") or "",
                "description": record.get("description") or "",
            }
            for record in dimension_repository.find_selectable()
        ]
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "可选维度读取失败")


@router.post("")
async def create_dimension(payload: dict[str, Any]) -> JSONResponse:
    if not str(payload.get("name") or "").strip():
        return tmp_error(400, ERR_PARAM, "请填写维度名称")
    try:
        dimension_id = dimension_repository.insert(payload)
    except ValueError as exc:
        return tmp_error(409, ERR_CONFLICT, str(exc))
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "维度创建失败")
    return tmp_ok({"id": dimension_id}, status_code=201)


@router.put("/{dimension_id}")
async def update_dimension(dimension_id: int, payload: dict[str, Any]) -> JSONResponse:
    try:
        record = dimension_repository.update_by_id(dimension_id, payload)
    except ValueError as exc:
        return tmp_error(409, ERR_CONFLICT, str(exc))
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "维度更新失败")
    if record is None:
        return tmp_error(404, ERR_NOTFOUND, "维度不存在")
    return tmp_ok(_dimension_tmp(record))


@router.delete("/{dimension_id}")
async def delete_dimension(dimension_id: int) -> JSONResponse:
    try:
        deleted = dimension_repository.delete_by_id(dimension_id)
    except ValueError as exc:
        return tmp_error(409, ERR_CONFLICT, str(exc))
    except RuntimeError:
        return tmp_error(500, ERR_SERVER, "维度删除失败")
    if not deleted:
        return tmp_error(404, ERR_NOTFOUND, "维度不存在")
    return tmp_ok()


@router.post("/relations")
async def save_relations(payload: dict[str, Any]) -> JSONResponse:
    return tmp_ok()


def _dimension_tmp(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(record["id"]),
        "name": record.get("name", ""),
        "description": record.get("description") or "",
        "desc": record.get("description") or "",
        "sortOrder": int(record.get("sort_order") or 0),
        "enabled": int(record.get("enabled") or 0),
        "status": "已启用" if int(record.get("enabled") or 0) else "已停用",
        "updatedAt": _format_iso(record.get("updated_at")),
    }


def _format_iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")
