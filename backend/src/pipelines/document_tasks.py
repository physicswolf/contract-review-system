from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from src.config import Settings
from src.services.document_parser import (
    ParsingArtifacts,
    ParsingError,
    delete_parsing_artifacts,
    parse_uploaded_document,
)
from src.services.file_storage import StoredUpload, delete_stored_upload


SHANGHAI_TZ = timezone(timedelta(hours=8))
TaskStatus = Literal["queued", "running", "succeeded", "failed"]


@dataclass(frozen=True)
class TaskError:
    code: str
    message: str


@dataclass(frozen=True)
class DocumentTaskSnapshot:
    id: str
    file_id: str
    status: TaskStatus
    stage: str
    created_at: str
    updated_at: str
    error: TaskError | None = None
    parsing_dir: str | None = None
    document_json_path: str | None = None


@dataclass
class _DocumentTaskState:
    id: str
    file_id: str
    stored_upload: StoredUpload
    status: TaskStatus
    stage: str
    created_at: datetime
    updated_at: datetime
    error: TaskError | None = None
    parsing_dir: Path | None = None
    document_json_path: Path | None = None

    def snapshot(self) -> DocumentTaskSnapshot:
        return DocumentTaskSnapshot(
            id=self.id,
            file_id=self.file_id,
            status=self.status,
            stage=self.stage,
            created_at=self.created_at.isoformat(timespec="seconds"),
            updated_at=self.updated_at.isoformat(timespec="seconds"),
            error=self.error,
            parsing_dir=str(self.parsing_dir) if self.parsing_dir else None,
            document_json_path=str(self.document_json_path)
            if self.document_json_path
            else None,
        )


class DocumentTaskManager:
    def __init__(self, max_workers: int = 1):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="document-pipeline",
        )
        self._lock = threading.Lock()
        self._tasks: dict[str, _DocumentTaskState] = {}

    def enqueue(
        self,
        stored_upload: StoredUpload,
        settings: Settings,
    ) -> DocumentTaskSnapshot:
        now = datetime.now(SHANGHAI_TZ)
        task_id = str(uuid4())
        state = _DocumentTaskState(
            id=task_id,
            file_id=stored_upload.metadata.id,
            stored_upload=stored_upload,
            status="queued",
            stage="queued",
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks[task_id] = state

        self._executor.submit(self._run_task, task_id, settings)
        return state.snapshot()

    def get(self, task_id: str) -> DocumentTaskSnapshot | None:
        with self._lock:
            state = self._tasks.get(task_id)
            if state is None:
                return None
            return state.snapshot()

    def _run_task(self, task_id: str, settings: Settings) -> None:
        parsing_artifacts: ParsingArtifacts | None = None
        stored_upload: StoredUpload | None = None
        try:
            stored_upload = self._get_stored_upload(task_id)
            self._update(task_id, status="running", stage="parsing")
            parsing_artifacts = parse_uploaded_document(
                stored_upload.path,
                stored_upload.metadata.id,
                stored_upload.metadata.extension,
                settings,
            )
            self._update(
                task_id,
                status="succeeded",
                stage="completed",
                parsing_dir=parsing_artifacts.directory,
                document_json_path=parsing_artifacts.json_path,
            )
        except ParsingError as exc:
            if stored_upload is not None:
                delete_stored_upload(stored_upload)
            if parsing_artifacts is not None:
                delete_parsing_artifacts(parsing_artifacts)
            self._fail(task_id, exc.code, exc.message)
        except Exception as exc:
            if stored_upload is not None:
                delete_stored_upload(stored_upload)
            if parsing_artifacts is not None:
                delete_parsing_artifacts(parsing_artifacts)
            self._fail(task_id, "DOCUMENT_TASK_ERROR", str(exc) or "文档处理失败")

    def _get_stored_upload(self, task_id: str) -> StoredUpload:
        with self._lock:
            return self._tasks[task_id].stored_upload

    def _update(
        self,
        task_id: str,
        *,
        status: TaskStatus,
        stage: str,
        parsing_dir: Path | None = None,
        document_json_path: Path | None = None,
    ) -> None:
        with self._lock:
            state = self._tasks[task_id]
            state.status = status
            state.stage = stage
            state.updated_at = datetime.now(SHANGHAI_TZ)
            if parsing_dir is not None:
                state.parsing_dir = parsing_dir
            if document_json_path is not None:
                state.document_json_path = document_json_path

    def _fail(self, task_id: str, code: str, message: str) -> None:
        with self._lock:
            state = self._tasks[task_id]
            state.status = "failed"
            state.stage = "failed"
            state.updated_at = datetime.now(SHANGHAI_TZ)
            state.error = TaskError(code=code, message=message)


document_task_manager = DocumentTaskManager()
