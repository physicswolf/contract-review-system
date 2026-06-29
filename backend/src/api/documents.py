from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from fastapi.responses import JSONResponse

from src.api.responses import error_response
from src.config import get_settings
from src.schemas import (
    DocumentData,
    DocumentInfo,
    StructureData,
    StructureMeta,
    StructureUpdateRequest,
)
from src.services.structure_editor import (
    DocumentNotFoundError,
    StructureEditorError,
    StructureValidationError,
    document_exists,
    load_document_json,
    save_contract_structure,
)


router = APIRouter()


@router.get("/{file_id}", response_model=None)
async def get_document(file_id: str) -> dict | JSONResponse:
    settings = get_settings()
    if not document_exists(file_id, settings):
        return error_response(
            404,
            "DOCUMENT_NOT_FOUND",
            "文档不存在或尚未解析完成",
        )

    try:
        document = load_document_json(file_id, settings)
    except FileNotFoundError:
        return error_response(
            404,
            "DOCUMENT_NOT_FOUND",
            "文档不存在或尚未解析完成",
        )
    except (OSError, json.JSONDecodeError):
        return error_response(500, "INTERNAL_ERROR", "文档读取失败，请稍后重试")

    structure = document.get("contract_structure")
    warnings = document.get("warnings")
    origin = document.get("origin")
    children = structure.get("children") if isinstance(structure, dict) else None

    return DocumentData(
        document=DocumentInfo(
            file_id=file_id,
            schema_name=str(document.get("schema_name") or ""),
            origin=origin if isinstance(origin, dict) else {},
            has_structure=isinstance(structure, dict),
            chapter_count=len(children) if isinstance(children, list) else 0,
            warning_count=len(warnings) if isinstance(warnings, list) else 0,
        )
    ).model_dump()


@router.get("/{file_id}/structure", response_model=None)
async def get_document_structure(file_id: str) -> dict | JSONResponse:
    settings = get_settings()
    try:
        document = load_document_json(file_id, settings)
    except FileNotFoundError:
        return error_response(
            404,
            "DOCUMENT_NOT_FOUND",
            "文档不存在或尚未解析完成",
        )
    except (OSError, json.JSONDecodeError):
        return error_response(500, "INTERNAL_ERROR", "文档读取失败，请稍后重试")

    structure = document.get("contract_structure")
    if not isinstance(structure, dict):
        return error_response(
            422,
            "STRUCTURE_VALIDATION_ERROR",
            "文档缺少 contract_structure",
        )

    return StructureData(
        meta=StructureMeta(
            schema_name=str(document.get("schema_name") or ""),
            file_id=file_id,
        ),
        structure=structure,
    ).model_dump()


@router.put("/{file_id}/structure")
async def update_document_structure(
    file_id: str,
    request: StructureUpdateRequest,
) -> JSONResponse:
    settings = get_settings()
    try:
        save_contract_structure(file_id, request.structure, settings)
    except (DocumentNotFoundError, FileNotFoundError):
        return error_response(
            404,
            "DOCUMENT_NOT_FOUND",
            "文档不存在或尚未解析完成",
        )
    except StructureValidationError as error:
        return error_response(error.status_code, error.code, error.message)
    except StructureEditorError as error:
        return error_response(error.status_code, error.code, error.message)
    except (OSError, json.JSONDecodeError):
        return error_response(500, "INTERNAL_ERROR", "结构保存失败，请稍后重试")

    return JSONResponse(status_code=200, content={"message": "结构已保存"})
