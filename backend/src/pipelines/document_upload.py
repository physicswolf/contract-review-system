from __future__ import annotations

from dataclasses import dataclass

from fastapi import UploadFile

from src.config import Settings
from src.pipelines.document_tasks import DocumentTaskManager, DocumentTaskSnapshot, document_task_manager
from src.schemas import FileMeta
from src.services.file_storage import StoredUpload, UploadError, save_upload


DOCUMENT_UPLOAD_PIPELINE_ERRORS = (
    UploadError,
)


@dataclass(frozen=True)
class DocumentUploadResult:
    metadata: FileMeta
    stored_upload: StoredUpload
    task: DocumentTaskSnapshot


class DocumentUploadPipeline:
    def __init__(
        self,
        settings: Settings,
        task_manager: DocumentTaskManager = document_task_manager,
    ):
        self.settings = settings
        self.task_manager = task_manager

    async def run(self, file: UploadFile) -> DocumentUploadResult:
        stored_upload = await save_upload(file, self.settings)
        task = self.task_manager.enqueue(stored_upload, self.settings)

        return DocumentUploadResult(
            metadata=stored_upload.metadata,
            stored_upload=stored_upload,
            task=task,
        )
