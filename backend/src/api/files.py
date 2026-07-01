from __future__ import annotations

import shutil
from dataclasses import asdict

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from src.api.responses import error_response, ok_deleted
from src.config import get_settings
from src.pipelines.document_upload import (
    DOCUMENT_UPLOAD_PIPELINE_ERRORS,
    DocumentUploadPipeline,
)
from src.pipelines.document_tasks import document_task_manager
from src.schemas import FileData, TaskData, TaskMeta, UploadData
from src.services.file_storage import UploadError, find_upload_metadata


router = APIRouter()


def upload_error_response(error: UploadError) -> JSONResponse:
    return error_response(error.status_code, error.code, error.message)


@router.post("/upload", response_model=None)
async def upload_file(
    file: UploadFile | None = File(default=None),
) -> dict | JSONResponse:
    if file is None:
        return upload_error_response(
            UploadError("FILE_REQUIRED", "请提交合同文件", status_code=422)
        )

    settings = get_settings()
    try:
        result = await DocumentUploadPipeline(settings).run(file)
    except DOCUMENT_UPLOAD_PIPELINE_ERRORS as error:
        return upload_error_response(error)

    return UploadData(
        file=result.metadata,
        task=TaskMeta(**asdict(result.task)),
    ).model_dump()


@router.get("/tasks/{task_id}", response_model=None)
async def get_task_status(task_id: str) -> dict | JSONResponse:
    task = document_task_manager.get(task_id)
    if task is None:
        return error_response(404, "TASK_NOT_FOUND", "任务不存在")

    return TaskData(task=TaskMeta(**asdict(task))).model_dump()


@router.get("/{file_id}", response_model=None)
async def get_file_metadata(file_id: str) -> dict | JSONResponse:
    metadata = find_upload_metadata(file_id, get_settings())
    if metadata is None:
        return error_response(404, "FILE_NOT_FOUND", "文件不存在")
    return FileData(file=metadata).model_dump()


@router.delete("/{file_id}/artifacts")
async def delete_upload_artifacts(file_id: str) -> JSONResponse:
    settings = get_settings()

    if settings.upload_root.exists():
        for path in settings.upload_root.rglob(f"{file_id}.*"):
            if path.is_file():
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    shutil.rmtree(settings.parsing_root / file_id, ignore_errors=True)
    return ok_deleted()
