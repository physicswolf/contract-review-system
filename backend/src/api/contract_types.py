from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.adapters import contract_type_from_frontend, contract_type_to_frontend
from src.api.responses import error_response, flat_list, flat_object, ok_deleted
from src.services.contract_type_store import contract_type_repository


router = APIRouter()


@router.get("")
async def list_contract_types(keyword: str = Query(default="")) -> JSONResponse:
    try:
        records = contract_type_repository.find_all({"keyword": keyword})
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同类型列表读取失败")
    return flat_list([contract_type_to_frontend(record) for record in records], len(records))


@router.get("/{type_id}")
async def get_contract_type(type_id: int) -> JSONResponse:
    try:
        record = contract_type_repository.find_by_id(type_id)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同类型读取失败")
    if record is None:
        return error_response(404, "CONTRACT_TYPE_NOT_FOUND", "合同类型不存在")
    return flat_object(contract_type_to_frontend(record, detail=True))


@router.post("")
async def create_contract_type(payload: dict) -> JSONResponse:
    if not str(payload.get("name") or "").strip():
        return error_response(422, "CONTRACT_TYPE_NAME_REQUIRED", "请填写合同类型名称")
    try:
        type_id = contract_type_repository.insert(contract_type_from_frontend(payload))
        record = contract_type_repository.find_by_id(type_id)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同类型创建失败")
    return flat_object(contract_type_to_frontend(record, detail=True), status_code=201)


@router.put("/{type_id}")
async def update_contract_type(type_id: int, payload: dict) -> JSONResponse:
    try:
        record = contract_type_repository.update_by_id(type_id, contract_type_from_frontend(payload))
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同类型更新失败")
    if record is None:
        return error_response(404, "CONTRACT_TYPE_NOT_FOUND", "合同类型不存在")
    return flat_object(contract_type_to_frontend(record, detail=True))


@router.delete("/{type_id}")
async def delete_contract_type(type_id: int) -> JSONResponse:
    try:
        deleted = contract_type_repository.delete_by_id(type_id)
    except RuntimeError:
        return error_response(500, "INTERNAL_ERROR", "合同类型删除失败")
    if not deleted:
        return error_response(404, "CONTRACT_TYPE_NOT_FOUND", "合同类型不存在")
    return ok_deleted()
